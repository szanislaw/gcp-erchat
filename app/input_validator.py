_A=False
import re,html
from typing import Tuple,List,Optional
from dataclasses import dataclass
@dataclass
class ValidationResult:is_valid:bool;sanitized_text:str;warnings:List[str];error:Optional[str]=None
XSS_PATTERNS=[re.compile('<script[^>]*>.*?</script>',re.IGNORECASE|re.DOTALL),re.compile('javascript:',re.IGNORECASE),re.compile('on\\w+\\s*=',re.IGNORECASE),re.compile('<iframe[^>]*>',re.IGNORECASE),re.compile('<object[^>]*>',re.IGNORECASE),re.compile('<embed[^>]*>',re.IGNORECASE),re.compile('<img[^>]+src\\s*=\\s*["\\\']?javascript:',re.IGNORECASE),re.compile('expression\\s*\\(',re.IGNORECASE),re.compile('url\\s*\\(\\s*["\\\']?javascript:',re.IGNORECASE)]
INJECTION_PATTERNS=[re.compile(';\\s*drop\\s+',re.IGNORECASE),re.compile(';\\s*delete\\s+',re.IGNORECASE),re.compile(';\\s*insert\\s+',re.IGNORECASE),re.compile(';\\s*update\\s+',re.IGNORECASE),re.compile(';\\s*alter\\s+',re.IGNORECASE),re.compile(';\\s*truncate\\s+',re.IGNORECASE),re.compile(';\\s*grant\\s+',re.IGNORECASE),re.compile(';\\s*revoke\\s+',re.IGNORECASE),re.compile('union\\s+all\\s+select',re.IGNORECASE),re.compile('union\\s+select',re.IGNORECASE),re.compile("'\\s*;\\s*--",re.IGNORECASE),re.compile('"\\s*;\\s*--',re.IGNORECASE)]
DANGEROUS_CHAR_PATTERN=re.compile('[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f]')
MAX_INPUT_LENGTH=2000
MIN_INPUT_LENGTH=2
def detect_xss(text):
	matches=[]
	for pattern in XSS_PATTERNS:
		if pattern.search(text):matches.append(pattern.pattern)
	return bool(matches),matches
def detect_injection(text):
	matches=[]
	for pattern in INJECTION_PATTERNS:
		if pattern.search(text):matches.append(pattern.pattern)
	return bool(matches),matches
def sanitize_text(text):
	if not text:return''
	sanitized=DANGEROUS_CHAR_PATTERN.sub('',text);sanitized=html.escape(sanitized,quote=True);sanitized=' '.join(sanitized.split())
	if len(sanitized)>MAX_INPUT_LENGTH:sanitized=sanitized[:MAX_INPUT_LENGTH]
	return sanitized
def validate_nlq_input(text,strict_mode=True):
	warnings=[]
	if text is None:return ValidationResult(is_valid=_A,sanitized_text='',warnings=[],error='Query text cannot be null')
	text=text.strip()
	if len(text)<MIN_INPUT_LENGTH:return ValidationResult(is_valid=_A,sanitized_text=text,warnings=[],error=f"Query must be at least {MIN_INPUT_LENGTH} characters")
	if len(text)>MAX_INPUT_LENGTH:return ValidationResult(is_valid=_A,sanitized_text=text[:MAX_INPUT_LENGTH],warnings=[f"Query exceeded max length of {MAX_INPUT_LENGTH} characters"],error=f"Query exceeds maximum length of {MAX_INPUT_LENGTH} characters")
	has_xss,xss_patterns=detect_xss(text)
	if has_xss:
		if strict_mode:return ValidationResult(is_valid=_A,sanitized_text=sanitize_text(text),warnings=['XSS attempt detected'],error='Potentially malicious content detected in query')
		warnings.append('Potential XSS content detected and neutralized')
	has_injection,inj_patterns=detect_injection(text)
	if has_injection:
		if strict_mode:return ValidationResult(is_valid=_A,sanitized_text=sanitize_text(text),warnings=['SQL injection attempt detected'],error='Potentially malicious SQL patterns detected in query')
		warnings.append('Potential SQL injection patterns detected')
	sanitized=sanitize_text(text)
	if len(sanitized)<len(text)*.5 and len(text)>20:warnings.append('Query was significantly modified during sanitization')
	return ValidationResult(is_valid=True,sanitized_text=sanitized,warnings=warnings,error=None)
def validate_uuid_format(uuid_str):
	if not uuid_str:return _A
	uuid_pattern=re.compile('^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',re.IGNORECASE);extended_pattern=re.compile('^(?:[a-z]+-)?[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}[a-z]*$',re.IGNORECASE);return bool(uuid_pattern.match(uuid_str)or extended_pattern.match(uuid_str))