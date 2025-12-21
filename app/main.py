from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from app.models import NLQRequest
from app.prompt import build_prompt
from app.sqlcoder import run_sqlcoder
from app.security import validate_sql
from app.athena_client import execute_query
from app.utils import gen_request_id
from app.permissions import get_allowed_access
from app.request_logger import log_request, get_logs, get_log_count
from app.display_hint import get_display_type
import json

app = FastAPI(
    title="NLQ → Athena SQL API",
    version="0.3-prototype"
)


class PrettyJSONResponse(JSONResponse):
    """Custom JSON response with pretty formatting for terminal readability"""
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            separators=(", ", ": "),
        ).encode("utf-8")


@app.post("/nlq/execute", response_class=PrettyJSONResponse)
def execute(req: NLQRequest):
    try:
        request_id = req.trace.request_id or gen_request_id()

        # Get allowed access based on account/property UUIDs
        access = get_allowed_access(req.context.account_uuid, req.context.property_uuid)
        if access is None:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: No permissions for account {req.context.account_uuid} and property {req.context.property_uuid}"
            )

        # Use the first athena target - in future could support multi-target queries
        athena_target = access["athena_targets"][0]
        allowed_tables = access["tables"]

        prompt = build_prompt(
            text=req.text,
            context=req.context,
            sql=req.sql,
            athena_target=athena_target
        )

        result = run_sqlcoder(
            prompt=prompt,
            max_tokens=req.model.max_tokens
        )

        sql = validate_sql(
            result["query"],
            allowed_tables,
            req.sql.dialect
        )

        execution_data = None
        executed = False

        if not req.execution.dry_run:
            execution_data = execute_query(
                sql=sql,
                target_name=athena_target,
                max_rows=req.execution.max_rows
            )
            executed = True

        # Determine display type based on query and results
        display_type = "table"  # Default
        
        if executed and execution_data:
            display_type = get_display_type(sql, execution_data)

        response = {
            "success": True,
            "sql": {
                "query": sql,
                "confidence": result["confidence"]
            },
            "execution": {
                "executed": executed,
                "row_count": execution_data["row_count"] if execution_data else None,
                "data": execution_data
            },
            "display": {
                "type": display_type
            },
            "explanation": result["explanation"],
            "trace": {
                "request_id": request_id,
                "latency_ms": result["latency_ms"],
                "athena_target": athena_target,
                "allowed_tables": allowed_tables
            }
        }

        # Log the request/response
        log_request(
            request_id=request_id,
            request_data=req.dict(),
            response_data=response,
            status_code=200
        )

        return response

    except Exception as e:
        # Log the failed request
        error_response = {"success": False, "error": str(e)}
        log_request(
            request_id=request_id if 'request_id' in locals() else gen_request_id(),
            request_data=req.dict(),
            response_data=error_response,
            status_code=400,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/logs", response_class=PrettyJSONResponse)
def view_logs(limit: int = 100):
    """
    View the last N API request/response logs (max 100).
    """
    return {
        "total_logs": get_log_count(),
        "logs": get_logs(limit=min(limit, 100))
    }
