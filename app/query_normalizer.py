_AL='category_name'
_AK='department_name'
_AJ='status_name'
_AI='severity_name'
_AH='incident_name'
_AG='property_name'
_AF='last month'
_AE='this month'
_AD='last week'
_AC='this week'
_AB='Alleged Food-borne Illness'
_AA='Foreign Object in Food / Beverage'
_A9='Delay of Service'
_A8='Product Quality'
_A7='lost property'
_A6='staff attitude'
_A5='Reservation'
_A4='The Lobby'
_A3='Banquet & Event'
_A2='Engineering'
_A1='reservation'
_A0='reservations'
_z='transportation'
_y='transport'
_x='safety'
_w='security'
_v='checkout'
_u='check-in'
_t='check in'
_s='front office'
_r='dining'
_q='restaurant'
_p='food and beverage'
_o='housekeeping'
_n='waiting'
_m='Positive Comments'
_l='Abnormal Smell / Odour'
_k='Billing Issue / Dispute Charge'
_j='Staff Attitude'
_i='Noise - Guest Room'
_h='Data Privacy'
_g='Guest Room'
_f='Safety & Security'
_e='The Peninsula Istanbul'
_d='last 7 days'
_c='Guest Injury / Sickness'
_b='Power Failure / Black Out'
_a='Lost / Damaged Guest Property'
_Z='Systems'
_Y='Reservations'
_X='In Room Dining'
_W=True
_V='Hotel Facilities'
_U='Disturbance'
_T='Spa & Wellness'
_S='The Peninsula London'
_R='The Peninsula Manila'
_Q='Plumbing / Drainage Issue'
_P='Billing'
_O='Service Quality'
_N='Room Condition'
_M='The Peninsula Bangkok'
_L=None
_K='AC Issue'
_J='Health & Safety'
_I='Transportation'
_H='Security'
_G='Housekeeping'
_F='cancelled'
_E='The Peninsula Hong Kong'
_D='completed'
_C='Front Office'
_B='pending'
_A='Food & Beverage'
from typing import Dict,List,Tuple,Optional,Set
from functools import lru_cache
import re,logging
logger=logging.getLogger(__name__)
PROPERTY_ALIASES={'peninsula bangkok':_M,'pen bangkok':_M,'bkk peninsula':_M,'peninsula bkk':_M,'bangkok':_M,'bkk':_M,'peninsula manila':_R,'pen manila':_R,'manila peninsula':_R,'manila':_R,'mnl':_R,'peninsula hong kong':_E,'peninsula hk':_E,'pen hk':_E,'hk peninsula':_E,'hong kong':_E,'hk':_E,'hongkong':_E,'peninsula london':_S,'pen london':_S,'london peninsula':_S,'london':_S,'ldn':_S,'peninsula istanbul':_e,'pen istanbul':_e,'istanbul peninsula':_e,'the peninsula':'The Peninsula'}
SEVERITY_ALIASES={}
STATUS_ALIASES={_B:_B,'open':_B,'active':_B,'in progress':_B,'ongoing':_B,'unresolved':_B,'outstanding':_B,_n:_B,'new':_B,'not completed':_B,'incomplete':_B,_D:_D,'done':_D,'finished':_D,'resolved':_D,'closed':_D,'fixed':_D,'complete':_D,_F:_F,'canceled':_F,'dropped':_F,'abandoned':_F,'voided':_F,'withdrawn':_F}
DEPARTMENT_ALIASES={'hk':_G,_o:_G,'house keeping':_G,'cleaning':_G,'cleaners':_G,'room cleaning':_G,'fb':_A,'f&b':_A,_p:_A,'food beverage':_A,_q:_A,_r:_A,'kitchen':_A,'fnb':_A,'fo':_C,_s:_C,'front desk':_C,'reception':_C,_t:_C,_u:_C,_v:_C,'check-out':_C,'concierge':'Concierge','eng':_A2,'engineering':_A2,'sec':_H,_w:_H,_x:_f,'safety & security':_f,'safety and security':_f,'spa':_T,'wellness':_T,'spa & wellness':_T,'spa and wellness':_T,'massage':_T,'it':'IT','tech':'IT','technology':'IT','it & elv':'IT & ELV','room service':'Room Service','ird':_X,'in room dining':_X,'in-room dining':_X,'inroom dining':_X,'guest services':'Guest Services','guest service':'Guest Service','guest experience':'Guest Experience','gcc':'Guest Communication Centre','gcc':'GCC','events':'Events','banquet':_A3,'banquets':'Banquets & Events','banquet & event':_A3,_y:_I,_z:_I,'driver':_I,'limo':_I,'car':_I,'lobby':_A4,'the lobby':_A4,'laundry':'Laundry',_A0:_Y,_A1:_A5,'booking':_Y}
CATEGORY_ALIASES={'room condition':_N,'room cleanliness':_N,'dirty room':_N,'unclean room':_N,'cleaning issue':_N,'room issue':_N,'guest room':_g,'guestroom':_g,'room':_g,_o:_G,'service':_O,'service quality':_O,'poor service':_O,'bad service':_O,_A6:_O,'attitude':_O,'food':_A,'beverage':_A,'food & beverage':_A,_p:_A,_q:_A,_r:_A,'billing':_P,'bill':_P,'payment':_P,'charge':_P,'invoice':_P,'dispute':_P,'noise':_U,'disturbance':_U,'loud':_U,'noisy':_U,'noise complaint':_U,_w:_H,'theft':_H,'lost':_H,'stolen':_H,_A7:_H,'health & safety':_J,'health and safety':_J,_x:_J,'injury':_J,'sickness':_J,'illness':_J,'medical':_J,'systems':_Z,'system':_Z,'technical':_Z,'it issue':_Z,'facilities':_V,'hotel facilities':_V,'facility':_V,'pool':'Pool','gym':_V,'fitness':_V,_s:_C,_u:_C,_t:_C,_v:_C,_z:_I,_y:_I,_A1:_A5,_A0:_Y,'booking':_Y,'spa':'Spa','laundry':'Laundry','data privacy':_h,'privacy':_h,'gdpr':_h,'product quality':_A8,'quality':_A8,'clinic':'Clinic','doctor':'Clinic'}
INCIDENT_ALIASES={'plumbing':_Q,'drainage':_Q,'clogged':_Q,'blocked drain':_Q,'toilet':_Q,'leak':_Q,'ac issue':_K,'ac':_K,'air conditioning':_K,'aircon':_K,'temperature':_K,'cold room':_K,'hot room':_K,'noise':_i,'noisy':_i,'loud':_i,_A7:_a,'lost item':_a,'missing item':_a,'damaged property':_a,_A6:_j,'rude staff':_j,'unfriendly':_j,'delay':_A9,_n:'Long Waiting Time','slow service':_A9,'billing issue':_k,'wrong charge':_k,'overcharge':_k,'foreign object':_AA,'hair in food':_AA,'food illness':_AB,'food poisoning':_AB,'power failure':_b,'blackout':_b,'power outage':_b,'no power':_b,'room not ready':'Room Not Ready / Front Office','wait for room':'Wait for Room','smell':_l,'odour':_l,'odor':_l,'sewage smell':'Sewage Smell','injury':_c,'injured':_c,'sick':_c,'medical':_c,'medical emergency':'Code 444 - Medical Emergency','positive':_m,'compliment':_m,'praise':_m,'good feedback':'Positive Feedback'}
TIME_ALIASES={'today':'today','yesterday':'1 day ago',_AC:'this week (calendar boundary)',_AD:'last week (previous Mon–Sun)','past week':_d,_AE:'this month (calendar boundary)',_AF:'last month (previous calendar month)','past month':'last 30 days','this year':'last 365 days','recent':_d,'recently':_d,'latest':_d}
_TIME_SQL_HINTS={_AC:"Use this exact date filter for 'this week': date_parse(snapshotdate, '%Y-%m-%d') >= date_trunc('week', current_date)",_AE:"Use this exact date filter for 'this month': date_parse(snapshotdate, '%Y-%m-%d') >= date_trunc('month', current_date)",_AD:"Use this exact date filter for 'last week': date_parse(snapshotdate, '%Y-%m-%d') >= date_add('week', -1, date_trunc('week', current_date)) AND date_parse(snapshotdate, '%Y-%m-%d') < date_trunc('week', current_date)",_AF:"Use this exact date filter for 'last month': date_parse(snapshotdate, '%Y-%m-%d') >= date_add('month', -1, date_trunc('month', current_date)) AND date_parse(snapshotdate, '%Y-%m-%d') < date_trunc('month', current_date)"}
def get_time_expression_hint(text):
	text_lower=text.lower()
	for expr in sorted(_TIME_SQL_HINTS,key=len,reverse=_W):
		if expr in text_lower:return _TIME_SQL_HINTS[expr]
