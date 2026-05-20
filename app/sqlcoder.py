_J='extract'
_I='department'
_H='months'
_G='created_date'
_F='maintenance_order'
_E=None
_D='year'
_C='day'
_B='month'
_A='week'
import time,re,os,torch,threading,hashlib
from transformers import AutoTokenizer,AutoModelForCausalLM
from typing import Dict
import logging
os.environ.setdefault('PYTORCH_CUDA_ALLOC_CONF','expandable_segments:True')
logger=logging.getLogger(__name__)
_model_lock=threading.Lock()
_model=_E
_tokenizer=_E
SELECT_REGEX=re.compile('(select\\s+.*?)(;|\\Z)',re.IGNORECASE|re.DOTALL)
_sql_cache={}
_CACHE_MAX_SIZE=500
_KNOWN_TABLES=frozenset({_F,'master_maintenance_status','master_job_priority','property_location'})
def _get_cache_key(prompt,max_tokens):return hashlib.md5(f"{prompt}::{max_tokens}".encode()).hexdigest()
def load_model():
	C='auto';B='max_memory';A='device_map';global _model,_tokenizer
	with _model_lock:
		if _model is not _E:return
		model_name='defog/sqlcoder-7b-2';use_quantization=os.getenv('USE_QUANTIZATION','false').lower()=='true';gpu_memory_cap=os.getenv('GPU_MEMORY_CAP','11GiB');max_memory={0:gpu_memory_cap,'cpu':'32GiB'}
		if use_quantization:from transformers import BitsAndBytesConfig;quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_compute_dtype=torch.float16);logger.info(f"[BOOT] Loading {model_name} (4-bit quantized, gpu_cap={gpu_memory_cap})...");kwargs={'quantization_config':quantization_config,A:C,B:max_memory}
		else:logger.info(f"[BOOT] Loading {model_name} (float16, gpu_cap={gpu_memory_cap})...");kwargs={'torch_dtype':torch.float16,A:C,B:max_memory}
		_tokenizer=AutoTokenizer.from_pretrained(model_name);_model=AutoModelForCausalLM.from_pretrained(model_name,**kwargs);device=next(_model.parameters()).device;logger.info(f"[BOOT] {model_name} loaded on {device} (quantized={use_quantization})")
_TIMESTAMP_COLS=frozenset({_G,'completed_date','cancelled_date','assigned_date','modified_date'})
def fix_date_parse_to_to_date(sql):
	if not sql or'date_parse'not in sql.lower():return sql
	def _replace(match):
		col=match.group(1);col_bare=col.split('.')[-1].lower()
		if col_bare in _TIMESTAMP_COLS:return col
		return f"TO_DATE({col}, 'YYYY-MM-DD')"
	fixed=re.sub("date_parse\\s*\\(\\s*(\\w+(?:\\.\\w+)?)(?:::text)?\\s*,\\s*'%Y-%m-%d'\\s*\\)",_replace,sql,flags=re.IGNORECASE)
	if fixed!=sql:logger.info('Fixed date_parse() → stripped cast or TO_DATE()')
	return fixed
def fix_interval_to_dateadd(sql):
	if not sql or'interval'not in sql.lower():return sql
	_UNIT_MAP={_C:_C,'days':_C,_A:_A,'weeks':_A,_B:_B,_H:_B,_D:_D,'years':_D}
	def _replace(match):date_expr=match.group(1).strip();n_str=match.group(2);unit_raw=match.group(3).lower();unit=_UNIT_MAP.get(unit_raw,unit_raw);n=int(n_str);return f"DATEADD({unit}, -{n}, {date_expr})"
	fixed=re.sub("(\\w+(?:\\s*\\(\\s*\\))?)\\s*-\\s*INTERVAL\\s+\\'(\\d+)\\s+(\\w+)\\'",_replace,sql,flags=re.IGNORECASE)
	if fixed!=sql:logger.info('Fixed INTERVAL subtraction → DATEADD()')
	return fixed
