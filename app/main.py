from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from app.models import NLQRequest
from app.prompt import build_prompt
from app.sqlcoder import run_sqlcoder, load_model
from app.security import validate_sql
from app.athena_client import execute_query
from app.utils import gen_request_id
from app.request_logger import log_request, get_logs, get_log_count
from app.display_hint import get_display_type
from app.chart_formatter import format_for_chart
from app.query_suggestions import generate_query_suggestions, get_schema_summary
from app.input_validator import validate_nlq_input, ValidationResult
from app.rate_limiter import get_rate_limiter, RateLimiter, RateLimitConfig
import json
import os
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Thread pool for model inference (prevents blocking async loop)
_executor = ThreadPoolExecutor(max_workers=4)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    # Startup
    logger.info("[STARTUP] Preloading ML model...")
    load_model()
    logger.info("[STARTUP] Model preloaded successfully! Ready to handle queries.")
    
    # Initialize rate limiter
    rate_limiter = get_rate_limiter()
    logger.info(f"[STARTUP] Rate limiter initialized: {rate_limiter.config.requests_per_second} req/s, burst {rate_limiter.config.burst_size}")
    
    yield
    
    # Shutdown
    logger.info("[SHUTDOWN] Cleaning up...")
    _executor.shutdown(wait=True)
    logger.info("[SHUTDOWN] Cleanup complete.")


app = FastAPI(
    title="NLQ → Athena SQL API",
    version="0.4-refactored",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


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


def get_limiter() -> RateLimiter:
    """Dependency to get rate limiter"""
    return get_rate_limiter()


@app.get("/")
def read_root():
    """Serve the web GUI"""
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "NLQ → Athena SQL API", "version": "0.4-refactored", "gui": "not available"}


@app.get("/health")
def health_check():
    """Health check endpoint"""
    rate_limiter = get_rate_limiter()
    return {
        "status": "healthy",
        "version": "0.4-refactored",
        "rate_limiter": rate_limiter.get_stats()
    }


def _run_model_inference(prompt: str, max_tokens: int) -> dict:
    """Run model inference in thread pool to prevent blocking"""
    return run_sqlcoder(prompt=prompt, max_tokens=max_tokens)