def _normalize_text(text):
	if not text:return''
	return re.sub('\\s+',' ',text.lower().strip())
def _calculate_similarity(s1,s2):
	if not s1 or not s2:return .0
	s1_norm=_normalize_text(s1);s2_norm=_normalize_text(s2)
	if s1_norm==s2_norm:return 1.
	if s1_norm in s2_norm or s2_norm in s1_norm:return .8
	set1=set(s1_norm.replace(' ',''));set2=set(s2_norm.replace(' ',''))
	if not set1 or not set2:return .0
	intersection=len(set1&set2);union=len(set1|set2);return intersection/union if union>0 else .0
def _find_best_match(query,candidates,threshold=.7):
	query_norm=_normalize_text(query)
	if query_norm in candidates:return candidates[query_norm]
	best_score=.0;best_match=_L
	for(alias,canonical)in candidates.items():
		score=_calculate_similarity(query_norm,alias)
		if score>best_score and score>=threshold:best_score=score;best_match=canonical
	return best_match
def normalize_property_name(text):
	text_lower=text.lower();sorted_aliases=sorted(PROPERTY_ALIASES.keys(),key=len,reverse=_W)
	for alias in sorted_aliases:
		pattern=re.compile(rf"\b{re.escape(alias)}\b",re.IGNORECASE)
		if pattern.search(text_lower):canonical=PROPERTY_ALIASES[alias];normalized_text=pattern.sub(canonical,text,count=1);logger.debug(f"Property alias matched: '{alias}' -> '{canonical}'");return normalized_text,canonical
	return text,_L