def fix_date_add_to_dateadd(sql):
	if not sql or'date_add'not in sql.lower():return sql
	_UNIT_MAP={_C:_C,'days':_C,_A:_A,'weeks':_A,_B:_B,_H:_B,_D:_D,'years':_D}
	def _replace(match):unit_raw=match.group(1).strip('\'"').lower();unit=_UNIT_MAP.get(unit_raw,unit_raw);n=match.group(2);date_expr=match.group(3).strip();return f"DATEADD({unit}, {n}, {date_expr})"
	fixed=re.sub('date_add\\s*\\(\\s*[\'\\"](\\w+)[\'\\"],\\s*(-?\\d+)\\s*,\\s*([^)]+)\\)',_replace,sql,flags=re.IGNORECASE)
	if fixed!=sql:logger.info('Converted date_add() → DATEADD()')
	return fixed
def fix_main_table_fk_names(sql):
	if not sql:return sql
	has_status_join=bool(re.search('\\bJOIN\\s+master_maintenance_status\\b',sql,re.IGNORECASE));has_priority_join=bool(re.search('\\bJOIN\\s+master_job_priority\\b',sql,re.IGNORECASE))
	def _status_replace(match):
		if has_status_join:return match.group(0)
		alias,val=match.group(1),match.group(2);return f"{alias}.status = (SELECT status_id FROM master_maintenance_status WHERE status_name = '{val}')"
	def _priority_replace(match):
		if has_priority_join:return match.group(0)
		alias,val=match.group(1),match.group(2);return f"{alias}.priority = (SELECT priority_id FROM master_job_priority WHERE priority_name = '{val}')"
	original=sql;sql=re.sub("\\b(\\w+)\\.status_name\\s*=\\s*\\'([^\\']+)\\'",_status_replace,sql,flags=re.IGNORECASE);sql=re.sub("\\b(\\w+)\\.priority_name\\s*=\\s*\\'([^\\']+)\\'",_priority_replace,sql,flags=re.IGNORECASE)
	if sql!=original:logger.info('Fixed m.status_name/m.priority_name → FK subquery lookup')
	return sql
def fix_spurious_department_join(sql):
	if not sql or _I not in sql.lower():return sql
	logger.debug(f"fix_spurious_department_join input: {repr(sql[:300])}");original=sql;sql=re.sub('\\b(?:LEFT\\s+|INNER\\s+|RIGHT\\s+)?JOIN\\s+department\\s+(?:AS\\s+)?\\w+\\s+ON\\s+\\w+\\.department_name\\s*=\\s*\\w+\\.department_name\\b','',sql,flags=re.IGNORECASE)
	if sql==original:
		dept_join_match=re.search('\\b(?:LEFT\\s+|INNER\\s+|RIGHT\\s+)?JOIN\\s+department\\s+(?:AS\\s+)?(\\w+)\\s+ON\\s+\\w+\\.department_uuid\\s*=\\s*\\1\\.department_uuid\\b',sql,flags=re.IGNORECASE)
		if dept_join_match:
			alias=dept_join_match.group(1)
			if not re.search(rf"\b{re.escape(alias)}\.department_name\b",sql,re.IGNORECASE):sql=sql[:dept_join_match.start()]+sql[dept_join_match.end():];logger.info(f"Removed spurious JOIN department (alias '{alias}' never selected)")
	if sql==original:return sql
	sql=re.sub("\\bWHERE\\s+\\w+\\.department_name\\s*=\\s*\\'[^\\']+\\'\\s+AND\\s+",'WHERE ',sql,flags=re.IGNORECASE);sql=re.sub("\\s+AND\\s+\\w+\\.department_name\\s*=\\s*\\'[^\\']+\\'",'',sql,flags=re.IGNORECASE);sql=re.sub("\\bWHERE\\s+\\w+\\.department_name\\s*=\\s*\\'[^\\']+\\'\\s*$",'',sql,flags=re.IGNORECASE);sql=re.sub('\\s{2,}',' ',sql).strip();logger.info("Removed spurious JOIN department ON m.department_name (column doesn't exist)");return sql
def fix_snapshotdate(sql):
	if not sql or'snapshotdate'not in sql.lower():return sql
	fixed=re.sub('\\bsnapshotdate\\b',_G,sql,flags=re.IGNORECASE)
	if fixed!=sql:logger.info('Fixed hallucinated snapshotdate → created_date')
	fixed=re.sub("\\bTO_DATE\\s*\\(\\s*([\\w.]+)\\s*,\\s*'[^']+'\\s*\\)",'\\1',fixed,flags=re.IGNORECASE);return fixed