@app.post("/nlq/execute", response_class=PrettyJSONResponse)
async def execute(req: NLQRequest, rate_limiter: RateLimiter = Depends(get_limiter)):
    """
    Execute NLQ to SQL conversion with optional query execution.
    
    Features:
    - Input validation and sanitization
    - Rate limiting
    - Non-blocking model inference
    - Comprehensive error handling
    """
    request_id = req.trace.request_id or gen_request_id()
    start_time = time.time()
    
    try:
        # Step 1: Input Validation
        validation_result = validate_nlq_input(req.text, strict_mode=True)
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid input: {validation_result.error}"
            )
        
        # Use sanitized text
        sanitized_text = validation_result.sanitized_text
        
        # Step 2: Rate Limiting Check
        rate_check = rate_limiter.check_rate_limit()
        if not rate_check.allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Retry after {rate_check.retry_after:.1f} seconds",
                headers={"Retry-After": str(int(rate_check.retry_after) + 1)}
            )

        # Step 3: Determine Athena target and allowed tables
        # Authentication is now handled by external token service
        athena_target = req.execution.athena_target or "peninsula_incident"
        # Use tables from payload if provided, otherwise from ATHENA_TARGETS config
        if req.sql.tables:
            allowed_tables = req.sql.tables
        else:
            from app.athena_config import ATHENA_TARGETS
            target_cfg = ATHENA_TARGETS.get(athena_target, {})
            allowed_tables = target_cfg.get("tables", ["incident_combine"])

        # Step 4: Build Prompt
        prompt = build_prompt(
            text=sanitized_text,
            context=req.context,
            sql=req.sql,
            athena_target=athena_target,
            property_uuid=req.context.property_uuid,
            user_uuid=req.context.user_uuid
        )

        # Step 5: Run Model Inference (non-blocking)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            _run_model_inference,
            prompt,
            req.model.max_tokens
        )

        # Step 5.5: Fix hallucinated table names before validation
        from app.sqlcoder import fix_table_names
        result["query"] = fix_table_names(result["query"], allowed_tables)

        # Step 6: Validate Generated SQL
        sql = validate_sql(
            result["query"],
            allowed_tables,
            req.sql.dialect
        )
        
        # Step 7: Execute Query (if not dry run)
        execution_data = None
        executed = False

        if not req.execution.dry_run:
            execution_data = await loop.run_in_executor(
                _executor,
                lambda: execute_query(
                    sql=sql,
                    target_name=athena_target,
                    max_rows=req.execution.max_rows
                )
            )
            executed = True

        # Step 8: Determine Display Type
        # Use user-provided display type if specified in payload, otherwise auto-detect
        if req.display and req.display.type:
            display_type = req.display.type
            logger.info(f"Using user-specified display type: {display_type}")
        elif executed and execution_data:
            display_type = get_display_type(sql, execution_data, query_text=req.text)
            logger.info(f"Auto-detected display type: {display_type}")
        else:
            display_type = "table"

        # Step 9: Format data for charts if needed
        chart_data = None
        if executed and execution_data and display_type in ["bar", "pie", "line", "metric"]:
            chart_data = format_for_chart(execution_data, display_type)
            logger.info(f"Chart data formatted for {display_type}: {chart_data is not None}")

        total_latency_ms = int((time.time() - start_time) * 1000)

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
                "type": display_type,
                "chart_data": chart_data
            },
            "explanation": result["explanation"],
            "trace": {
                "request_id": request_id,
                "model_latency_ms": result["latency_ms"],
                "total_latency_ms": total_latency_ms,
                "athena_target": athena_target,
                "allowed_tables": allowed_tables,
                "input_warnings": validation_result.warnings
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

    except HTTPException:
        raise
    except ValueError as e:
        # SQL validation errors, permission errors
        error_response = {"success": False, "error": str(e)}
        log_request(
            request_id=request_id,
            request_data=req.dict(),
            response_data=error_response,
            status_code=400,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Query execution errors from Athena should be returned as client-visible SQL errors, not 500.
        error_response = {"success": False, "error": str(e)}
        log_request(
            request_id=request_id,
            request_data=req.dict(),
            response_data=error_response,
            status_code=400,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Unexpected errors - log full traceback
        logger.exception(f"Unexpected error processing request {request_id}")
        error_response = {"success": False, "error": "Internal server error"}
        log_request(
            request_id=request_id,
            request_data=req.dict(),
            response_data=error_response,
            status_code=500,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error. Please try again.")


@app.get("/logs", response_class=PrettyJSONResponse)
def view_logs(limit: int = 100):
    """
    View the last N API request/response logs (max 100).
    """
    return {
        "total_logs": get_log_count(),
        "logs": get_logs(limit=min(limit, 100))
    }


@app.get("/nlq/suggestions", response_class=PrettyJSONResponse)
def get_suggestions(target: str = "peninsula_incident"):
    """
    Get suggested queries based on database schema.
    """
    try:
        suggestions = generate_query_suggestions(target)
        return {
            "target": target,
            "total_suggestions": len(suggestions),
            "suggestions": suggestions
        }
    except Exception as e:
        logger.exception(f"Error getting suggestions for target {target}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/nlq/schema", response_class=PrettyJSONResponse)
def get_schema(target: str = "peninsula_incident"):
    """
    Get database schema summary.
    """
    try:
        summary = get_schema_summary(target)
        return summary
    except Exception as e:
        logger.exception(f"Error getting schema for target {target}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/rate-limit/stats", response_class=PrettyJSONResponse)
def get_rate_limit_stats(rate_limiter: RateLimiter = Depends(get_limiter)):
    """
    Get rate limiter statistics.
    """
    return rate_limiter.get_stats()
