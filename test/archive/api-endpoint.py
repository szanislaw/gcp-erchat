from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
import uuid
import time
import re

# ─────────────────────────────────────────────
# App
# ─────────────────────────────────────────────
app = FastAPI(
    title="NLQ SQL API",
    version="1.0",
    description="Natural language → SQL API (SQLCoder integration pending)"
)

# ─────────────────────────────────────────────
# Models (API contract — DO NOT CHANGE LATER)
# ─────────────────────────────────────────────

class Context(BaseModel):
    property_uuid: str
    location_name: Optional[str]
    user_role: str
    language: Literal["en", "zh", "ms", "ta"] = "en"

class SQLConfig(BaseModel):
    dialect: Literal["postgres", "mysql"]
    schema: str
    tables: List[str]

class ExecutionConfig(BaseModel):
    dry_run: bool = True
    max_rows: int = 100
    timeout_ms: int = 5000

class ModelConfig(BaseModel):
    name: str = "defog/sqlcoder-7b-2"
    temperature: float = 0.0
    max_tokens: int = 512

class Trace(BaseModel):
    request_id: Optional[str]
    source: str = "fcs1-ui"

class NLQRequest(BaseModel):
    text: str = Field(..., min_length=3)
    context: Context
    sql: SQLConfig
    execution: ExecutionConfig
    model: ModelConfig
    trace: Trace

# ─────────────────────────────────────────────
# Safety
# ─────────────────────────────────────────────

FORBIDDEN_SQL = re.compile(r"\b(drop|delete|update|insert|alter)\b", re.I)

def validate_sql(query: str, allowed_tables: list[str]) -> str:
    if not query:
        raise ValueError("No SQL generated")

    if FORBIDDEN_SQL.search(query):
        raise ValueError("Forbidden SQL operation detected")

    for table in re.findall(r"from\s+(\w+)", query, re.I):
        if table not in allowed_tables:
            raise ValueError(f"Table not allowed: {table}")

    return query

# ─────────────────────────────────────────────
# SQLCoder STUB (replace later)
# ─────────────────────────────────────────────

def run_sqlcoder_stub(prompt: str):
    """
    Placeholder implementation.
    Safe, deterministic, auditable.
    """
    return {
        "query": (
            "SELECT job_no, job_status "
            "FROM job_order "
            "WHERE property_uuid = '<PROPERTY_UUID>' "
            "LIMIT 10;"
        ),
        "confidence": 0.01,
        "latency_ms": 5,
        "explanation": {
            "summary": "Stubbed response. SQLCoder not yet enabled.",
            "assumptions": [
                "This SQL is a placeholder",
                "Model integration pending"
            ]
        }
    }

# ─────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────

@app.post("/nlq/execute")
def execute_nlq(req: NLQRequest):
    start = time.time()
    trace_id = req.trace.request_id or str(uuid.uuid4())

    try:
        # Build prompt (kept simple for stub phase)
        prompt = f"""
User request:
{req.text}

Property UUID: {req.context.property_uuid}
Allowed tables: {", ".join(req.sql.tables)}

Generate a single SELECT query only.
""".strip()

        result = run_sqlcoder_stub(prompt)

        sql = validate_sql(result["query"], req.sql.tables)

        return {
            "success": True,
            "sql": {
                "query": sql,
                "confidence": result["confidence"]
            },
            "execution": {
                "executed": False,
                "row_count": None
            },
            "explanation": result["explanation"],
            "trace": {
                "request_id": trace_id,
                "latency_ms": int((time.time() - start) * 1000)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ─────────────────────────────────────────────
# Health check (for GCP / LB)
# ─────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}