def fix_department_column(sql):
	if _I not in sql.lower():return sql
	fixed=re.sub('\\b(\\w+)\\.department\\b(?!_)','\\1.department_name',sql,flags=re.IGNORECASE)
	if fixed!=sql:logger.info('Fixed hallucinated .department → .department_name')
	return fixed
def fix_dateadd_quoted_unit(sql):
	if not sql or'dateadd'not in sql.lower():return sql
	fixed=re.sub("\\bDATEADD\\s*\\(\\s*'(\\w+)'\\s*,",'DATEADD(\\1,',sql,flags=re.IGNORECASE)
	if fixed!=sql:logger.info('Fixed DATEADD quoted unit → unquoted')
	return fixed
def fix_date_part_this_period(sql):
	if not sql or'date_part'not in sql.lower():return sql
	for period in(_B,_A):
		p1=re.compile(rf"date_part\s*\(\s*'{period}'\s*,\s*([\w.]+)\s*\)\s*=\s*date_part\s*\(\s*'{period}'\s*,\s*CURRENT_DATE\s*\)\s+AND\s+date_part\s*\(\s*'year'\s*,\s*[\w.]+\s*\)\s*=\s*date_part\s*\(\s*'year'\s*,\s*CURRENT_DATE\s*\)",re.IGNORECASE);m=p1.search(sql)
		if m:col=m.group(1);sql=p1.sub(f"{col} >= DATE_TRUNC('{period}', CURRENT_DATE)",sql);logger.info(f"Fixed date_part '{period}' pair (period-first) → DATE_TRUNC");continue
		p2=re.compile(rf"date_part\s*\(\s*'year'\s*,\s*([\w.]+)\s*\)\s*=\s*date_part\s*\(\s*'year'\s*,\s*CURRENT_DATE\s*\)\s+AND\s+date_part\s*\(\s*'{period}'\s*,\s*[\w.]+\s*\)\s*=\s*date_part\s*\(\s*'{period}'\s*,\s*CURRENT_DATE\s*\)",re.IGNORECASE);m=p2.search(sql)
		if m:col=m.group(1);sql=p2.sub(f"{col} >= DATE_TRUNC('{period}', CURRENT_DATE)",sql);logger.info(f"Fixed date_part '{period}' pair (year-first) → DATE_TRUNC")
		p_last=re.compile(rf"date_part\s*\(\s*'{period}'\s*,\s*([\w.]+)\s*\)\s*=\s*date_part\s*\(\s*'{period}'\s*,\s*CURRENT_DATE\s*\)\s*-\s*1(?:\s+AND\s+date_part\s*\(\s*'year'\s*,\s*[\w.]+\s*\)\s*=\s*date_part\s*\(\s*'year'\s*,\s*CURRENT_DATE\s*\))?",re.IGNORECASE);m=p_last.search(sql)
		if m:col=m.group(1);sql=p_last.sub(f"{col} >= DATEADD({period}, -1, DATE_TRUNC('{period}', CURRENT_DATE)) AND {col} < DATE_TRUNC('{period}', CURRENT_DATE)",sql);logger.info(f"Fixed date_part last-{period} arithmetic → DATEADD range")
	return sql
def fix_extract_week_trend(sql):
	if not sql or _J not in sql.lower()or _A not in sql.lower():return sql
	col_match=re.search('EXTRACT\\s*\\(\\s*WEEK\\s+FROM\\s+([\\w.]+)\\s*\\)',sql,re.IGNORECASE)
	if not col_match:return sql
	col=col_match.group(1);fixed=re.sub('EXTRACT\\s*\\(\\s*YEAR\\s+FROM\\s+[\\w.]+\\s*\\)\\s*AS\\s+\\w+\\s*,\\s*EXTRACT\\s*\\(\\s*WEEK\\s+FROM\\s+[\\w.]+\\s*\\)\\s*AS\\s+\\w+',f"DATE_TRUNC('week', {col}) AS week_start",sql,flags=re.IGNORECASE);_WEEK_ALIASES=frozenset({'YEAR','WEEK','YEAR_NUM','WEEK_NUM'});fixed=re.sub('(GROUP\\s+BY\\s+)(\\w+)\\s*,\\s*(\\w+)',lambda m:f"{m.group(1)}DATE_TRUNC('week', {col})"if m.group(2).upper()in _WEEK_ALIASES or m.group(3).upper()in _WEEK_ALIASES else m.group(0),fixed,flags=re.IGNORECASE);fixed=re.sub('ORDER\\s+BY\\s+(?:\\w+\\s*,\\s*)*(?:YEAR|WEEK|YEAR_NUM|WEEK_NUM)\\b[^)]*?(?=\\s*LIMIT|\\s*$)',f"ORDER BY DATE_TRUNC('week', {col})",fixed,flags=re.IGNORECASE)
	if fixed!=sql:logger.info("Fixed EXTRACT(YEAR/WEEK) trend → DATE_TRUNC('week', col)")
	return fixed
