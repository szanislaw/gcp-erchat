import os
import redshift_connector


ENUM_COLUMNS = {
    "default": [
        {"table": "master_maintenance_status", "columns": ["status_name"], "limit": 50},
        {"table": "master_job_priority", "columns": ["priority_name"], "limit": 50},
    ],
    "incident": [
        {"table": "mv_recovery_all", "columns": ["status_name"], "limit": 50},
        {"table": "mv_recovery_all", "columns": ["severity_name"], "limit": 50},
        {"table": "mv_recovery_all", "columns": ["category_name"], "limit": 50},
        {"table": "mv_recovery_all", "columns": ["incident_name"], "limit": 100},
        {"table": "mv_recovery_all", "columns": ["temperament_text"], "limit": 50},
        {"table": "mv_recovery_all", "columns": ["property_name"], "limit": 50},
    ],
}

REDSHIFT_TARGETS = {
    "default": {
        "schema": os.getenv("REDSHIFT_SCHEMA", "nxg_107747471_q2sj"),
        "tables": [
            "maintenance_order",
            "master_maintenance_status",
            "master_job_priority",
            "property_location",
        ],
    },
    "incident": {
        "schema": os.getenv("REDSHIFT_INCIDENT_SCHEMA", "public"),
        "tables": [
            "mv_recovery_all",
        ],
    },
}

def get_connection() -> redshift_connector.Connection:
    """Open a new password-authenticated Redshift connection. Caller must close it."""
    return redshift_connector.connect(
        host=os.getenv("REDSHIFT_HOST", ""),
        port=int(os.getenv("REDSHIFT_PORT", "5439")),
        database=os.getenv("REDSHIFT_DBNAME", "dev"),
        user=os.getenv("REDSHIFT_USER", ""),
        password=os.getenv("REDSHIFT_PASSWORD", ""),
    )
