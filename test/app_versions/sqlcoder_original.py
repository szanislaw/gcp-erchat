import time
import re
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

_model = None
_tokenizer = None

SELECT_REGEX = re.compile(
    r"(select\s+.*?)(;|\Z)",
    re.IGNORECASE | re.DOTALL
)


def load_model():
    global _model, _tokenizer

    if _model is not None:
        return

    print("[BOOT] Loading Qwen-2.5-3b-Text_to_SQL model (specialized for SQL generation)...", flush=True)

    # Qwen-2.5-3b-Text_to_SQL is fine-tuned specifically for text-to-SQL
    # Benefits: Faster (3B vs 7B), Less memory, Specialized training
    # Alternative: "Qwen/Qwen2.5-Coder-7B-Instruct" (general code, larger)
    model_name = "Ellbendls/Qwen-2.5-3b-Text_to_SQL"

    _tokenizer = AutoTokenizer.from_pretrained(model_name)

    _model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map="auto"
    )

    _model.eval()
    print(f"[BOOT] {model_name} loaded successfully!", flush=True)
    print(f"[INFO] Model size: ~3B parameters, optimized for text-to-SQL tasks", flush=True)


def extract_sql(text: str) -> str:
    if not text:
        return ""

    text = text.replace("```sql", "").replace("```", "")

    match = SELECT_REGEX.search(text)
    if not match:
        return ""

    sql = match.group(1).strip()
    sql = re.sub(r"\s+", " ", sql)

    # Only add LIMIT if missing, and cap at 100 for safety
    if " limit " not in sql.lower():
        sql = sql.rstrip(";") + " LIMIT 100"
    else:
        # Extract and cap the limit value at 100
        limit_match = re.search(r'limit\s+(\d+)', sql, re.IGNORECASE)
        if limit_match:
            limit_val = int(limit_match.group(1))
            if limit_val > 100:
                sql = re.sub(r'limit\s+\d+', 'LIMIT 100', sql, flags=re.IGNORECASE)

    return sql


def run_sqlcoder(prompt: str, max_tokens: int):
    load_model()
    start = time.time()

    # Format prompt as chat message for Qwen
    messages = [{"role": "user", "content": prompt}]
    formatted_prompt = _tokenizer.apply_chat_template(
        messages, 
        tokenize=False, 
        add_generation_prompt=True
    )
    
    inputs = _tokenizer(formatted_prompt, return_tensors="pt").to(_model.device)

    outputs = _model.generate(
        **inputs,
        max_new_tokens=max_tokens,
        do_sample=False,
        temperature=0.0,
        top_p=1.0,
        eos_token_id=_tokenizer.eos_token_id,
        pad_token_id=_tokenizer.pad_token_id if _tokenizer.pad_token_id else _tokenizer.eos_token_id
    )

    raw_output = _tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Remove the input prompt from output
    if formatted_prompt in raw_output:
        raw_output = raw_output.replace(formatted_prompt, "").strip()

    print("\n===== QWEN RAW OUTPUT =====")
    print(raw_output)
    print("===== END RAW OUTPUT =====\n")

    sql = extract_sql(raw_output)
    latency_ms = int((time.time() - start) * 1000)

    return {
        "query": sql,
        "confidence": 0.90,
        "latency_ms": latency_ms,
        "explanation": {
            "summary": "SQL generated for Athena execution.",
            "assumptions": []
        }
    }
