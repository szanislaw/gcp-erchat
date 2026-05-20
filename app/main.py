_T='redshift_target'
_S='chart_data'
_R='display'
_Q='execution'
_P='metric'
_O='version'
_N='NLQ → Redshift SQL API'
_M='sql'
_L='bar'
_K='0.4-refactored'
_J='default'
_I='static'
_H='success'
_G='pie'
_F='error'
_E=True
_D='line'
_C=False
_B=None
_A='query'
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI,HTTPException,Request,Depends
from fastapi.responses import JSONResponse,FileResponse,HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.models import NLQRequest
from app.prompt import build_prompt,build_correction_prompt,find_property_uuid_column
from app.sqlcoder import run_sqlcoder,load_model,fix_table_names,fix_property_column,inject_property_filter,fix_impossible_this_period_filter,fix_last_week_filter,fix_invalid_extract_from_table,fix_department_column,fix_spurious_department_join,fix_main_table_fk_names,fix_snapshotdate,fix_scalar_subquery_eq,fix_status_case,fix_unaliased_table_ref,fix_year_extract_comparison,fix_dateadd_quoted_unit,fix_date_part_this_period,fix_extract_week_trend
from app.schema_loader import load_schema
from app.security import validate_sql
from app.redshift_client import execute_query
from app.redshift_config import REDSHIFT_TARGETS
from app.utils import gen_request_id
from app.request_logger import log_request,get_logs,get_log_count
from app.display_hint import get_display_type,get_display_type_from_question
from app.chart_formatter import format_for_chart
from app.query_suggestions import generate_query_suggestions,get_schema_summary
from app.input_validator import validate_nlq_input,ValidationResult
from app.rate_limiter import get_rate_limiter,RateLimiter,RateLimitConfig
from app.column_formatter import format_execution_data
import json,os,time,asyncio
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote as url_quote
import logging
logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger=logging.getLogger(__name__)
_executor=ThreadPoolExecutor(max_workers=4)
@asynccontextmanager
async def lifespan(app):logger.info('[STARTUP] Preloading ML model...');load_model();logger.info('[STARTUP] Model preloaded successfully! Ready to handle queries.');rate_limiter=get_rate_limiter();logger.info(f"[STARTUP] Rate limiter initialized: {rate_limiter.config.requests_per_second} req/s, burst {rate_limiter.config.burst_size}");yield;logger.info('[SHUTDOWN] Cleaning up...');_executor.shutdown(wait=_E);logger.info('[SHUTDOWN] Cleanup complete.')
app=FastAPI(title=_N,version=_K,lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_credentials=_E,allow_methods=['*'],allow_headers=['*'])
static_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)),_I)
if os.path.exists(static_dir):app.mount('/static',StaticFiles(directory=static_dir),name=_I)
class PrettyJSONResponse(JSONResponse):
	def render(self,content):return json.dumps(content,ensure_ascii=_C,allow_nan=_C,indent=2,separators=(', ',': ')).encode('utf-8')
def get_limiter():return get_rate_limiter()
@app.get('/')
def read_root():
	static_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)),_I);index_file=os.path.join(static_dir,'index.html')
	if os.path.exists(index_file):return FileResponse(index_file)
	return{'message':_N,_O:_K,'gui':'not available'}
@app.get('/dashboard')
def read_dashboard():
	static_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)),_I);dash_file=os.path.join(static_dir,'dashboard.html')
	if os.path.exists(dash_file):return FileResponse(dash_file)
	return{_F:'dashboard not found'}
