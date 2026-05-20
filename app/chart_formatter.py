from typing import Dict,Any,List,Optional
def format_for_chart(execution_data,display_type):
	A='rows'
	if not execution_data or not execution_data.get(A):return
	rows=execution_data[A];columns=execution_data.get('columns',[])
	if display_type=='metric':
		if len(rows)==1 and len(columns)>=1:first_col=columns[0];value=rows[0].get(first_col);return{'value':value,'label':first_col}
		return
	if display_type in['bar','pie','line']:
		if len(columns)<2 or len(rows)==0:return
		label_col=columns[0];value_col=columns[1];labels=[];values=[]
		for row in rows:
			label=row.get(label_col);value=row.get(value_col)
			if label is None:continue
			labels.append(str(label))
			try:values.append(float(value)if value is not None else 0)
			except(ValueError,TypeError):values.append(0)
		return{'labels':labels,'values':values,'label_column':label_col,'value_column':value_col}