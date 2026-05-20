_K='tables'
_J='schema'
_I='master_job_priority'
_H='status_name'
_G='master_maintenance_status'
_F='incident'
_E='default'
_D='mv_recovery_all'
_C='limit'
_B='columns'
_A='table'
import os,redshift_connector
ENUM_COLUMNS={_E:[{_A:_G,_B:[_H],_C:50},{_A:_I,_B:['priority_name'],_C:50}],_F:[{_A:_D,_B:[_H],_C:50},{_A:_D,_B:['severity_name'],_C:50},{_A:_D,_B:['category_name'],_C:50},{_A:_D,_B:['incident_name'],_C:100},{_A:_D,_B:['temperament_text'],_C:50},{_A:_D,_B:['property_name'],_C:50}]}
REDSHIFT_TARGETS={_E:{_J:os.getenv('REDSHIFT_SCHEMA','nxg_107747471_q2sj'),_K:['maintenance_order',_G,_I,'property_location']},_F:{_J:os.getenv('REDSHIFT_INCIDENT_SCHEMA','public'),_K:[_D]}}
def get_connection():return redshift_connector.connect(host=os.getenv('REDSHIFT_HOST',''),port=int(os.getenv('REDSHIFT_PORT','5439')),database=os.getenv('REDSHIFT_DBNAME','dev'),user=os.getenv('REDSHIFT_USER',''),password=os.getenv('REDSHIFT_PASSWORD',''))