def normalize_severity(text):
	text_lower=text.lower()
	for(alias,canonical)in SEVERITY_ALIASES.items():
		pattern=re.compile(rf"\b{re.escape(alias)}\b",re.IGNORECASE)
		if pattern.search(text_lower):normalized_text=pattern.sub(canonical,text);logger.debug(f"Severity alias matched: '{alias}' -> '{canonical}'");return normalized_text,canonical
	return text,_L
def normalize_status(text):
	text_lower=text.lower()
	for(alias,canonical)in STATUS_ALIASES.items():
		pattern=re.compile(rf"\b{re.escape(alias)}\b",re.IGNORECASE)
		if pattern.search(text_lower):normalized_text=pattern.sub(canonical,text);logger.debug(f"Status alias matched: '{alias}' -> '{canonical}'");return normalized_text,canonical
	return text,_L
def normalize_department(text):
	text_lower=text.lower();sorted_aliases=sorted(DEPARTMENT_ALIASES.keys(),key=len,reverse=_W)
	for alias in sorted_aliases:
		pattern=re.compile(rf"\b{re.escape(alias)}\b",re.IGNORECASE)
		if pattern.search(text_lower):canonical=DEPARTMENT_ALIASES[alias];normalized_text=pattern.sub(canonical,text);logger.debug(f"Department alias matched: '{alias}' -> '{canonical}'");return normalized_text,canonical
	return text,_L
def normalize_category(text):
	text_lower=text.lower();sorted_aliases=sorted(CATEGORY_ALIASES.keys(),key=len,reverse=_W)
	for alias in sorted_aliases:
		pattern=re.compile(rf"\b{re.escape(alias)}\b",re.IGNORECASE)
		if pattern.search(text_lower):canonical=CATEGORY_ALIASES[alias];normalized_text=pattern.sub(canonical,text);logger.debug(f"Category alias matched: '{alias}' -> '{canonical}'");return normalized_text,canonical
	return text,_L
def normalize_incident_type(text):
	text_lower=text.lower();sorted_aliases=sorted(INCIDENT_ALIASES.keys(),key=len,reverse=_W)
	for alias in sorted_aliases:
		pattern=re.compile(rf"\b{re.escape(alias)}\b",re.IGNORECASE)
		if pattern.search(text_lower):canonical=INCIDENT_ALIASES[alias];normalized_text=pattern.sub(canonical,text);logger.debug(f"Incident alias matched: '{alias}' -> '{canonical}'");return normalized_text,canonical
	return text,_L
@lru_cache(maxsize=512)
def normalize_query(text):
	if not text:return'',{}
	normalized=text;matched_entities={};normalized,prop=normalize_property_name(normalized)
	if prop:matched_entities[_AG]=prop
	normalized,incident=normalize_incident_type(normalized)
	if incident:matched_entities[_AH]=incident
	normalized,sev=normalize_severity(normalized)
	if sev:matched_entities[_AI]=sev
	normalized,status=normalize_status(normalized)
	if status:matched_entities[_AJ]=status
	normalized,dept=normalize_department(normalized)
	if dept:matched_entities[_AK]=dept
	normalized,cat=normalize_category(normalized)
	if cat:matched_entities[_AL]=cat
	if matched_entities:logger.info(f"Query normalized: '{text}' -> '{normalized}' (entities: {matched_entities})")
	return normalized,matched_entities
def get_entity_hints(matched_entities):
	if not matched_entities:return''
	hints=[]
	for(column,value)in matched_entities.items():
		if column in(_AI,_AJ):hints.append(f"- Use {column} = '{value.lower()}' in WHERE clause")
		elif column==_AH:hints.append(f"- Use incident_name LIKE '%{value}%' or incident_name = '{value}' in WHERE clause")
		elif column in(_AG,_AK,_AL):hints.append(f"- Use {column} = '{value}' in WHERE clause")
	return'\n'.join(hints)
def expand_room_reference(text):
	pattern=re.compile('\\b(?:room|rm)\\s*#?\\s*(\\d+)\\b',re.IGNORECASE)
	def replace_room(match):room_num=match.group(1);return f"Room {room_num}"
	return pattern.sub(replace_room,text)
def preprocess_query(text):processed=expand_room_reference(text);processed,matched_entities=normalize_query(processed);hints=get_entity_hints(matched_entities);return processed,matched_entities,hints
def clear_normalization_cache():normalize_query.cache_clear();logger.info('Query normalization cache cleared')