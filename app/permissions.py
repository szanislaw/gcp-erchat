# app/permissions.py
# Access control functions for account/property UUID authorization
# Refactored for ~90% accuracy with robust validation and matching

from typing import Dict, List, Optional, Set, Tuple, Any
from functools import lru_cache
import re
import logging
from app.permissions_config import PERMISSIONS_MAPPING
from app.user_table_permissions import (
    USER_TABLE_PERMISSIONS,
    get_user_tables,
    has_table_access,
    has_property_access,
    get_user_properties,
    get_property_name,
    TABLE_METADATA,
    PROPERTY_METADATA
)

# Configure logging for audit trail
logger = logging.getLogger(__name__)

# UUID validation regex pattern (standard UUID format)
UUID_PATTERN = re.compile(
    r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',
    re.IGNORECASE
)

# Extended UUID pattern (supports prefixed UUIDs like acc-xxx, prop-xxx)
EXTENDED_UUID_PATTERN = re.compile(
    r'^(?:[a-z]+-)?[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}[a-z]*$',
    re.IGNORECASE
)

# Wildcard key for super user access
WILDCARD_KEY = "*"


class PermissionError(Exception):
    """Custom exception for permission-related errors with detailed context"""
    def __init__(self, message: str, account_uuid: str = None, property_uuid: str = None,
                 error_code: str = "ACCESS_DENIED", suggestions: List[str] = None):
        self.message = message
        self.account_uuid = account_uuid
        self.property_uuid = property_uuid
        self.error_code = error_code
        self.suggestions = suggestions or []
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.message,
            "error_code": self.error_code,
            "account_uuid": self.account_uuid,
            "property_uuid": self.property_uuid,
            "suggestions": self.suggestions
        }


def normalize_uuid(uuid_str: str) -> str:
    """
    Normalize UUID to lowercase for consistent matching.
    Handles both standard and prefixed UUID formats.
    
    Args:
        uuid_str: The UUID string to normalize
        
    Returns:
        Lowercase, stripped UUID string
    """
    if not uuid_str:
        return ""
    return uuid_str.strip().lower()


def is_valid_uuid(uuid_str: str) -> bool:
    """
    Validate UUID format (supports standard and prefixed formats).
    
    Args:
        uuid_str: The UUID string to validate
        
    Returns:
        True if valid UUID format, False otherwise
    """
    if not uuid_str:
        return False
    normalized = normalize_uuid(uuid_str)
    return bool(UUID_PATTERN.match(normalized) or EXTENDED_UUID_PATTERN.match(normalized))