def fix_scalar_subquery_eq(sql):
	if not sql or'(select'not in sql.lower():return sql
	fixed=re.sub('\\s*=\\s*\\(\\s*(SELECT\\s+)',' IN (\\1',sql,flags=re.IGNORECASE)
	if fixed!=sql:logger.info('Fixed scalar subquery: = (SELECT ...) → IN (SELECT ...)')
	return fixed
def fix_status_case(sql):
	if not sql:return sql
	fixed=re.sub("(status_name\\s*(?:=|IN\\s*\\())\\s*'(?:Open|open)'","\\1'pending'",sql,flags=re.IGNORECASE);fixed=re.sub("(status_name\\s*=\\s*)'[Oo]pen'","\\1IN ('pending', 'delayed', 'acknowledged')",fixed,flags=re.IGNORECASE)
	for val in('Completed','Cancelled','Pending','Delayed','Acknowledged','In Progress'):fixed=re.sub(rf"(status_name\s*=\s*)'{re.escape(val)}'",f"\\g<1>'{val.lower()}'",fixed,flags=re.IGNORECASE)
	for val in('High','Low','Medium','Normal','Urgent','Critical'):fixed=re.sub(rf"(priority_name\s*=\s*)'{re.escape(val)}'",f"\\g<1>'{val.lower()}'",fixed,flags=re.IGNORECASE)
	if fixed!=sql:logger.info('Normalized status/priority values to lowercase')
	return fixed
def fix_unaliased_table_ref(sql):
	if not sql or _F not in sql.lower():return sql
	if not re.search('\\bmaintenance_order\\s+(?:AS\\s+)?m\\b',sql,re.IGNORECASE):return sql
	fixed=re.sub('\\bmaintenance_order\\.(\\w+)\\b','m.\\1',sql,flags=re.IGNORECASE)
	if fixed!=sql:logger.info('Fixed unaliased maintenance_order.col → m.col')
	return fixed
def fix_year_extract_comparison(sql):
	if not sql or _J not in sql.lower():return sql
	fixed=re.sub('(EXTRACT\\s*\\(\\s*YEAR\\s+FROM\\s+[\\w.]+\\s*\\))\\s*=\\s*DATE_TRUNC\\s*\\([^)]+\\)','\\1 = EXTRACT(YEAR FROM CURRENT_DATE)',sql,flags=re.IGNORECASE)
	if fixed!=sql:logger.info('Fixed EXTRACT(YEAR) = DATE_TRUNC() → = EXTRACT(YEAR FROM CURRENT_DATE)')
	return fixed
def inject_property_filter(sql,property_col,property_uuids):
	if not sql or not property_col or not property_uuids:return sql
	if any(u in sql for u in property_uuids):return sql
	uuid_list=', '.join(f"'{u}'"for u in property_uuids);filter_clause=f"{property_col} IN ({uuid_list})";where_match=re.search('\\bWHERE\\b',sql,re.IGNORECASE)
	if where_match:insert_pos=where_match.end();sql=sql[:insert_pos]+f" {filter_clause} AND"+sql[insert_pos:]
	else:
		insert_match=re.search('\\b(GROUP\\s+BY|ORDER\\s+BY|LIMIT)\\b',sql,re.IGNORECASE)
		if insert_match:sql=sql[:insert_match.start()]+f"WHERE {filter_clause} "+sql[insert_match.start():]
		else:sql=sql.rstrip(';')+f" WHERE {filter_clause}"
	logger.info(f"Injected missing property filter: {filter_clause}");return sql
