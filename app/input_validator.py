# app/input_validator.py
"""
Input validation and sanitization for NLQ requests.
Provides security against XSS, injection, and malformed inputs.
"""

import re
import html
from typing import Tuple, List, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of input validation"""
    is_valid: bool
    sanitized_text: str
    warnings: List[str]
    error: Optional[str] = None


# HTML/Script patterns to detect XSS attempts
XSS_PATTERNS = [
    re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
    re.compile(r'javascript:', re.IGNORECASE),
    re.compile(r'on\w+\s*=', re.IGNORECASE),  # onclick=, onerror=, etc.
    re.compile(r'<iframe[^>]*>', re.IGNORECASE),
    re.compile(r'<object[^>]*>', re.IGNORECASE),
    re.compile(r'<embed[^>]*>', re.IGNORECASE),
    re.compile(r'<img[^>]+src\s*=\s*["\']?javascript:', re.IGNORECASE),
    re.compile(r'expression\s*\(', re.IGNORECASE),  # CSS expression
    re.compile(r'url\s*\(\s*["\']?javascript:', re.IGNORECASE),
]

# SQL injection patterns (beyond model-generated SQL)
INJECTION_PATTERNS = [
    re.compile(r";\s*drop\s+", re.IGNORECASE),
    re.compile(r";\s*delete\s+", re.IGNORECASE),
    re.compile(r";\s*insert\s+", re.IGNORECASE),
    re.compile(r";\s*update\s+", re.IGNORECASE),
    re.compile(r";\s*alter\s+", re.IGNORECASE),
    re.compile(r";\s*truncate\s+", re.IGNORECASE),
    re.compile(r";\s*grant\s+", re.IGNORECASE),
    re.compile(r";\s*revoke\s+", re.IGNORECASE),
    re.compile(r"union\s+all\s+select", re.IGNORECASE),
    re.compile(r"union\s+select", re.IGNORECASE),
    re.compile(r"'\s*;\s*--", re.IGNORECASE),
    re.compile(r'"\s*;\s*--', re.IGNORECASE),
]

# Dangerous characters that might indicate an attack
DANGEROUS_CHAR_PATTERN = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')

# Maximum input length
MAX_INPUT_LENGTH = 2000

# Minimum meaningful query length
MIN_INPUT_LENGTH = 2


def detect_xss(text: str) -> Tuple[bool, List[str]]:
    """
    Detect potential XSS attacks in input text.
    
    Returns:
        Tuple of (is_xss_detected, list of matched patterns)
    """
    matches = []
    for pattern in XSS_PATTERNS:
        if pattern.search(text):
            matches.append(pattern.pattern)
    return bool(matches), matches


def detect_injection(text: str) -> Tuple[bool, List[str]]:
    """
    Detect potential SQL injection patterns in input text.
    
    Returns:
        Tuple of (is_injection_detected, list of matched patterns)
    """
    matches = []
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            matches.append(pattern.pattern)
    return bool(matches), matches


def sanitize_text(text: str) -> str:
    """
    Sanitize input text by removing/escaping dangerous content.
    
    Args:
        text: Raw input text
        
    Returns:
        Sanitized text safe for processing
    """
    if not text:
        return ""
    
    # Remove null bytes and control characters
    sanitized = DANGEROUS_CHAR_PATTERN.sub('', text)
    
    # HTML escape to neutralize XSS
    sanitized = html.escape(sanitized, quote=True)
    
    # Remove excessive whitespace
    sanitized = ' '.join(sanitized.split())
    
    # Truncate to max length
    if len(sanitized) > MAX_INPUT_LENGTH:
        sanitized = sanitized[:MAX_INPUT_LENGTH]
    
    return sanitized


def validate_nlq_input(text: str, strict_mode: bool = True) -> ValidationResult:
    """
    Comprehensive validation of NLQ input text.
    
    Args:
        text: The natural language query text
        strict_mode: If True, reject suspicious inputs; if False, sanitize and warn
        
    Returns:
        ValidationResult with validation status and sanitized text
    """
    warnings = []
    
    # Check for None/empty
    if text is None:
        return ValidationResult(
            is_valid=False,
            sanitized_text="",
            warnings=[],
            error="Query text cannot be null"
        )
    
    # Trim whitespace
    text = text.strip()
    
    # Check minimum length
    if len(text) < MIN_INPUT_LENGTH:
        return ValidationResult(
            is_valid=False,
            sanitized_text=text,
            warnings=[],
            error=f"Query must be at least {MIN_INPUT_LENGTH} characters"
        )
    
    # Check maximum length
    if len(text) > MAX_INPUT_LENGTH:
        return ValidationResult(
            is_valid=False,
            sanitized_text=text[:MAX_INPUT_LENGTH],
            warnings=[f"Query exceeded max length of {MAX_INPUT_LENGTH} characters"],
            error=f"Query exceeds maximum length of {MAX_INPUT_LENGTH} characters"
        )
    
    # Check for XSS
    has_xss, xss_patterns = detect_xss(text)
    if has_xss:
        if strict_mode:
            return ValidationResult(
                is_valid=False,
                sanitized_text=sanitize_text(text),
                warnings=["XSS attempt detected"],
                error="Potentially malicious content detected in query"
            )
        warnings.append("Potential XSS content detected and neutralized")
    
    # Check for SQL injection in natural language input
    has_injection, inj_patterns = detect_injection(text)
    if has_injection:
        if strict_mode:
            return ValidationResult(
                is_valid=False,
                sanitized_text=sanitize_text(text),
                warnings=["SQL injection attempt detected"],
                error="Potentially malicious SQL patterns detected in query"
            )
        warnings.append("Potential SQL injection patterns detected")
    
    # Sanitize the text
    sanitized = sanitize_text(text)
    
    # Check if sanitization changed the text significantly
    if len(sanitized) < len(text) * 0.5 and len(text) > 20:
        warnings.append("Query was significantly modified during sanitization")
    
    return ValidationResult(
        is_valid=True,
        sanitized_text=sanitized,
        warnings=warnings,
        error=None
    )


def validate_uuid_format(uuid_str: str) -> bool:
    """
    Validate UUID format.
    
    Args:
        uuid_str: String to validate
        
    Returns:
        True if valid UUID format
    """
    if not uuid_str:
        return False
    
    # Standard UUID pattern
    uuid_pattern = re.compile(
        r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',
        re.IGNORECASE
    )
    
    # Extended UUID pattern (with prefixes like acc-, prop-)
    extended_pattern = re.compile(
        r'^(?:[a-z]+-)?[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}[a-z]*$',
        re.IGNORECASE
    )
    
    return bool(uuid_pattern.match(uuid_str) or extended_pattern.match(uuid_str))
