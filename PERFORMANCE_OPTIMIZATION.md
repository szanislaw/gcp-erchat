# Performance Optimization Guide

## Current Performance Bottlenecks

Based on your architecture, here are the main performance bottlenecks:

1. **Model Inference**: ~2-5 seconds (Mistral-7B)
2. **Athena Query Execution**: ~5-15 seconds (depends on data size)
3. **Schema Loading**: ~1-2 seconds (first call only, then cached)
4. **Model Loading**: ~2-3 seconds (startup only)

**Total typical query time**: 7-20 seconds

---

## Quick Wins (Immediate Improvements)

### 1. ✅ **Already Optimized** - Good job!
- Schema caching (✓)
- Athena client caching (✓)
- Model singleton pattern (✓)

### 2. **Use Smaller/Faster Model** (HIGHEST IMPACT)

Replace Mistral-7B with a faster model:

```python
# In app/sqlcoder.py, change model_name to:
model_name = "defog/sqlcoder-7b-2"  # Specialized for SQL, faster
# OR
model_name = "NumbersStation/nsql-llama-2-7B"  # SQL-optimized
```

**Expected improvement**: 30-50% faster inference

### 3. **Reduce Token Limit**

```python
# In API calls, use fewer max_tokens:
"model": {"max_tokens": 256}  # Instead of 512
```

**Expected improvement**: 20-30% faster generation

### 4. **Add Query Result Caching**

Cache common queries to avoid re-execution:

```python
# Add to app/athena_client.py
import hashlib
_QUERY_CACHE = {}

def execute_query(sql: str, target_name: str, max_rows: int):
    # Create cache key
    cache_key = hashlib.md5(f"{sql}:{target_name}:{max_rows}".encode()).hexdigest()
    
    if cache_key in _QUERY_CACHE:
        return _QUERY_CACHE[cache_key]
    
    # ... existing code ...
    
    _QUERY_CACHE[cache_key] = result
    return result
```

**Expected improvement**: Instant response for repeated queries

---

## Medium-Term Improvements

### 5. **Use Athena Query Result Reuse**

Enable result reuse in Athena configuration:

```python
# In app/athena_client.py, add to start_query_execution:
response = client.start_query_execution(
    QueryString=sql,
    QueryExecutionContext={"Database": cfg["database"]},
    ResultConfiguration={
        "OutputLocation": cfg["s3_output"]
    },
    ResultReuseConfiguration={
        'ResultReuseByAgeConfiguration': {
            'Enabled': True,
            'MaxAgeInMinutes': 60  # Reuse results for 1 hour
        }
    }
)
```

**Expected improvement**: 5-10x faster for repeated/similar queries

### 6. **Optimize Athena Polling**

Adjust polling interval based on query complexity:

```python
# In app/athena_client.py, _wait_for_query:
def _wait_for_query(client, query_execution_id: str):
    poll_interval = 0.2  # Start with 200ms
    max_interval = 2.0
    
    while True:
        res = client.get_query_execution(QueryExecutionId=query_execution_id)
        status = res["QueryExecution"]["Status"]["State"]
        
        if status == "SUCCEEDED":
            return
        if status in ("FAILED", "CANCELLED"):
            reason = res["QueryExecution"]["Status"].get("StateChangeReason", "Unknown")
            raise RuntimeError(f"Athena query {status}: {reason}")
        
        time.sleep(poll_interval)
        poll_interval = min(poll_interval * 1.5, max_interval)  # Exponential backoff
```

**Expected improvement**: 10-20% faster for short queries

### 7. **Partition Pruning**

Always use partition columns in WHERE clauses:

```python
# Update prompt.py to emphasize partitions:
"- ALWAYS filter by partition columns (account, property, date) when possible"
"- Example: WHERE date >= '2026-01-01' AND property = 'uuid'"
```

**Expected improvement**: 10-100x faster queries (depends on data size)

---

## Advanced Optimizations

### 8. **Use GPU for Model Inference**

Ensure you're using GPU (already configured with `device_map="auto"`):

```bash
# Check if GPU is being used:
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

If no GPU, consider:
- Using a cloud GPU instance (AWS g4dn, g5)
- Quantization (reduce model to 8-bit or 4-bit)

### 9. **Model Quantization**

Reduce memory and increase speed:

```python
# In app/sqlcoder.py:
from transformers import BitsAndBytesConfig

quantization_config = BitsAndBytesConfig(
    load_in_8bit=True,  # or load_in_4bit=True for even faster
)

_model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=quantization_config,
    device_map="auto"
)
```

**Expected improvement**: 2-4x faster with minimal accuracy loss

### 10. **Async/Parallel Processing**

For multiple queries, process in parallel:

```python
# Use FastAPI background tasks or asyncio
from fastapi import BackgroundTasks
import asyncio

async def execute_query_async(sql, target, max_rows):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, execute_query, sql, target, max_rows)
```

---

## Database-Level Optimizations

### 11. **Create Athena Views**

Pre-create views for common queries:

```sql
CREATE VIEW recent_incidents AS
SELECT * FROM incident_combine
WHERE date >= DATE_ADD('day', -30, CURRENT_DATE);
```

### 12. **Optimize Table Format**

Convert to Parquet/ORC with partitioning:

```sql
CREATE TABLE incident_combine_optimized
WITH (
    format = 'PARQUET',
    partitioned_by = ARRAY['year', 'month', 'property']
)
AS SELECT * FROM incident_combine;
```

**Expected improvement**: 2-10x faster queries

### 13. **Use Athena Workgroups**

Configure workgroups with better resources:

```python
# In AWS Console or CLI:
# - Set query result location
# - Enable result encryption
# - Set bytes scanned per query limits
```

---

## Monitoring & Profiling

### Add Performance Tracking

```python
# In app/main.py, enhance the response:
response = {
    "success": True,
    "sql": {"query": sql, "confidence": result["confidence"]},
    "execution": {"executed": executed, "row_count": ..., "data": ...},
    "trace": {
        "request_id": request_id,
        "latency_ms": result["latency_ms"],
        "breakdown": {
            "model_inference_ms": result["inference_time"],
            "athena_execution_ms": result.get("athena_time"),
            "total_ms": result["latency_ms"]
        }
    }
}
```

---

## Performance Targets

| Optimization Level | Total Query Time | Effort |
|-------------------|------------------|--------|
| **Current** | 7-20 seconds | - |
| **Quick Wins (1-4)** | 4-10 seconds | Low |
| **Medium-Term (5-7)** | 2-5 seconds | Medium |
| **Advanced (8-10)** | 1-3 seconds | High |
| **All + DB Optimizations** | <1 second | Very High |

---

## Recommended Implementation Order

1. ✅ **Reduce max_tokens to 256** (5 min)
2. ✅ **Add query result caching** (30 min)
3. ✅ **Enable Athena result reuse** (15 min)
4. **Optimize partition usage in prompts** (1 hour)
5. **Try sqlcoder-7b-2 model** (30 min)
6. **Implement model quantization** (1 hour)
7. **Consider AWS infrastructure upgrades** (varies)

Start with items 1-3 for immediate 40-60% improvement with minimal effort!
