import uuid

def gen_request_id():
    # to dev when Long implement key
    return f"req-{uuid.uuid4()}"