def fix_property_column(sql,correct_col,property_uuids):
	if not sql or not correct_col or not property_uuids:return sql
	pattern=re.compile('(\\b\\w+\\.)?(property\\w*)\\s+(IN\\s*\\([^)]+\\))',re.IGNORECASE)
	def _replace(match):
		alias=match.group(1)or'';col=match.group(2);in_clause=match.group(3)
		if col.lower()!=correct_col.lower()and any(u in in_clause for u in property_uuids):logger.info(f"Fixed hallucinated property column: {col} → {correct_col}");return f"{alias}{correct_col} {in_clause}"
		return match.group(0)
	return pattern.sub(_replace,sql)
def fix_invalid_extract_from_table(sql):
	def _replace(match):
		unit=match.group(1).lower();target=match.group(2).lower()
		if target in _KNOWN_TABLES:logger.warning(f"Fixed hallucinated EXTRACT({unit} FROM {target}) → DATE_TRUNC('week', CURRENT_DATE)");return"DATE_TRUNC('week', CURRENT_DATE)"
		return match.group(0)
	return re.sub('\\bEXTRACT\\s*\\(\\s*(\\w+)\\s+FROM\\s+(\\w+)\\s*\\)',_replace,sql,flags=re.IGNORECASE)
def fix_impossible_this_period_filter(sql):
	for period in(_A,_B):
		has_lower=re.search(rf"created_date\s*>=\s*DATE_TRUNC\s*\(\s*'{period}'\s*,\s*CURRENT_DATE\s*\)",sql,re.IGNORECASE)
		if not has_lower:continue
		sql=re.sub(rf"\s+AND\s+created_date\s*<\s*DATE_TRUNC\s*\(\s*'{period}'\s*,\s*CURRENT_DATE\s*\)",'',sql,flags=re.IGNORECASE)
	return sql
def fix_last_week_filter(sql,question_text):
	A="created_date >= DATEADD(week, -1, DATE_TRUNC('week', CURRENT_DATE)) AND created_date < DATE_TRUNC('week', CURRENT_DATE)"
	if not question_text or'last week'not in question_text.lower():return sql
	original=sql
	if re.search('DATEADD\\s*\\(\\s*day\\s*,\\s*-7',sql,re.IGNORECASE):pattern=re.compile("created_date\\s*>=\\s*DATEADD\\s*\\(\\s*day\\s*,\\s*-7\\s*,\\s*CURRENT_DATE\\s*\\)(?:\\s+AND\\s+created_date\\s*<\\s*DATE_TRUNC\\s*\\(\\s*'day'\\s*,\\s*CURRENT_DATE\\s*\\))?",re.IGNORECASE);sql=pattern.sub(A,sql)
	if re.search("date_part\\s*\\(\\s*'week'",sql,re.IGNORECASE):
		sql=re.sub("date_part\\s*\\(\\s*'year'\\s*,\\s*[\\w.]+\\s*\\)\\s*=\\s*date_part\\s*\\(\\s*'year'\\s*,\\s*CURRENT_DATE\\s*\\)\\s+AND\\s+date_part\\s*\\(\\s*'week'\\s*,\\s*[\\w.]+\\s*\\)\\s*=\\s*[^A-Z\\s][^\\s]*",A,sql,flags=re.IGNORECASE)
		if sql==original:sql=re.sub("\\bdate_part\\s*\\(\\s*'week'\\s*,\\s*([\\w.]+)\\s*\\)\\s*=\\s*\\S+","\\1 >= DATEADD(week, -1, DATE_TRUNC('week', CURRENT_DATE)) AND \\1 < DATE_TRUNC('week', CURRENT_DATE)",sql,flags=re.IGNORECASE)
	if sql!=original:logger.info("Fixed 'last week' filter → Mon–Sun calendar boundary")
	return sql
