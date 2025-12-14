from fastapi import FastAPI, HTTPException
from app.models import NLQRequest
from app.prompt import build_prompt
from app.sqlcoder import run_sqlcoder
from app.security import validate_sql
from app.athena_client import execute_query
from app.utils import gen_request_id

app = FastAPI(
    title="NLQ → Athena SQL API",
    version="0.3-prototype"
)


@app.post("/nlq/execute")
def execute(req: NLQRequest):
    try:
        request_id = req.trace.request_id or gen_request_id()

        prompt = build_prompt(
            text=req.text,
            context=req.context,
            sql=req.sql,
            athena_target=req.execution.athena_target
        )

        result = run_sqlcoder(
            prompt=prompt,
            max_tokens=req.model.max_tokens
        )

        sql = validate_sql(
            result["query"],
            req.sql.tables,
            req.sql.dialect
        )

        execution_data = None
        executed = False

        if not req.execution.dry_run:
            execution_data = execute_query(
                sql=sql,
                target_name=req.execution.athena_target,
                max_rows=req.execution.max_rows
            )
            executed = True

        return {
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
            "explanation": result["explanation"],
            "trace": {
                "request_id": request_id,
                "latency_ms": result["latency_ms"]
            }
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
