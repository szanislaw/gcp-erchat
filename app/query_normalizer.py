# app/query_normalizer.py
# Natural language query normalization for ~90% accuracy
# Handles entity aliases, abbreviations, and fuzzy matching
# Updated with real data from Athena database

from typing import Dict, List, Tuple, Optional, Set
from functools import lru_cache
import re
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# ENTITY ALIASES: Maps common variations to canonical database values
# Data sourced from actual Athena database queries
# ============================================================================

# Property/Hotel name aliases -> canonical name in database
# Actual DB values: The Peninsula Bangkok, The Peninsula Manila, 
#                   The Peninsula Hong Kong, The Peninsula London, The Peninsula Istanbul
PROPERTY_ALIASES: Dict[str, str] = {
    # Bangkok
    "peninsula bangkok": "The Peninsula Bangkok",
    "pen bangkok": "The Peninsula Bangkok",
    "bkk peninsula": "The Peninsula Bangkok",
    "peninsula bkk": "The Peninsula Bangkok",
    "bangkok": "The Peninsula Bangkok",
    "bkk": "The Peninsula Bangkok",
    
    # Manila
    "peninsula manila": "The Peninsula Manila",
    "pen manila": "The Peninsula Manila",
    "manila peninsula": "The Peninsula Manila",
    "manila": "The Peninsula Manila",
    "mnl": "The Peninsula Manila",
    
    # Hong Kong
    "peninsula hong kong": "The Peninsula Hong Kong",
    "peninsula hk": "The Peninsula Hong Kong",
    "pen hk": "The Peninsula Hong Kong",
    "hk peninsula": "The Peninsula Hong Kong",
    "hong kong": "The Peninsula Hong Kong",
    "hk": "The Peninsula Hong Kong",
    "hongkong": "The Peninsula Hong Kong",
    
    # London
    "peninsula london": "The Peninsula London",
    "pen london": "The Peninsula London",
    "london peninsula": "The Peninsula London",
    "london": "The Peninsula London",
    "ldn": "The Peninsula London",
    
    # Istanbul
    "peninsula istanbul": "The Peninsula Istanbul",
    "pen istanbul": "The Peninsula Istanbul",
    "istanbul peninsula": "The Peninsula Istanbul",
    # Note: Don't add just "istanbul" to avoid false matches like "Disturbance"
    
    # Generic Peninsula references (will need context)
    "the peninsula": "The Peninsula",  # Keep generic
}

# Severity aliases -> canonical database value (actual DB values: high, medium, low, critical)
SEVERITY_ALIASES: Dict[str, str] = {
    # Critical mappings
    "critical": "critical",
    "emergency": "critical",
    "urgent": "critical",
    
    # High mappings
    "high": "high",
    "important": "high",
    "serious": "high",
    "severe": "high",
    "major": "high",
    "priority": "high",
    
    # Medium mappings
    "medium": "medium",
    "moderate": "medium",
    "normal": "medium",
    "standard": "medium",
    "regular": "medium",
    "average": "medium",
    
    # Low mappings  
    "low": "low",
    "minor": "low",
    "trivial": "low",
    "small": "low",
    "insignificant": "low",
    "minimal": "low",
}

# Status aliases -> canonical database value (actual DB values: pending, completed, cancelled)
STATUS_ALIASES: Dict[str, str] = {
    # Pending mappings
    "pending": "pending",
    "open": "pending",
    "active": "pending",
    "in progress": "pending",
    "ongoing": "pending",
    "unresolved": "pending",
    "outstanding": "pending",
    "waiting": "pending",
    "new": "pending",
    "not completed": "pending",
    "incomplete": "pending",
    
    # Completed mappings
    "completed": "completed",
    "done": "completed",
    "finished": "completed",
    "resolved": "completed",
    "closed": "completed",
    "fixed": "completed",
    "complete": "completed",
    
    # Cancelled mappings
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "dropped": "cancelled",
    "abandoned": "cancelled",
    "voided": "cancelled",
    "withdrawn": "cancelled",
}

