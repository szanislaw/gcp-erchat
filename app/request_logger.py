from datetime import datetime
from typing import Dict,Any,List
import json,os
from pathlib import Path
import threading
LOG_FILE_PATH=Path(__file__).parent.parent/'logs'/'api_requests.json'
_file_lock=threading.Lock()
def _ensure_log_file_exists():
	LOG_FILE_PATH.parent.mkdir(parents=True,exist_ok=True)
	if not LOG_FILE_PATH.exists():LOG_FILE_PATH.write_text('[]')
def _read_logs_from_file():
	_ensure_log_file_exists()
	try:
		with open(LOG_FILE_PATH,'r')as f:return json.load(f)
	except(json.JSONDecodeError,FileNotFoundError):return[]
def _write_logs_to_file(logs):
	_ensure_log_file_exists()
	with open(LOG_FILE_PATH,'w')as f:json.dump(logs,f,indent=2)
def log_request(request_id,request_data,response_data,status_code,error=None):
	log_entry={'timestamp':datetime.utcnow().isoformat()+'Z','request_id':request_id,'status_code':status_code,'request':request_data,'response':response_data,'error':error}
	with _file_lock:
		logs=_read_logs_from_file();logs.append(log_entry)
		if len(logs)>100:logs=logs[-100:]
		_write_logs_to_file(logs)
def get_logs(limit=100):
	with _file_lock:logs=_read_logs_from_file();logs.reverse();return logs[:limit]
def get_logs_json():return json.dumps(get_logs(),indent=2)
def clear_logs():
	with _file_lock:_write_logs_to_file([])
def get_log_count():
	with _file_lock:logs=_read_logs_from_file();return len(logs)