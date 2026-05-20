_D='line'
_C='table'
_B='bar'
_A='metric'
import re
from typing import Dict,Any,List,Optional
def get_display_type_from_question(question):
	q=question.lower().strip()
	if q in QUERY_DISPLAY_TYPE_MAP:return QUERY_DISPLAY_TYPE_MAP[q]
	line_patterns=['\\btrend\\b','per (day|week|month|year)','each (day|week|month|year)','over (time|the)\\b','(daily|weekly|monthly|yearly) (trend|count|breakdown)']
	for pattern in line_patterns:
		if re.search(pattern,q):return _D
	metric_patterns=['^how many\\b','^what is the total\\b','^what is the average\\b','^what percentage\\b','^which .{0,40} has the most\\b','^what is the most common\\b','\\bwere (completed|created|cancelled)\\b.*(this|last).*(month|week|year)','\\bin the last \\d+ (days?|weeks?|months?)\\?$','\\bin the last (week|month|year)\\?$']
	for pattern in metric_patterns:
		if re.search(pattern,q):
			if not re.search('\\bby (category|department|severity|status|property|location|priority|type)\\b',q):
				if not re.search('\\bgrouped by\\b',q):return _A
	bar_patterns=['count.*by (department|category|severity|property|status|priority|location|type)','\\bby (department|status|priority|location|severity|category|property)\\b','grouped by (department|status|priority|location|severity|category)','per (department|location)\\b','which (department|category|severity)','top \\d+.*(department|location|status|priority|category|severity)','(average|avg).*by (category|severity|department|status|location)']
	for pattern in bar_patterns:
		if re.search(pattern,q):return _B
	pie_patterns=['breakdown by (status|category|type)','distribution (of|by)']
	for pattern in pie_patterns:
		if re.search(pattern,q):return'pie'
	table_patterns=['^show me (all|the)\\b','^show (recent|open|completed|cancelled|high|low|urgent)\\b.*(order|maintenance|incident)','^show.*(order|maintenance).*(last \\d+|last week|last month|recent|from the)','^show (the )?(most recent|\\d+) (recent )?(incident|order|maintenance)','^show recent\\b','most recent \\d+','\\bordered by\\b','\\blast \\d+ days\\b']
	for pattern in table_patterns:
		if re.search(pattern,q):return _C
