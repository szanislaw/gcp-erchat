from app.schema_loader import load_schema, compress_schema


def build_prompt(text, context, sql, athena_target: str) -> str:
    schema = load_schema(athena_target)
    schema_text = compress_schema(schema)

    return f"""You are an expert SQL generator for AWS Athena (PrestoSQL).

STRICT RULES:
- Output ONLY the SQL query, nothing else
- Do NOT include explanations before or after the query
- Do NOT include comments
- Do NOT include markdown code fences like ```sql
- Use PrestoSQL syntax ONLY
- Use ONLY the columns listed below
- Do NOT invent columns
- Do NOT perform cross-database joins
- Prefer partition columns when filtering
- ALWAYS include LIMIT 100

Available tables and schemas:
{schema_text}

Semantic hints:
- For "most recent", prefer bigint timestamp columns such as created_date or incident_time
- Do not use string date columns for recency ordering if bigint timestamps exist

Generate a SQL query for this request:
{text}

Return only the SQL query:""".strip()
