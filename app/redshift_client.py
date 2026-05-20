import hashlib,logging
from typing import Dict,Any
from app.redshift_config import REDSHIFT_TARGETS,get_connection
logger=logging.getLogger(__name__)
_QUERY_CACHE={}
_CACHE_MAX_SIZE=100
def execute_query(sql,target_name,max_rows):
	sql_lower=sql.strip().lower()
	if not(sql_lower.startswith('select')or sql_lower.startswith('with')):raise ValueError('Only SELECT queries are allowed')
	cfg=REDSHIFT_TARGETS.get(target_name)
	if not cfg:raise ValueError(f"Unknown Redshift target: {target_name}")
	cache_key=hashlib.md5(f"{sql}:{target_name}:{max_rows}".encode()).hexdigest()
	if cache_key in _QUERY_CACHE:return _QUERY_CACHE[cache_key]
	schema=cfg['schema']
	try:
		conn=get_connection()
		try:
			with conn.cursor()as cur:cur.execute(f"SET search_path TO {schema}, public");cur.execute(sql);columns=[desc[0]for desc in cur.description]if cur.description else[];rows=cur.fetchmany(max_rows)
		finally:conn.close()
	except Exception as e:raise RuntimeError(f"Redshift query failed: {e}")from e
	data=[dict(zip(columns,(str(v)if v is not None else None for v in row)))for row in rows];normalized={'columns':columns,'rows':data,'row_count':len(data)}
	if len(_QUERY_CACHE)>=_CACHE_MAX_SIZE:_QUERY_CACHE.pop(next(iter(_QUERY_CACHE)))
	_QUERY_CACHE[cache_key]=normalized;return normalized