@app.get('/health')
def health_check():rate_limiter=get_rate_limiter();return{'status':'healthy',_O:_K,'rate_limiter':rate_limiter.get_stats()}
def _run_model_inference(prompt,max_tokens):return run_sqlcoder(prompt=prompt,max_tokens=max_tokens)
@app.post('/nlq/execute',response_class=PrettyJSONResponse)
async def execute(req,rate_limiter=Depends(get_limiter),request=_B):
	I='row_count';H='confidence';G='explanation';F='latency_ms';E='total_ms';D='query_ms';C='postprocess_ms';B='model_ms';A='prompt_ms';request_id=req.trace.request_id or gen_request_id();start_time=time.time()
	try:
		validation_result=validate_nlq_input(req.text,strict_mode=_E)
		if not validation_result.is_valid:raise HTTPException(status_code=400,detail=f"Invalid input: {validation_result.error}")
		sanitized_text=validation_result.sanitized_text;t_validated=time.time();rate_check=rate_limiter.check_rate_limit()
		if not rate_check.allowed:raise HTTPException(status_code=429,detail=f"Rate limit exceeded. Retry after {rate_check.retry_after:.1f} seconds",headers={'Retry-After':str(int(rate_check.retry_after)+1)})
		redshift_target=req.execution.redshift_target or _J
		if req.sql.tables:allowed_tables=req.sql.tables
		else:target_cfg=REDSHIFT_TARGETS.get(redshift_target,{});allowed_tables=target_cfg.get('tables',['maintenance_order'])
		prompt=build_prompt(text=sanitized_text,context=req.context,sql=req.sql,redshift_target=redshift_target,property_uuid=req.context.property_uuid,user_uuid=req.context.user_uuid);t_prompt=time.time();loop=asyncio.get_event_loop();result=await loop.run_in_executor(_executor,_run_model_inference,prompt,req.model.max_tokens);t_model=time.time();result[_A]=fix_snapshotdate(result[_A]);result[_A]=fix_table_names(result[_A],allowed_tables);result[_A]=fix_unaliased_table_ref(result[_A]);result[_A]=fix_dateadd_quoted_unit(result[_A]);result[_A]=fix_date_part_this_period(result[_A]);result[_A]=fix_extract_week_trend(result[_A])
		if redshift_target!='incident':result[_A]=fix_spurious_department_join(result[_A]);result[_A]=fix_main_table_fk_names(result[_A])
		result[_A]=fix_scalar_subquery_eq(result[_A]);result[_A]=fix_status_case(result[_A]);result[_A]=fix_department_column(result[_A]);result[_A]=fix_invalid_extract_from_table(result[_A]);result[_A]=fix_year_extract_comparison(result[_A]);result[_A]=fix_impossible_this_period_filter(result[_A]);result[_A]=fix_last_week_filter(result[_A],sanitized_text);_schema=load_schema(redshift_target);_property_col=find_property_uuid_column(_schema);_property_uuids=[u.strip()for u in req.context.property_uuid.split(',')if u.strip()]if req.context.property_uuid else[];result[_A]=fix_property_column(result[_A],_property_col,_property_uuids);result[_A]=inject_property_filter(result[_A],_property_col,_property_uuids);sql=validate_sql(result[_A],allowed_tables,req.sql.dialect);t_postprocess=time.time();execution_data=_B;executed=_C;correction_attempts=0;MAX_CORRECTIONS=2
		if not req.execution.dry_run:
			current_sql=sql
			for attempt in range(MAX_CORRECTIONS+1):
				try:raw_data=await loop.run_in_executor(_executor,lambda s=current_sql:execute_query(sql=s,target_name=redshift_target,max_rows=req.execution.max_rows));execution_data=format_execution_data(raw_data);executed=_E;sql=current_sql;break
				except RuntimeError as exec_error:
					if attempt>=MAX_CORRECTIONS:raise
					error_msg=str(exec_error);logger.warning(f"Redshift execution failed (attempt {attempt+1}/{MAX_CORRECTIONS}), running self-correction. Error: {error_msg[:200]}");correction_prompt=build_correction_prompt(text=sanitized_text,context=req.context,sql=req.sql,redshift_target=redshift_target,failed_sql=current_sql,error_message=error_msg,property_uuid=req.context.property_uuid,user_uuid=req.context.user_uuid);correction_result=await loop.run_in_executor(_executor,_run_model_inference,correction_prompt,req.model.max_tokens);corrected_sql=fix_table_names(correction_result[_A],allowed_tables);corrected_sql=fix_property_column(corrected_sql,_property_col,_property_uuids);corrected_sql=inject_property_filter(corrected_sql,_property_col,_property_uuids);corrected_sql=validate_sql(corrected_sql,allowed_tables,req.sql.dialect);correction_attempts+=1;logger.info(f"Self-correction {correction_attempts}: new SQL: {corrected_sql[:120]}");current_sql=corrected_sql
		t_query=time.time()
		if req.display and req.display.type:display_type=req.display.type;logger.info(f"Using user-specified display type: {display_type}")
		else:
			display_type=get_display_type_from_question(req.text)
			if display_type:logger.info(f"Detected display type from question pattern: {display_type}")
			elif executed and execution_data:display_type=get_display_type(sql,execution_data);logger.info(f"Auto-detected display type from SQL: {display_type}")
			else:display_type='table';logger.info(f"Using default display type: {display_type}")
		chart_data=_B
		if executed and execution_data and display_type in[_L,_G,_D,_P]:chart_data=format_for_chart(execution_data,display_type);logger.info(f"Chart data formatted for {display_type}: {chart_data is not _B}")
		total_latency_ms=int((time.time()-start_time)*1000);latency_breakdown={A:int((t_prompt-t_validated)*1000),B:result[F],C:int((t_postprocess-t_model)*1000),D:int((t_query-t_postprocess)*1000),E:total_latency_ms};logger.info(f"[LATENCY] {request_id} prompt={latency_breakdown[A]}ms model={latency_breakdown[B]}ms post={latency_breakdown[C]}ms query={latency_breakdown[D]}ms total={latency_breakdown[E]}ms");response={_H:_E,_M:{_A:sql,H:result[H]},_Q:{'executed':executed,I:execution_data[I]if execution_data else _B,'data':execution_data},_R:{'type':display_type,_S:chart_data,'embed_link':str(request.base_url).rstrip('/')+'/chart?q='+url_quote(req.text)if request is not _B else _B},G:result[G],'trace':{'request_id':request_id,F:latency_breakdown,_T:redshift_target,'allowed_tables':allowed_tables,'input_warnings':validation_result.warnings,'correction_attempts':correction_attempts}};log_request(request_id=request_id,request_data=req.dict(),response_data=response,status_code=200);return response
	except HTTPException:raise
	except ValueError as e:error_response={_H:_C,_F:str(e)};log_request(request_id=request_id,request_data=req.dict(),response_data=error_response,status_code=400,error=str(e));raise HTTPException(status_code=400,detail=str(e))
	except RuntimeError as e:error_response={_H:_C,_F:str(e)};log_request(request_id=request_id,request_data=req.dict(),response_data=error_response,status_code=400,error=str(e));raise HTTPException(status_code=400,detail=str(e))
	except Exception as e:logger.exception(f"Unexpected error processing request {request_id}");error_response={_H:_C,_F:'Internal server error'};log_request(request_id=request_id,request_data=req.dict(),response_data=error_response,status_code=500,error=str(e));raise HTTPException(status_code=500,detail='Internal server error. Please try again.')
