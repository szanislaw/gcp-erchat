import re
from typing import List,Set
FORBIDDEN=re.compile('\\b(drop|delete|update|insert|alter|truncate|grant|revoke|create)\\b',re.I)
REDSHIFT_UNSUPPORTED=['distinct on','returning','for update','for share']
TABLE_PATTERNS=['\\bfrom\\s+([a-zA-Z_][\\w]*)','\\bjoin\\s+([a-zA-Z_][\\w]*)','\\binner\\s+join\\s+([a-zA-Z_][\\w]*)','\\bleft\\s+(?:outer\\s+)?join\\s+([a-zA-Z_][\\w]*)','\\bright\\s+(?:outer\\s+)?join\\s+([a-zA-Z_][\\w]*)','\\bfull\\s+(?:outer\\s+)?join\\s+([a-zA-Z_][\\w]*)','\\bcross\\s+join\\s+([a-zA-Z_][\\w]*)','\\bnatural\\s+join\\s+([a-zA-Z_][\\w]*)']
SQL_KEYWORDS={'select','from','where','and','or','not','in','is','null','true','false','as','on','using','group','by','order','having','limit','offset','union','intersect','except','case','when','then','else','end','cast','between','like','ilike','exists','any','all','distinct','asc','desc','nulls','first','last','over','partition','row','rows','range','preceding','following','current','unbounded','lateral','cross','inner','outer','left','right','full','natural','join','with','recursive','values','default','set','coalesce','greatest','least','date','time','timestamp','interval','the','a','an','other','another','this','that','these','those','each','every','some','many','few','several','both','either','neither','year','month','day','hour','minute','second','week','quarter'}
def extract_tables(sql):
	if not sql:return set()
	found_tables=set();sql_scrubbed=re.sub('\\b(?:EXTRACT|SUBSTRING)\\s*\\([^)]+\\)','__FUNC__',sql,flags=re.IGNORECASE);sql_lower=sql_scrubbed.lower()
	for pattern in TABLE_PATTERNS:
		matches=re.findall(pattern,sql_lower,re.IGNORECASE)
		for match in matches:
			match=match.strip()
			if not match:continue
			if match.lower()in SQL_KEYWORDS:continue
			if not re.match('^[a-zA-Z_][a-zA-Z0-9_]*$',match):continue
			if len(match)<=2:continue
			if match.lower()in{'current_date','current_time','current_timestamp','localtime','localtimestamp','now'}:continue
			found_tables.add(match.lower())
	return found_tables
def validate_sql(sql,allowed_tables,dialect):
	if not sql:raise ValueError('Empty SQL')
	sql_stripped=sql.strip()
	if FORBIDDEN.search(sql_stripped):forbidden_match=FORBIDDEN.search(sql_stripped);raise ValueError(f"Forbidden SQL operation: {forbidden_match.group()}")
	if dialect=='redshift':
		sql_lower=sql_stripped.lower()
		for kw in REDSHIFT_UNSUPPORTED:
			if kw in sql_lower:raise ValueError(f"Redshift does not support: {kw}")
	found_tables=extract_tables(sql_stripped);allowed_tables_lower=set(t.lower()for t in allowed_tables);cte_aliases={m.lower()for m in re.findall('\\b(\\w+)\\s+AS\\s*\\(',sql_stripped,re.IGNORECASE)};found_tables-=cte_aliases;unauthorized_tables=found_tables-allowed_tables_lower
	if unauthorized_tables:raise ValueError(f"Unauthorized table(s): {', '.join(sorted(unauthorized_tables))}. Allowed tables: {', '.join(allowed_tables)}")
	return sql_stripped