# Department aliases -> canonical database value
# Actual DB values include: Housekeeping, Front Office, IT, Engineering, Events, 
#                           Spa & Wellness, Food & Beverage, Security, etc.
DEPARTMENT_ALIASES: Dict[str, str] = {
    # Housekeeping
    "hk": "Housekeeping",
    "housekeeping": "Housekeeping",
    "house keeping": "Housekeeping",
    "cleaning": "Housekeeping",
    "cleaners": "Housekeeping",
    "room cleaning": "Housekeeping",
    
    # Food & Beverage
    "fb": "Food & Beverage",
    "f&b": "Food & Beverage",
    "food and beverage": "Food & Beverage",
    "food beverage": "Food & Beverage",
    "restaurant": "Food & Beverage",
    "dining": "Food & Beverage",
    "kitchen": "Food & Beverage",
    "fnb": "Food & Beverage",
    
    # Front Office
    "fo": "Front Office",
    "front office": "Front Office",
    "front desk": "Front Office",
    "reception": "Front Office",
    "check in": "Front Office",
    "check-in": "Front Office",
    "checkout": "Front Office",
    "check-out": "Front Office",
    
    # Concierge
    "concierge": "Concierge",
    
    # Engineering
    "eng": "Engineering",
    "engineering": "Engineering",
    "maintenance": "Engineering",
    "technical": "Engineering",
    "repair": "Engineering",
    "repairs": "Engineering",
    
    # Security / Safety
    "sec": "Security",
    "security": "Security",
    "safety": "Safety & Security",
    "safety & security": "Safety & Security",
    "safety and security": "Safety & Security",
    
    # Spa & Wellness
    "spa": "Spa & Wellness",
    "wellness": "Spa & Wellness",
    "spa & wellness": "Spa & Wellness",
    "spa and wellness": "Spa & Wellness",
    "massage": "Spa & Wellness",
    
    # IT
    "it": "IT",
    "tech": "IT",
    "technology": "IT",
    "it & elv": "IT & ELV",
    
    # Room Service / In Room Dining
    "room service": "Room Service",
    "ird": "In Room Dining",
    "in room dining": "In Room Dining",
    "in-room dining": "In Room Dining",
    "inroom dining": "In Room Dining",
    
    # Guest Services
    "guest services": "Guest Services",
    "guest service": "Guest Service",
    "guest experience": "Guest Experience",
    "gcc": "Guest Communication Centre",
    "gcc": "GCC",
    
    # Events & Banquets
    "events": "Events",
    "banquet": "Banquet & Event",
    "banquets": "Banquets & Events",
    "banquet & event": "Banquet & Event",
    
    # Transportation
    "transport": "Transportation",
    "transportation": "Transportation",
    "driver": "Transportation",
    "limo": "Transportation",
    "car": "Transportation",
    
    # The Lobby
    "lobby": "The Lobby",
    "the lobby": "The Lobby",
    
    # Laundry
    "laundry": "Laundry",
    
    # Reservations
    "reservations": "Reservations",
    "reservation": "Reservation",
    "booking": "Reservations",
}

