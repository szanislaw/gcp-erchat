import re
from typing import List,Dict,Any
def format_column_name(column):
	special_cases={'vip':'VIP','uuid':'UUID','id':'ID','url':'URL','api':'API','ip':'IP'}
	if column.lower()in special_cases:return special_cases[column.lower()]
	suffixes_to_remove=['_name','_text','_no','_uuid','_id'];cleaned=column
	for suffix in suffixes_to_remove:
		if cleaned.lower().endswith(suffix):cleaned=cleaned[:-len(suffix)];break
	parts=cleaned.split('_');expanded_parts=[]
	for part in parts:
		spaced=re.sub('([a-z])([A-Z])','\\1 \\2',part);common_words=['snapshot','date','time','created','updated','completed','cancelled','incident','actual','potential','category','department','severity','status','location','profile','property','account','recovery','compensation','temperament','description','mapping'];remaining=spaced.lower();word_parts=[]
		while remaining:
			found=False
			for word in sorted(common_words,key=len,reverse=True):
				if remaining.startswith(word):word_parts.append(word);remaining=remaining[len(word):];found=True;break
			if not found:
				words=re.findall('[a-z]+|[A-Z][a-z]*',remaining)
				if words:word_parts.extend(words)
				break
		if word_parts:expanded_parts.extend(word_parts)
		else:expanded_parts.append(part)
	formatted=' '.join(word.capitalize()for word in expanded_parts if word)
	for(key,value)in special_cases.items():formatted=re.sub(rf"\b{key.capitalize()}\b",value,formatted,flags=re.IGNORECASE)
	return formatted
def format_columns(columns):return[format_column_name(col)for col in columns]
def format_execution_data(data):
	C='row_count';B='rows';A='columns'
	if not data or A not in data or B not in data:return data
	original_columns=data[A];formatted_columns=format_columns(original_columns);column_mapping=dict(zip(original_columns,formatted_columns));formatted_rows=[]
	for row in data[B]:formatted_row={column_mapping.get(key,key):value for(key,value)in row.items()};formatted_rows.append(formatted_row)
	return{A:formatted_columns,B:formatted_rows,C:data.get(C,len(formatted_rows))}