_A=None
from pydantic import BaseModel,Field
from typing import List,Optional,Literal
class Context(BaseModel):account_uuid:Optional[str]=_A;property_uuid:Optional[str]=_A;user_uuid:Optional[str]=_A;user_role:Optional[str]=_A;location_name:Optional[str]=_A;language:Literal['en','zh','ms','ta']='en'
class SQLConfig(BaseModel):dialect:Literal['redshift'];tables:List[str]=[]
class ExecutionConfig(BaseModel):dry_run:bool=True;max_rows:int=100;timeout_ms:int=5000;redshift_target:Optional[str]=_A
class ModelConfig(BaseModel):name:str='Ellbendls/Qwen-2.5-3b-Text_to_SQL';temperature:float=.0;max_tokens:int=256
class DisplayConfig(BaseModel):type:Literal['table','metric','bar','line','pie','card','list']='table';title:Optional[str]=_A;subtitle:Optional[str]=_A;chart_config:Optional[dict]=_A
class Trace(BaseModel):request_id:Optional[str]=_A;source:str='fcs1-ui'
class NLQRequest(BaseModel):text:str=Field(...,min_length=3);context:Context;sql:SQLConfig;execution:ExecutionConfig;model:ModelConfig;display:Optional[DisplayConfig]=_A;trace:Trace