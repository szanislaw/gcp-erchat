from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class Context(BaseModel):
    account_uuid: str  # REQUIRED for access control
    property_uuid: str  # REQUIRED for access control
    user_uuid: Optional[str] = None  # OPTIONAL - for user-level table access control
    user_role: Optional[str] = None
    location_name: Optional[str] = None
    language: Literal["en", "zh", "ms", "ta"] = "en"


class SQLConfig(BaseModel):
    # Lock to Athena for now
    # Tables are determined by account/property UUID permissions
    dialect: Literal["athena"]


class ExecutionConfig(BaseModel):
    dry_run: bool = True
    max_rows: int = 100
    timeout_ms: int = 5000
    # athena_target determined by account/property UUID permissions


class ModelConfig(BaseModel):
    name: str = "Ellbendls/Qwen-2.5-3b-Text_to_SQL"
    temperature: float = 0.0
    max_tokens: int = 256  # Usually sufficient for SQL queries


class DisplayConfig(BaseModel):
    """
    UI display recommendations for query results
    """
    type: Literal["table", "metric", "bar", "line", "pie", "card", "list"] = "table"
    title: Optional[str] = None
    subtitle: Optional[str] = None
    chart_config: Optional[dict] = None  # For additional chart-specific settings


class Trace(BaseModel):
    request_id: Optional[str] = None
    source: str = "fcs1-ui"


class NLQRequest(BaseModel):
    text: str = Field(..., min_length=3)
    context: Context
    sql: SQLConfig
    execution: ExecutionConfig
    model: ModelConfig
    display: Optional[DisplayConfig] = None
    trace: Trace
