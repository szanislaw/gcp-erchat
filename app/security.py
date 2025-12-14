import re

FORBIDDEN = re.compile(r"\b(drop|delete|update|insert|alter|truncate)\b", re.I)
ATHENA_UNSUPPORTED = ["distinct on", "returning"]

def validate_sql(sql: str, allowed_tables: list[str], dialect: str):
    if not sql:
        raise ValueError("Empty SQL")

    if FORBIDDEN.search(sql):
        raise ValueError("Forbidden SQL operation")

    if dialect == "athena":
        for kw in ATHENA_UNSUPPORTED:
            if kw in sql.lower():
                raise ValueError(f"Athena does not support: {kw}")

    tables = re.findall(r"from\s+([a-zA-Z_][\w]*)", sql, re.I)
    for t in tables:
        if t not in allowed_tables:
            raise ValueError(f"Table not allowed: {t}")

    return sql
