_N='severity'
_M='status'
_L='target'
_K='date'
_J='text_columns'
_I='partitions'
_H='schema'
_G='columns'
_F='tables'
_E='date_columns'
_D='numeric_columns'
_C='name'
_B='categorical_columns'
_A='category'
from typing import List,Dict,Any
from app.schema_loader import load_schema
from app.redshift_config import REDSHIFT_TARGETS
def analyze_schema(target_name):
	A='type';schema=load_schema(target_name);cfg=REDSHIFT_TARGETS[target_name];analysis={_L:target_name,_H:cfg[_H],_F:[]}
	for(table_name,table_info)in schema.items():
		table_analysis={_C:table_name,_G:[],_D:[],_E:[],_J:[],_B:[],_I:table_info.get(_I,[])}
		for col in table_info[_G]:
			col_name=col[_C];col_type=col[A].lower();table_analysis[_G].append({_C:col_name,A:col_type})
			if any(t in col_type for t in['int','bigint','decimal','double','float']):table_analysis[_D].append(col_name)
			if any(t in col_type for t in[_K,'timestamp'])or _K in col_name or'time'in col_name:table_analysis[_E].append(col_name)
			if'string'in col_type or'varchar'in col_type:
				if any(keyword in col_name for keyword in[_C,_M,_A,A,_N,'department']):table_analysis[_B].append(col_name)
				else:table_analysis[_J].append(col_name)
		analysis[_F].append(table_analysis)
	return analysis
def generate_query_suggestions(target_name):
	H='Basic';G='Time-based';F='Analytics';E='Filtering';D=' ';C='_';B='description';A='query';analysis=analyze_schema(target_name);suggestions=[]
	for table in analysis[_F]:
		table_name=table[_C];suggestions.append({_A:H,A:f"Show all {table_name}",B:f"Retrieve all records from {table_name} table"});suggestions.append({_A:H,A:f"Show me 10 {table_name}",B:f"Get a sample of records from {table_name}"})
		if table[_E]:date_col=table[_E][0];suggestions.append({_A:G,A:f"Show recent {table_name}",B:f"Get the most recent records based on {date_col}"});suggestions.append({_A:G,A:f"Show {table_name} from last 7 days",B:f"Filter records from the past week"});suggestions.append({_A:G,A:f"Show {table_name} from today",B:f"Get today's records"})
		for cat_col in table[_B]:
			col_display=cat_col.replace(C,D);suggestions.append({_A:E,A:f"Show {table_name} by {col_display}",B:f"Group or filter by {col_display}"})
			if _M in cat_col.lower():suggestions.append({_A:E,A:f"Show pending {table_name}",B:f"Filter by pending status"});suggestions.append({_A:E,A:f"Show completed {table_name}",B:f"Filter by completed status"})
			if _N in cat_col.lower():suggestions.append({_A:E,A:f"Show high severity {table_name}",B:f"Filter by high severity"})
		if table[_D]:
			for num_col in table[_D][:2]:col_display=num_col.replace(C,D);suggestions.append({_A:F,A:f"What is the total {col_display}",B:f"Calculate sum of {col_display}"});suggestions.append({_A:F,A:f"What is the average {col_display}",B:f"Calculate average {col_display}"})
		suggestions.append({_A:F,A:f"How many {table_name} are there",B:f"Count total records in {table_name}"})
		if table[_B]:cat_col=table[_B][0];col_display=cat_col.replace(C,D);suggestions.append({_A:F,A:f"Count {table_name} by {col_display}",B:f"Group count by {col_display}"})
		if table[_E]and table[_B]:cat_col=table[_B][0];col_display=cat_col.replace(C,D);suggestions.append({_A:'Combined',A:f"Show recent {table_name} by {col_display}",B:f"Recent records grouped by {col_display}"})
		if table[_D]and table[_B]:num_col=table[_D][0];cat_col=table[_B][0];num_display=num_col.replace(C,D);cat_display=cat_col.replace(C,D);suggestions.append({_A:'Top/Bottom',A:f"Top 10 {table_name} by {num_display}",B:f"Highest values of {num_display}"})
	return suggestions
def get_schema_summary(target_name):
	analysis=analyze_schema(target_name);cfg=REDSHIFT_TARGETS[target_name];summary={_L:target_name,_H:cfg[_H],_F:[]}
	for table in analysis[_F]:table_summary={_C:table[_C],'total_columns':len(table[_G]),'column_types':{'numeric':len(table[_D]),_K:len(table[_E]),'categorical':len(table[_B]),'text':len(table[_J])},'key_columns':{'dates':table[_E],'categories':table[_B],'metrics':table[_D][:5]},_I:table[_I],'all_columns':[col[_C]for col in table[_G]]};summary[_F].append(table_summary)
	return summary