QUERY_DISPLAY_TYPE_MAP={'how many total maintenance orders are there?':_A,'how many maintenance orders are currently open?':_A,'how many maintenance orders have been completed?':_A,'how many maintenance orders are cancelled?':_A,'how many high priority maintenance orders are there?':_A,'how many low priority maintenance orders exist?':_A,'how many urgent maintenance orders are there?':_A,'how many maintenance orders were created this month?':_A,'how many maintenance orders were created this week?':_A,'how many maintenance orders were created last week?':_A,'how many maintenance orders were completed this year?':_A,'how many maintenance orders were cancelled last month?':_A,'how many maintenance orders were created vs completed this month?':_A,'what percentage of maintenance orders are completed?':_A,'what is the most common maintenance order type?':_A,'which status has the most maintenance orders?':_A,'which location has the most maintenance orders?':_A,'show maintenance order count by status':_B,'show maintenance order count by priority':_B,'show maintenance order count by location':_B,'show maintenance order count grouped by department':_B,'which departments have open maintenance orders?':_B,'show high priority maintenance orders per department':_B,'show the top 5 departments with most maintenance orders':_B,'show maintenance orders created this month by department':_B,'show cancelled orders from last month grouped by priority':_B,'show the monthly trend of maintenance orders created':_D,'show weekly maintenance order trend for this year':_D,'how many maintenance orders were created each day this month?':_D,'show trend of high priority orders by month':_D,'how many total incidents are there?':_A,'how many open incidents are there?':_A,'how many completed incidents?':_A,'how many cancelled incidents?':_A,'how many draft incidents are there?':_A,'how many high severity incidents?':_A,'how many critical severity incidents are there?':_A,'how many pending incidents?':_A,'how many incidents were created this month?':_A,'how many incidents were created this year?':_A,'how many incidents were created this week?':_A,'how many incidents were created last month?':_A,'how many incidents were created last week?':_A,'how many incidents were created in the last 30 days?':_A,'how many incidents were completed this month?':_A,'how many incidents were created in the last 7 days?':_A,'how many high severity open incidents are there?':_A,'how many critical incidents are pending?':_A,'how many completed high severity incidents are there?':_A,'how many vip guest incidents are there?':_A,'how many high severity incidents were created this month?':_A,'how many open critical incidents are there?':_A,'what percentage of incidents are completed?':_A,'what percentage of incidents are open?':_A,'what percentage of incidents are high or critical severity?':_A,'what percentage of incidents created this month are completed?':_A,'what is the average actual cost per incident?':_A,'what is the total actual cost of all incidents?':_A,'show incident count by status':_B,'show incident count by severity':_B,'show incident count by category':_B,'show incident count by department':_B,'which category has the most incidents?':_B,'which department has the most incidents?':_B,'show incident count by location':_B,'show top 5 incident categories':_B,'show average cost by category':_B,'show average cost by severity':_B,'show top 5 categories by average cost':_B,'show the monthly incident trend':_D,'show the weekly incident trend for this year':_D,'show the daily incident trend this month':_D,'show monthly trend of completed incidents':_D,'show monthly incident count by severity':_D,'show weekly trend of open incidents':_D,'show the 10 most recent incidents':_C,'show the 5 most recent completed incidents':_C,'show recent high severity incidents':_C,'show recent incidents with their categories and status':_C,'show the most recent vip guest incidents':_C,'what is the distribution of maintenance orders by status and priority?':_C,'show high priority open maintenance orders':_C,'show maintenance orders created in the last 30 days':_C,'show orders created in the last 7 days':_C,'show the 10 most recent maintenance orders':_C,'what are the most recent 5 completed maintenance orders?':_C}
def get_display_type(sql,execution_data,query_text=None):
	A='rows'
	if query_text:
		normalized_query=query_text.lower().strip()
		if normalized_query in QUERY_DISPLAY_TYPE_MAP:return QUERY_DISPLAY_TYPE_MAP[normalized_query]
	if not execution_data or not execution_data.get(A):return _C
	sql_lower=sql.lower();columns=execution_data.get('columns',[]);rows=execution_data.get(A,[]);row_count=len(rows);col_count=len(columns)
	if row_count==1 and col_count==1:return _A
	if row_count==1 and col_count<=3 and _has_aggregation(sql_lower):return _A
	if _is_time_series(sql_lower,columns)and _has_aggregation(sql_lower)and _has_group_by(sql_lower):return _D
	if col_count==2 and row_count>=2 and row_count<=100 and _has_aggregation(sql_lower)and _has_group_by(sql_lower):
		first_col=columns[0].lower()
		if any(term in first_col for term in['date','day','week','month','year','time']):return _D
	if col_count==2 and row_count<=10 and _has_aggregation(sql_lower)and _has_group_by(sql_lower):return'pie'
	if _has_group_by(sql_lower)and _has_aggregation(sql_lower):
		if row_count<=50:return _B
		else:return _C
	return _C
def _is_time_series(sql,columns):
	time_group_patterns=['group\\s+by\\s+[^,]*\\b(date|year|month|week|day)\\b','group\\s+by\\s+[^,]*date_trunc','group\\s+by\\s+[^,]*extract\\s*\\(','group\\s+by\\s+[^,]*snapshotdate','group\\s+by\\s+[^,]*created_date','group\\s+by\\s+[^,]*date\\s*\\(','group\\s+by\\s+[^,]*cast\\s*\\([^)]*as\\s+date','group\\s+by\\s+[^,]*to_char\\s*\\(','group\\s+by\\s+[^,]*date_format','group\\s+by\\s+[^,]*from_unixtime']
	for pattern in time_group_patterns:
		if re.search(pattern,sql,re.IGNORECASE):return True
	time_column_names=['date','day','week','month','year','time','timestamp']
	for col in columns:
		col_lower=col.lower()
		if any(time_term in col_lower for time_term in time_column_names):
			if re.search('group\\s+by',sql,re.IGNORECASE):return True
	return False
def _has_group_by(sql):return bool(re.search('\\bgroup\\s+by\\b',sql))
def _has_aggregation(sql):agg_functions=['\\bcount\\s*\\(','\\bsum\\s*\\(','\\bavg\\s*\\(','\\bmin\\s*\\(','\\bmax\\s*\\(','\\bstddev\\s*\\(','\\bvariance\\s*\\('];return any(re.search(pattern,sql)for pattern in agg_functions)