import uuid

def gen_request_id():
    return f"req-{uuid.uuid4()}"