def _build_normalized_permissions() -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
    Build normalized permissions dictionary with lowercase keys for case-insensitive matching.
    
    Returns:
        Dictionary with normalized (lowercase) UUID tuple keys
    """
    normalized = {}
    for (account_uuid, property_uuid), access in PERMISSIONS_MAPPING.items():
        # Normalize table names to lowercase for consistent matching
        normalized_access = {
            "athena_targets": [t.lower() for t in access["athena_targets"]],
            "tables": [t.lower() for t in access["tables"]],
            # Preserve original for reference
            "_original_tables": access["tables"],
            "_original_targets": access["athena_targets"]
        }
        normalized_key = (normalize_uuid(account_uuid), normalize_uuid(property_uuid))
        normalized[normalized_key] = normalized_access
    return normalized


# Pre-build normalized permissions at module load
PERMISSIONS = _build_normalized_permissions()


@lru_cache(maxsize=256)
def get_allowed_access(account_uuid: str, property_uuid: str) -> Optional[Dict[str, Any]]:
    """
    Return allowed athena targets and tables for given account/property UUID pair.
    Uses case-insensitive matching with caching for performance.
    
    Lookup priority:
    1. Exact match (normalized)
    2. Wildcard account match (*, property_uuid)
    3. Wildcard property match (account_uuid, *)
    4. Super wildcard match (*, *)
    
    Args:
        account_uuid: Account UUID from request
        property_uuid: Property UUID from request
        
    Returns:
        Dictionary with athena_targets and tables, or None if no access granted
    """
    norm_account = normalize_uuid(account_uuid)
    norm_property = normalize_uuid(property_uuid)
    
    # Priority 1: Exact match
    exact_key = (norm_account, norm_property)
    if exact_key in PERMISSIONS:
        logger.debug(f"Exact permission match for {exact_key}")
        return PERMISSIONS[exact_key]
    
    # Priority 2: Wildcard account match
    wildcard_account_key = (WILDCARD_KEY, norm_property)
    if wildcard_account_key in PERMISSIONS:
        logger.debug(f"Wildcard account match for property {norm_property}")
        return PERMISSIONS[wildcard_account_key]
    
    # Priority 3: Wildcard property match
    wildcard_property_key = (norm_account, WILDCARD_KEY)
    if wildcard_property_key in PERMISSIONS:
        logger.debug(f"Wildcard property match for account {norm_account}")
        return PERMISSIONS[wildcard_property_key]
    
    # Priority 4: Super wildcard match (universal access)
    super_wildcard_key = (WILDCARD_KEY, WILDCARD_KEY)
    if super_wildcard_key in PERMISSIONS:
        logger.debug(f"Super wildcard match applied")
        return PERMISSIONS[super_wildcard_key]
    
    logger.warning(f"No permission match found for account={account_uuid}, property={property_uuid}")
    return None


def get_all_allowed_tables(account_uuid: str, property_uuid: str) -> Set[str]:
    """
    Get all allowed tables for the given account/property combination.
    
    Args:
        account_uuid: Account UUID from request
        property_uuid: Property UUID from request
        
    Returns:
        Set of allowed table names (lowercase)
    """
    access = get_allowed_access(account_uuid, property_uuid)
    if access is None:
        return set()
    return set(access["tables"])


def get_all_allowed_targets(account_uuid: str, property_uuid: str) -> Set[str]:
    """
    Get all allowed Athena targets for the given account/property combination.
    
    Args:
        account_uuid: Account UUID from request
        property_uuid: Property UUID from request
        
    Returns:
        Set of allowed target names (lowercase)
    """
    access = get_allowed_access(account_uuid, property_uuid)
    if access is None:
        return set()
    return set(access["athena_targets"])


def validate_access(account_uuid: str, property_uuid: str, 
                     requested_target: str, requested_tables: List[str]) -> bool:
    """
    Validate if the account/property has access to the requested target and tables.
    Uses case-insensitive matching for robust validation.
    
    Args:
        account_uuid: Account UUID from request
        property_uuid: Property UUID from request
        requested_target: Athena target name from request
        requested_tables: List of table names from request
        
    Returns:
        True if access is allowed
        
    Raises:
        PermissionError: If validation fails with detailed context
    """
    # Validate UUID formats
    if not is_valid_uuid(account_uuid):
        raise PermissionError(
            message=f"Invalid account UUID format: '{account_uuid}'",
            account_uuid=account_uuid,
            property_uuid=property_uuid,
            error_code="INVALID_UUID_FORMAT",
            suggestions=[
                "UUID must be in format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "Prefixed formats like acc-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx are also supported"
            ]
        )
    
    if not is_valid_uuid(property_uuid):
        raise PermissionError(
            message=f"Invalid property UUID format: '{property_uuid}'",
            account_uuid=account_uuid,
            property_uuid=property_uuid,
            error_code="INVALID_UUID_FORMAT",
            suggestions=[
                "UUID must be in format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "Prefixed formats like prop-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx are also supported"
            ]
        )
    
    access = get_allowed_access(account_uuid, property_uuid)
    
    if access is None:
        # Provide helpful suggestions
        available_accounts = set(k[0] for k in PERMISSIONS.keys() if k[0] != WILDCARD_KEY)
        suggestions = [
            "Check that account and property UUIDs are correctly paired",
            "Contact administrator to request access"
        ]
        if available_accounts:
            suggestions.append(f"Available test accounts: {list(available_accounts)[:3]}")
            
        raise PermissionError(
            message=f"Access denied: No permissions found for account {account_uuid} and property {property_uuid}",
            account_uuid=account_uuid,
            property_uuid=property_uuid,
            error_code="NO_PERMISSION_MAPPING",
            suggestions=suggestions
        )
    
    # Normalize for comparison
    norm_target = requested_target.lower() if requested_target else ""
    allowed_targets = set(access["athena_targets"])
    
    # Check if requested target is allowed
    if norm_target not in allowed_targets:
        raise PermissionError(
            message=f"Access denied: Target '{requested_target}' not allowed",
            account_uuid=account_uuid,
            property_uuid=property_uuid,
            error_code="TARGET_NOT_ALLOWED",
            suggestions=[
                f"Allowed targets: {list(access['_original_targets'])}",
                "Check that you're using the correct database target for your property"
            ]
        )
    
    # Check if all requested tables are allowed
    allowed_tables = set(access["tables"])
    requested_set = set(t.lower() for t in requested_tables if t)
    
    unauthorized_tables = requested_set - allowed_tables
    if unauthorized_tables:
        raise PermissionError(
            message=f"Access denied: Tables not allowed: {list(unauthorized_tables)}",
            account_uuid=account_uuid,
            property_uuid=property_uuid,
            error_code="TABLE_NOT_ALLOWED",
            suggestions=[
                f"Allowed tables: {list(access['_original_tables'])}",
                "Query must only reference tables you have access to"
            ]
        )
    
    logger.info(f"Access validated for account={account_uuid}, property={property_uuid}, "
                f"target={requested_target}, tables={requested_tables}")
    return True


def validate_tables_in_sql(sql: str, allowed_tables: List[str]) -> List[str]:
    """
    Extract and validate all tables referenced in SQL against allowed tables.
    Handles FROM, JOIN, and subquery table references.
    
    Args:
        sql: SQL query string
        allowed_tables: List of allowed table names
        
    Returns:
        List of validated table names found in query
        
    Raises:
        PermissionError: If unauthorized tables are found
    """
    if not sql:
        return []
    
    sql_lower = sql.lower()
    
    # Comprehensive table extraction patterns
    patterns = [
        r'\bfrom\s+([a-zA-Z_][\w]*)',           # FROM table
        r'\bjoin\s+([a-zA-Z_][\w]*)',           # JOIN table  
        r'\binner\s+join\s+([a-zA-Z_][\w]*)',   # INNER JOIN table
        r'\bleft\s+(?:outer\s+)?join\s+([a-zA-Z_][\w]*)',   # LEFT [OUTER] JOIN table
        r'\bright\s+(?:outer\s+)?join\s+([a-zA-Z_][\w]*)',  # RIGHT [OUTER] JOIN table
        r'\bfull\s+(?:outer\s+)?join\s+([a-zA-Z_][\w]*)',   # FULL [OUTER] JOIN table
        r'\bcross\s+join\s+([a-zA-Z_][\w]*)',   # CROSS JOIN table
        r'\binto\s+([a-zA-Z_][\w]*)',           # INTO table (for INSERT)
        r'\bupdate\s+([a-zA-Z_][\w]*)',         # UPDATE table
    ]
    
    found_tables = set()
    for pattern in patterns:
        matches = re.findall(pattern, sql_lower, re.IGNORECASE)
        found_tables.update(matches)
    
    # Normalize allowed tables
    allowed_set = set(t.lower() for t in allowed_tables)
    
    # Check for unauthorized tables
    unauthorized = found_tables - allowed_set
    if unauthorized:
        raise PermissionError(
            message=f"SQL contains unauthorized tables: {list(unauthorized)}",
            error_code="UNAUTHORIZED_TABLES_IN_SQL",
            suggestions=[
                f"Allowed tables: {allowed_tables}",
                "Modify your query to only reference authorized tables"
            ]
        )
    
    return list(found_tables)


def clear_permission_cache():
    """Clear the LRU cache for permissions lookups (useful for testing/hot-reloading)"""
    get_allowed_access.cache_clear()
    logger.info("Permission cache cleared")


def validate_user_table_access(user_uuid: Optional[str], property_uuid: str, 
                               requested_tables: List[str]) -> bool:
    """
    Validate user-level table access for a specific property. This provides an additional 
    layer of access control beyond account/property permissions.
    
    If user_uuid is None, this check is skipped (backward compatibility).
    If user_uuid is provided, the user must have access to the property and 
    tables must be in the user's allowed list for that property.
    
    Args:
        user_uuid: User's UUID (optional)
        property_uuid: Property UUID from the request
        requested_tables: List of table names being queried
        
    Returns:
        True if access is allowed
        
    Raises:
        PermissionError: If user doesn't have access to the property or requested tables
    """
    # Skip user-level check if no user_uuid provided (backward compatibility)
    if not user_uuid:
        logger.debug("No user_uuid provided, skipping user-level table validation")
        return True
    
    normalized_user = user_uuid.strip().lower()
    normalized_property = property_uuid.strip().lower()
    
    # Check if user exists in permissions
    if normalized_user not in USER_TABLE_PERMISSIONS:
        raise PermissionError(
            message=f"User UUID '{user_uuid}' not found in table permissions",
            error_code="USER_NOT_FOUND",
            suggestions=[
                "Contact administrator to add your user UUID to table permissions",
                "Check that the user UUID is correct"
            ]
        )
    
    # Check if user has access to this property
    if not has_property_access(user_uuid, property_uuid):
        user_properties = get_user_properties(user_uuid)
        property_names = [get_property_name(p) for p in user_properties if p in PROPERTY_METADATA]
        raise PermissionError(
            message=f"User {user_uuid} does not have access to property {property_uuid}",
            error_code="USER_PROPERTY_NOT_ALLOWED",
            suggestions=[
                f"Your allowed properties: {property_names if property_names else user_properties}",
                "Contact administrator to request access to this property",
                "Use a different property UUID that you have access to"
            ]
        )
    
    # Get user's allowed tables for this specific property
    user_allowed_tables = get_user_tables(normalized_user, normalized_property)
    
    # Check if user has wildcard access
    user_all_properties = USER_TABLE_PERMISSIONS.get(normalized_user, [])
    if "*" in user_all_properties:
        logger.debug(f"User {user_uuid} has wildcard property access")
        return True
    
    # Normalize table names for comparison
    user_allowed_set = set(t.lower() for t in user_allowed_tables)
    requested_set = set(t.lower() for t in requested_tables if t)
    
    # Check for unauthorized tables at user level
    unauthorized_tables = requested_set - user_allowed_set
    if unauthorized_tables:
        property_name = get_property_name(property_uuid)
        raise PermissionError(
            message=f"User {user_uuid} does not have access to tables: {list(unauthorized_tables)} for property {property_name or property_uuid}",
            error_code="USER_TABLE_NOT_ALLOWED",
            suggestions=[
                f"Your allowed tables for this property: {user_allowed_tables}",
                "Contact administrator to request additional table access",
                "Modify your query to only use tables you have access to"
            ]
        )
    
    property_name = get_property_name(property_uuid)
    logger.info(f"User {user_uuid} has valid access to tables {requested_tables} for property {property_name or property_uuid}")
    return True


def validate_access_with_user(account_uuid: str, property_uuid: str, 
                               user_uuid: Optional[str],
                               requested_target: str, requested_tables: List[str]) -> bool:
    """
    Comprehensive access validation combining account/property AND user-level permissions.
    
    Validation hierarchy:
    1. Account/property-level permissions (required)
    2. User-level table permissions (if user_uuid provided)
    
    Both levels must pass for access to be granted.
    
    Args:
        account_uuid: Account UUID from request
        property_uuid: Property UUID from request  
        user_uuid: User UUID from request (optional)
        requested_target: Athena target name from request
        requested_tables: List of table names from request
        
    Returns:
        True if all access checks pass
        
    Raises:
        PermissionError: If any validation fails with detailed context
    """
    # Step 1: Validate account/property level access
    validate_access(account_uuid, property_uuid, requested_target, requested_tables)
    
    # Step 2: Validate user-level property and table access (if user_uuid provided)
    validate_user_table_access(user_uuid, property_uuid, requested_tables)
    
    logger.info(f"Full access validated for account={account_uuid}, property={property_uuid}, "
                f"user={user_uuid}, target={requested_target}, tables={requested_tables}")
    return True