def fix_table_names(sql,allowed_tables=_E):
	A='\\b'
	if not sql or not allowed_tables:return sql
	for table in allowed_tables:
		pattern=re.compile('(?<!\\.)'+A+re.escape(table)+'_[a-zA-Z0-9_]+\\b',re.IGNORECASE)
		for match in pattern.findall(sql):
			if match.lower()not in[t.lower()for t in allowed_tables]:logger.info(f"Fixed hallucinated table name: {match} → {table}");sql=re.sub('(?<!\\.)\\b'+re.escape(match)+A,table,sql,flags=re.IGNORECASE)
	primary_table=allowed_tables[0];allowed_lower={t.lower()for t in allowed_tables};cte_aliases={m.lower()for m in re.findall('\\b(\\w+)\\s+AS\\s*\\(',sql,re.IGNORECASE)}
	def _replace_unknown_from(match):
		keyword=match.group(1);table_name=match.group(2)
		if table_name.lower()in allowed_lower or table_name.lower()in cte_aliases:return match.group(0)
		if keyword.upper()=='FROM':
			pre=sql[:match.start()]
			if pre.count('(')>pre.count(')'):return match.group(0)
		logger.warning(f"Replacing unknown table '{table_name}' with '{primary_table}'");return f"{keyword} {primary_table}"
	sql=re.sub('\\b(FROM|JOIN)\\s+(\\w+)\\b',_replace_unknown_from,sql,flags=re.IGNORECASE);return sql
def extract_sql(text):
	A='[SQL]'
	if not text:return''
	if A in text:text=text.split(A)[-1]
	text=text.replace('```sql','').replace('```','');cte_match=re.search('\\b(with\\s+\\w.+)',text,re.IGNORECASE|re.DOTALL);select_match=SELECT_REGEX.search(text)
	if cte_match and(not select_match or cte_match.start()<=select_match.start()):sql=cte_match.group(1).split(';')[0].strip()
	elif select_match:sql=select_match.group(1).strip()
	else:return''
	sql=re.sub('\\s+',' ',sql);sql=fix_date_parse_to_to_date(sql);sql=fix_date_add_to_dateadd(sql);sql=fix_interval_to_dateadd(sql);sql=fix_snapshotdate(sql);sql=fix_unaliased_table_ref(sql);sql=fix_dateadd_quoted_unit(sql);sql=fix_date_part_this_period(sql);sql=fix_extract_week_trend(sql);sql=fix_scalar_subquery_eq(sql);sql=fix_status_case(sql);sql=fix_department_column(sql);sql=fix_year_extract_comparison(sql)
	if' limit 'not in sql.lower():sql=sql.rstrip(';')+' LIMIT 100'
	else:
		limit_match=re.search('limit\\s+(\\d+)',sql,re.IGNORECASE)
		if limit_match and int(limit_match.group(1))>100:sql=re.sub('limit\\s+\\d+','LIMIT 100',sql,flags=re.IGNORECASE)
	return sql
def run_sqlcoder(prompt,max_tokens):
	C=False;B='latency_ms';A='from_cache';cache_key=_get_cache_key(prompt,max_tokens)
	if cache_key in _sql_cache:cached=_sql_cache[cache_key].copy();cached[A]=True;cached[B]=0;logger.debug(f"SQL cache hit for key {cache_key[:8]}...");return cached
	load_model();start=time.time()
	with _model_lock:
		torch.cuda.empty_cache();inputs=_tokenizer(prompt,return_tensors='pt').to(_model.device);input_length=inputs['input_ids'].shape[1]
		with torch.inference_mode():outputs=_model.generate(**inputs,max_new_tokens=max_tokens,do_sample=C,num_beams=1,eos_token_id=_tokenizer.eos_token_id,pad_token_id=_tokenizer.pad_token_id if _tokenizer.pad_token_id else _tokenizer.eos_token_id)
		raw_output=_tokenizer.decode(outputs[0][input_length:],skip_special_tokens=True)
	logger.debug(f"Raw model output: {raw_output[:200]}...");sql=extract_sql(raw_output);latency_ms=int((time.time()-start)*1000);result={'query':sql,'confidence':.9,B:latency_ms,'explanation':{'summary':'SQL generated for Redshift execution.','assumptions':[]},A:C}
	if sql:
		if len(_sql_cache)>=_CACHE_MAX_SIZE:del _sql_cache[next(iter(_sql_cache))]
		_sql_cache[cache_key]=result.copy()
	return result
def clear_sql_cache():global _sql_cache;_sql_cache={};logger.info('SQL cache cleared')
def get_cache_stats():return{'size':len(_sql_cache),'max_size':_CACHE_MAX_SIZE}