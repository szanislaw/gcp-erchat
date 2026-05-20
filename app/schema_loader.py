_D='schema'
_C='type'
_B='name'
_A='columns'
import logging
from typing import Dict,Any
from app.redshift_config import REDSHIFT_TARGETS,get_connection
logger=logging.getLogger(__name__)
_SCHEMA_CACHE={}
_COLUMN_VALUES_CACHE={}
def load_schema(target_name):
	if target_name in _SCHEMA_CACHE:return _SCHEMA_CACHE[target_name]
	cfg=REDSHIFT_TARGETS.get(target_name)
	if not cfg:raise ValueError(f"Unknown Redshift target: {target_name}")
	schema_name=cfg[_D];schema={};conn=get_connection()
	try:
		with conn.cursor()as cur:
			for table_name in cfg['tables']:cur.execute('SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position',(schema_name,table_name));rows=cur.fetchall();schema[table_name]={_A:[{_B:row[0],_C:row[1]}for row in rows],'partitions':[]}
	finally:conn.close()
	_SCHEMA_CACHE[target_name]=schema;return schema
def compress_schema(schema):
	lines=[]
	for(table,meta)in schema.items():col_str=', '.join(f"{c[_B]} ({c[_C]})"for c in meta[_A]);lines.append(f"- {table}: columns [{col_str}]")
	return'\n'.join(lines)
def schema_to_ddl(schema):
	statements=[]
	for(table_name,meta)in schema.items():
		db=meta.get('database','');full_name=f"{db}.{table_name}"if db else table_name;col_defs=[]
		for col in meta.get(_A,[]):col_defs.append(f"    {col[_B]} {col[_C].upper()}")
		statements.append(f"CREATE TABLE {full_name} (\n"+',\n'.join(col_defs)+'\n);')
	return'\n\n'.join(statements)
def load_column_values(target_name):
	if target_name in _COLUMN_VALUES_CACHE:return _COLUMN_VALUES_CACHE[target_name]
	from app.redshift_config import ENUM_COLUMNS,REDSHIFT_TARGETS;enum_cfg=ENUM_COLUMNS.get(target_name)
	if not enum_cfg:return{}
	target_cfg=REDSHIFT_TARGETS.get(target_name,{});schema=target_cfg.get(_D,'');result={};failed=[];conn=get_connection()
	try:
		with conn.cursor()as cur:
			if schema:cur.execute(f"SET search_path TO {schema}, public")
			for entry in enum_cfg:
				table=entry['table'];limit=entry.get('limit',50)
				for col in entry[_A]:
					try:cur.execute(f"SELECT DISTINCT {col} FROM {table} WHERE {col} IS NOT NULL ORDER BY {col} LIMIT {limit}");values=[row[0]for row in cur.fetchall()if row[0]is not None];result[col]=values
					except Exception as e:logger.warning(f"Could not load distinct values for {table}.{col}: {e}");failed.append(f"{table}.{col}")
	finally:conn.close()
	if not failed:_COLUMN_VALUES_CACHE[target_name]=result
	else:logger.warning(f"Skipping cache for {target_name}: {len(failed)} column(s) failed ({failed})")
	return result