# Category aliases -> canonical database value
# Actual DB values: Food & Beverage, Systems, Billing, Service Quality, Room Condition,
#                   Security, Front Office, Transportation, Hotel Facilities, Housekeeping,
#                   Disturbance, Reservations, Guest Services, Guest Room, Health & Safety, etc.
CATEGORY_ALIASES: Dict[str, str] = {
    # Room Condition
    "room condition": "Room Condition",
    "room cleanliness": "Room Condition",
    "dirty room": "Room Condition",
    "unclean room": "Room Condition",
    "cleaning issue": "Room Condition",
    "room issue": "Room Condition",
    
    # Guest Room
    "guest room": "Guest Room",
    "guestroom": "Guest Room",
    "room": "Guest Room",
    
    # Housekeeping (category)
    "housekeeping": "Housekeeping",
    
    # Service Quality
    "service": "Service Quality",
    "service quality": "Service Quality",
    "poor service": "Service Quality",
    "bad service": "Service Quality",
    "staff attitude": "Service Quality",
    "attitude": "Service Quality",
    
    # Food & Beverage (category)
    "food": "Food & Beverage",
    "beverage": "Food & Beverage",
    "food & beverage": "Food & Beverage",
    "food and beverage": "Food & Beverage",
    "restaurant": "Food & Beverage",
    "dining": "Food & Beverage",
    
    # Billing
    "billing": "Billing",
    "bill": "Billing",
    "payment": "Billing",
    "charge": "Billing",
    "invoice": "Billing",
    "dispute": "Billing",
    
    # Disturbance / Noise
    "noise": "Disturbance",
    "disturbance": "Disturbance",
    "loud": "Disturbance",
    "noisy": "Disturbance",
    "noise complaint": "Disturbance",
    
    # Security
    "security": "Security",
    "theft": "Security",
    "lost": "Security",
    "stolen": "Security",
    "lost property": "Security",
    
    # Health & Safety
    "health & safety": "Health & Safety",
    "health and safety": "Health & Safety",
    "safety": "Health & Safety",
    "injury": "Health & Safety",
    "sickness": "Health & Safety",
    "illness": "Health & Safety",
    "medical": "Health & Safety",
    
    # Systems
    "systems": "Systems",
    "system": "Systems",
    "technical": "Systems",
    "it issue": "Systems",
    
    # Hotel Facilities
    "facilities": "Hotel Facilities",
    "hotel facilities": "Hotel Facilities",
    "facility": "Hotel Facilities",
    "pool": "Pool",
    "gym": "Hotel Facilities",
    "fitness": "Hotel Facilities",
    
    # Front Office (category)
    "front office": "Front Office",
    "check-in": "Front Office",
    "check in": "Front Office",
    "checkout": "Front Office",
    
    # Transportation
    "transportation": "Transportation",
    "transport": "Transportation",
    
    # Reservations
    "reservation": "Reservation",
    "reservations": "Reservations",
    "booking": "Reservations",
    
    # Spa
    "spa": "Spa",
    
    # Laundry
    "laundry": "Laundry",
    
    # Data Privacy
    "data privacy": "Data Privacy",
    "privacy": "Data Privacy",
    "gdpr": "Data Privacy",
    
    # Product Quality
    "product quality": "Product Quality",
    "quality": "Product Quality",
    
    # Clinic
    "clinic": "Clinic",
    "doctor": "Clinic",
}