@app.get('/logs',response_class=PrettyJSONResponse)
def view_logs(limit=100):return{'total_logs':get_log_count(),'logs':get_logs(limit=min(limit,100))}
@app.get('/nlq/suggestions',response_class=PrettyJSONResponse)
def get_suggestions(target=_J):
	try:suggestions=generate_query_suggestions(target);return{'target':target,'total_suggestions':len(suggestions),'suggestions':suggestions}
	except Exception as e:logger.exception(f"Error getting suggestions for target {target}");raise HTTPException(status_code=400,detail=str(e))
@app.get('/nlq/schema',response_class=PrettyJSONResponse)
def get_schema(target=_J):
	try:summary=get_schema_summary(target);return summary
	except Exception as e:logger.exception(f"Error getting schema for target {target}");raise HTTPException(status_code=400,detail=str(e))
@app.get('/rate-limit/stats',response_class=PrettyJSONResponse)
def get_rate_limit_stats(rate_limiter=Depends(get_limiter)):return rate_limiter.get_stats()
@app.get('/chart',response_class=HTMLResponse)
async def chart_embed(q,target=_J,property_uuid=''):
	A='labels';import html as _html;req=NLQRequest(**{'text':q,'context':{'property_uuid':property_uuid or _B},_M:{'dialect':'redshift'},_Q:{'dry_run':_C,'max_rows':100,_T:target},'model':{'max_tokens':256},'trace':{'source':'chart-embed'}});data=await execute(req,get_limiter())
	if not data.get(_H):err=_html.escape(data.get(_F)or data.get('detail')or'Query failed');return HTMLResponse(f'<!DOCTYPE html><html><head><meta charset="UTF-8">\n<style>body{{background:#0f1117;color:#fca5a5;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}}p{{padding:24px;border:1px solid #7f1d1d;border-radius:8px;background:#1c0f0f}}</style>\n</head><body><p>{err}</p></body></html>',status_code=200)
	disp=data.get(_R,{});display_type=disp.get('type','table');chart_data=disp.get(_S);sql_query=_html.escape(data.get(_M,{}).get(_A,''));q_escaped=_html.escape(q);palette=['#6366f1','#8b5cf6','#06b6d4','#10b981','#f59e0b','#ef4444','#ec4899','#84cc16']
	if display_type==_P and chart_data:chart_html=f'\n        <div style="text-align:center;padding:40px 24px">\n          <div style="font-size:60px;font-weight:700;background:linear-gradient(135deg,#6366f1,#8b5cf6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1">{_html.escape(str(chart_data.get("value","—")))}</div>\n          <div style="color:#64748b;font-size:14px;margin-top:12px;text-transform:capitalize">{_html.escape(str(chart_data.get("label","")or""))}</div>\n        </div>';chart_script=''
	elif display_type in(_L,_G,_D)and chart_data and chart_data.get(A):labels_json=json.dumps(chart_data[A]);values_json=json.dumps(chart_data['values']);pal_json=json.dumps(palette[:len(chart_data[A])]);val_col=_html.escape(chart_data.get('value_column')or'Value');bg='palette'if display_type==_G else"'rgba(99,102,241,0.75)'";border_color="'#6366f1'"if display_type==_D else"'transparent'";border_width='2'if display_type==_D else'0';scales_cfg=''if display_type==_G else",\n          scales:{x:{ticks:{color:'#94a3b8',font:{size:11}},grid:{color:'#1e2333'}},\n                  y:{ticks:{color:'#94a3b8',font:{size:11}},grid:{color:'#1e2333'},beginAtZero:true}}";chart_html='<canvas id="c"></canvas>';chart_script=f"""
<script src=\"https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js\"></script>
<script>
var palette={pal_json};
new Chart(document.getElementById('c').getContext('2d'),{{
  type:'{display_type}',
  data:{{labels:{labels_json},datasets:[{{
    label:'{val_col}',data:{values_json},
    backgroundColor:{bg},borderColor:{border_color},borderWidth:{border_width},
    fill:{json.dumps(display_type==_D)},tension:0.35,
    pointBackgroundColor:'#6366f1',pointRadius:{4 if display_type==_D else 0},
    borderRadius:{4 if display_type==_L else 0}
  }}]}},
  options:{{responsive:true,maintainAspectRatio:true,
    interaction:{{mode:'index',intersect:false}},
    plugins:{{legend:{{display:{json.dumps(display_type==_G)},labels:{{color:'#94a3b8',font:{{size:12}}}}}},
      tooltip:{{backgroundColor:'#1a1d2e',titleColor:'#f1f5f9',bodyColor:'#94a3b8',borderColor:'#374151',borderWidth:1}}
    }}{scales_cfg}
  }}
}});
</script>"""
	else:chart_html=f"<div style='color:#64748b;text-align:center;padding:32px'>Display type: {_html.escape(display_type)}</div>";chart_script=''
	return HTMLResponse(f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{q_escaped}</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:#0f1117;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}}
    .wrap{{width:100%;max-width:820px}}
    .title{{font-size:15px;font-weight:600;color:#94a3b8;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.05em}}
    .box{{background:#1a1d2e;border:1px solid #2d3748;border-radius:12px;padding:24px}}
    details{{margin-top:16px}}
    summary{{font-size:11px;color:#4b5563;cursor:pointer;user-select:none}}
    pre{{background:#0f1117;border:1px solid #2d3748;border-radius:6px;padding:12px;font-size:12px;color:#a5f3fc;white-space:pre-wrap;word-break:break-all;margin-top:8px;font-family:\'Courier New\',monospace}}
    .footer{{margin-top:10px;font-size:11px;color:#374151;text-align:right}}
    .footer a{{color:#6366f1;text-decoration:none}}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="title">{q_escaped}</div>
    <div class="box">{chart_html}</div>
    <details>
      <summary>SQL</summary>
      <pre>{sql_query}</pre>
    </details>
    <div class="footer"><a href="/">Maintenance Order Analytics ↗</a></div>
  </div>
  {chart_script}
</body>
</html>''')