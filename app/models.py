from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class Context(BaseModel):
    # Optional because Athena tables are not property-scoped yet
    property_uuid: Optional[str] = None
    user_role: Optional[str] = None
    location_name: Optional[str] = None
    language: Literal["en", "zh", "ms", "ta"] = "en"


class SQLConfig(BaseModel):
    # Lock to Athena for now
    dialect: Literal["athena"]
    tables: List[str]


class ExecutionConfig(BaseModel):
    dry_run: bool = True
    max_rows: int = 100
    timeout_ms: int = 5000
    athena_target: str  # REQUIRED


class ModelConfig(BaseModel):
    name: str = "defog/sqlcoder-7b-2"
    temperature: float = 0.0
    max_tokens: int = 512


class Trace(BaseModel):
    request_id: Optional[str] = None
    source: str = "fcs1-ui"


class NLQRequest(BaseModel):
    text: str = Field(..., min_length=3)
    context: Context
    sql: SQLConfig
    execution: ExecutionConfig
    model: ModelConfig
    trace: Trace