# Common incident type aliases
INCIDENT_ALIASES: Dict[str, str] = {
    # Plumbing
    "plumbing": "Plumbing / Drainage Issue",
    "drainage": "Plumbing / Drainage Issue",
    "clogged": "Plumbing / Drainage Issue",
    "blocked drain": "Plumbing / Drainage Issue",
    "toilet": "Plumbing / Drainage Issue",
    "leak": "Plumbing / Drainage Issue",
    
    # AC / Temperature
    "ac issue": "AC Issue",
    "ac": "AC Issue",
    "air conditioning": "AC Issue",
    "aircon": "AC Issue",
    "temperature": "AC Issue",
    "cold room": "AC Issue",
    "hot room": "AC Issue",
    
    # Noise
    "noise": "Noise - Guest Room",
    "noisy": "Noise - Guest Room",
    "loud": "Noise - Guest Room",
    
    # Lost property
    "lost property": "Lost / Damaged Guest Property",
    "lost item": "Lost / Damaged Guest Property",
    "missing item": "Lost / Damaged Guest Property",
    "damaged property": "Lost / Damaged Guest Property",
    
    # Staff attitude
    "staff attitude": "Staff Attitude",
    "rude staff": "Staff Attitude",
    "unfriendly": "Staff Attitude",
    
    # Delay
    "delay": "Delay of Service",
    "waiting": "Long Waiting Time",
    "slow service": "Delay of Service",
    
    # Billing
    "billing issue": "Billing Issue / Dispute Charge",
    "wrong charge": "Billing Issue / Dispute Charge",
    "overcharge": "Billing Issue / Dispute Charge",
    
    # Food related
    "foreign object": "Foreign Object in Food / Beverage",
    "hair in food": "Foreign Object in Food / Beverage",
    "food illness": "Alleged Food-borne Illness",
    "food poisoning": "Alleged Food-borne Illness",
    
    # Power
    "power failure": "Power Failure / Black Out",
    "blackout": "Power Failure / Black Out",
    "power outage": "Power Failure / Black Out",
    "no power": "Power Failure / Black Out",
    
    # Room not ready
    "room not ready": "Room Not Ready / Front Office",
    "wait for room": "Wait for Room",
    
    # Smell
    "smell": "Abnormal Smell / Odour",
    "odour": "Abnormal Smell / Odour",
    "odor": "Abnormal Smell / Odour",
    "sewage smell": "Sewage Smell",
    
    # Guest injury
    "injury": "Guest Injury / Sickness",
    "injured": "Guest Injury / Sickness",
    "sick": "Guest Injury / Sickness",
    "medical": "Guest Injury / Sickness",
    "medical emergency": "Code 444 - Medical Emergency",
    
    # Positive feedback
    "positive": "Positive Comments",
    "compliment": "Positive Comments",
    "praise": "Positive Comments",
    "good feedback": "Positive Feedback",
}

# Time expression normalization
TIME_ALIASES: Dict[str, str] = {
    "today": "today",
    "yesterday": "1 day ago",
    "this week": "last 7 days",
    "last week": "last 7 days",
    "past week": "last 7 days",
    "this month": "last 30 days",
    "last month": "last 30 days",
    "past month": "last 30 days",
    "this year": "last 365 days",
    "recent": "last 7 days",
    "recently": "last 7 days",
    "latest": "last 7 days",
}

# ============================================================================
# FUZZY MATCHING UTILITIES
# ============================================================================

def _normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, collapse whitespace, strip."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text.lower().strip())


def _calculate_similarity(s1: str, s2: str) -> float:
    """
    Calculate similarity ratio between two strings using character-level comparison.
    Returns value between 0.0 (no match) and 1.0 (exact match).
    """
    if not s1 or not s2:
        return 0.0
    
    s1_norm = _normalize_text(s1)
    s2_norm = _normalize_text(s2)
    
    if s1_norm == s2_norm:
        return 1.0
    
    # Check if one contains the other
    if s1_norm in s2_norm or s2_norm in s1_norm:
        return 0.8
    
    # Character-level Jaccard similarity
    set1 = set(s1_norm.replace(" ", ""))
    set2 = set(s2_norm.replace(" ", ""))
    
    if not set1 or not set2:
        return 0.0
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    return intersection / union if union > 0 else 0.0


def _find_best_match(query: str, candidates: Dict[str, str], threshold: float = 0.7) -> Optional[str]:
    """
    Find the best matching canonical value for a query string.
    
    Args:
        query: The user's input text
        candidates: Dict mapping aliases to canonical values
        threshold: Minimum similarity score to accept a match
        
    Returns:
        Canonical value if match found, None otherwise
    """
    query_norm = _normalize_text(query)
    
    # Exact match first
    if query_norm in candidates:
        return candidates[query_norm]
    
    # Fuzzy match
    best_score = 0.0
    best_match = None
    
    for alias, canonical in candidates.items():
        score = _calculate_similarity(query_norm, alias)
        if score > best_score and score >= threshold:
            best_score = score
            best_match = canonical
    
    return best_match


# ============================================================================
# QUERY NORMALIZATION FUNCTIONS
# ============================================================================

def normalize_property_name(text: str) -> Tuple[str, Optional[str]]:
    """
    Extract and normalize property/hotel name from query text.
    
    Args:
        text: User's query text
        
    Returns:
        Tuple of (normalized_text, canonical_property_name or None)
    """
    text_lower = text.lower()
    
    # Sort aliases by length (longest first) to match most specific first
    sorted_aliases = sorted(PROPERTY_ALIASES.keys(), key=len, reverse=True)
    
    for alias in sorted_aliases:
        # Use word boundary matching to avoid partial word matches
        pattern = re.compile(rf'\b{re.escape(alias)}\b', re.IGNORECASE)
        if pattern.search(text_lower):
            canonical = PROPERTY_ALIASES[alias]
            normalized_text = pattern.sub(canonical, text, count=1)
            logger.debug(f"Property alias matched: '{alias}' -> '{canonical}'")
            return normalized_text, canonical
    
    return text, None


def normalize_severity(text: str) -> Tuple[str, Optional[str]]:
    """Normalize severity-related terms in query text."""
    text_lower = text.lower()
    
    for alias, canonical in SEVERITY_ALIASES.items():
        # Use word boundary matching to avoid partial matches
        pattern = re.compile(rf'\b{re.escape(alias)}\b', re.IGNORECASE)
        if pattern.search(text_lower):
            normalized_text = pattern.sub(canonical, text)
            logger.debug(f"Severity alias matched: '{alias}' -> '{canonical}'")
            return normalized_text, canonical
    
    return text, None


def normalize_status(text: str) -> Tuple[str, Optional[str]]:
    """Normalize status-related terms in query text."""
    text_lower = text.lower()
    
    for alias, canonical in STATUS_ALIASES.items():
        pattern = re.compile(rf'\b{re.escape(alias)}\b', re.IGNORECASE)
        if pattern.search(text_lower):
            normalized_text = pattern.sub(canonical, text)
            logger.debug(f"Status alias matched: '{alias}' -> '{canonical}'")
            return normalized_text, canonical
    
    return text, None


def normalize_department(text: str) -> Tuple[str, Optional[str]]:
    """Normalize department-related terms in query text."""
    text_lower = text.lower()
    
    # Sort by length (longest first) to match most specific first
    sorted_aliases = sorted(DEPARTMENT_ALIASES.keys(), key=len, reverse=True)
    
    for alias in sorted_aliases:
        pattern = re.compile(rf'\b{re.escape(alias)}\b', re.IGNORECASE)
        if pattern.search(text_lower):
            canonical = DEPARTMENT_ALIASES[alias]
            normalized_text = pattern.sub(canonical, text)
            logger.debug(f"Department alias matched: '{alias}' -> '{canonical}'")
            return normalized_text, canonical
    
    return text, None


def normalize_category(text: str) -> Tuple[str, Optional[str]]:
    """Normalize category-related terms in query text."""
    text_lower = text.lower()
    
    # Sort by length for longest match first
    sorted_aliases = sorted(CATEGORY_ALIASES.keys(), key=len, reverse=True)
    
    for alias in sorted_aliases:
        # Use word boundary for more accurate matching
        pattern = re.compile(rf'\b{re.escape(alias)}\b', re.IGNORECASE)
        if pattern.search(text_lower):
            canonical = CATEGORY_ALIASES[alias]
            normalized_text = pattern.sub(canonical, text)
            logger.debug(f"Category alias matched: '{alias}' -> '{canonical}'")
            return normalized_text, canonical
    
    return text, None


def normalize_incident_type(text: str) -> Tuple[str, Optional[str]]:
    """Normalize incident type references in query text."""
    text_lower = text.lower()
    
    # Sort by length for longest match first
    sorted_aliases = sorted(INCIDENT_ALIASES.keys(), key=len, reverse=True)
    
    for alias in sorted_aliases:
        # Use word boundary for more accurate matching
        pattern = re.compile(rf'\b{re.escape(alias)}\b', re.IGNORECASE)
        if pattern.search(text_lower):
            canonical = INCIDENT_ALIASES[alias]
            normalized_text = pattern.sub(canonical, text)
            logger.debug(f"Incident alias matched: '{alias}' -> '{canonical}'")
            return normalized_text, canonical
    
    return text, None


@lru_cache(maxsize=512)
def normalize_query(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Fully normalize a natural language query, resolving all known aliases.
    
    Args:
        text: The user's natural language query
        
    Returns:
        Tuple of (normalized_text, dict of matched_entities)
    """
    if not text:
        return "", {}
    
    normalized = text
    matched_entities: Dict[str, str] = {}
    
    # Apply normalizations in order of specificity (most specific first)
    normalized, prop = normalize_property_name(normalized)
    if prop:
        matched_entities["property_name"] = prop
    
    normalized, incident = normalize_incident_type(normalized)
    if incident:
        matched_entities["incident_name"] = incident
    
    normalized, sev = normalize_severity(normalized)
    if sev:
        matched_entities["severity_name"] = sev
    
    normalized, status = normalize_status(normalized)
    if status:
        matched_entities["status_name"] = status
    
    normalized, dept = normalize_department(normalized)
    if dept:
        matched_entities["department_name"] = dept
    
    normalized, cat = normalize_category(normalized)
    if cat:
        matched_entities["category_name"] = cat
    
    if matched_entities:
        logger.info(f"Query normalized: '{text}' -> '{normalized}' (entities: {matched_entities})")
    
    return normalized, matched_entities


def get_entity_hints(matched_entities: Dict[str, str]) -> str:
    """
    Generate SQL hints based on matched entities for the prompt.
    
    Args:
        matched_entities: Dict of column_name -> canonical_value pairs
        
    Returns:
        String of SQL hints to include in prompt
    """
    if not matched_entities:
        return ""
    
    hints = []
    for column, value in matched_entities.items():
        if column in ("severity_name", "status_name"):
            # These should be lowercase in SQL
            hints.append(f"- Use {column} = '{value.lower()}' in WHERE clause")
        elif column == "incident_name":
            # Incident names may need LIKE for partial matching
            hints.append(f"- Use incident_name LIKE '%{value}%' or incident_name = '{value}' in WHERE clause")
        elif column in ("property_name", "department_name", "category_name"):
            # These preserve case
            hints.append(f"- Use {column} = '{value}' in WHERE clause")
    
    return "\n".join(hints)


def expand_room_reference(text: str) -> str:
    """
    Expand room references to match database format.
    E.g., "room 1018" -> "Room 1018"
    """
    # Match patterns like "room 1018", "rm 1018", "room #1018"
    pattern = re.compile(r'\b(?:room|rm)\s*#?\s*(\d+)\b', re.IGNORECASE)
    
    def replace_room(match):
        room_num = match.group(1)
        return f"Room {room_num}"
    
    return pattern.sub(replace_room, text)


def preprocess_query(text: str) -> Tuple[str, Dict[str, str], str]:
    """
    Full preprocessing pipeline for natural language queries.
    
    Args:
        text: Raw user query
        
    Returns:
        Tuple of (processed_text, matched_entities, entity_hints)
    """
    # Step 1: Expand room references
    processed = expand_room_reference(text)
    
    # Step 2: Normalize all entity references
    processed, matched_entities = normalize_query(processed)
    
    # Step 3: Generate hints for the prompt
    hints = get_entity_hints(matched_entities)
    
    return processed, matched_entities, hints


def clear_normalization_cache():
    """Clear the normalization cache (useful for testing/hot-reloading)."""
    normalize_query.cache_clear()
    logger.info("Query normalization cache cleared")
