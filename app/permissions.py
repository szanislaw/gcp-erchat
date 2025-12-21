# app/permissions.py
# Hard-coded access control mapping for account/property UUIDs to allowed tables

from typing import Dict, List, Optional

# Maps (account_uuid, property_uuid) tuples to allowed Athena targets and tables
PERMISSIONS: Dict[tuple, Dict[str, any]] = {
    # Super user - full access to all targets and tables
    ("00000000-0000-0000-0000-000000000000", "00000000-0000-0000-0000-000000000000"): {
        "athena_targets": ["peninsula_incident", "londoner_granded"],
        "tables": ["incident_combine", "ldco_testing"]
    },
    
# CHANGE THESE TO REAL UUIDS FOR PRODUCTION USE
# Example entries:

    # # Peninsula Incident access
    # ("acc-123e4567-e89b-12d3-a456-426614174000", "prop-987f6543-e21a-45d6-b789-123456789abc"): {
    #     "athena_targets": ["peninsula_incident"],
    #     "tables": ["incident_combine"]
    # },
    
    # # Londoner Granded access
    # ("acc-234e5678-e89b-12d3-a456-426614174001", "prop-876f5432-e21a-45d6-b789-123456789def"): {
    #     "athena_targets": ["londoner_granded"],
    #     "tables": ["ldco_testing"]
    # },
    
    # # Multi-property access example
    # ("acc-345e6789-e89b-12d3-a456-426614174002", "prop-765f4321-e21a-45d6-b789-123456789ghi"): {
    #     "athena_targets": ["peninsula_incident", "londoner_granded"],
    #     "tables": ["incident_combine", "ldco_testing"]
    # }
}


def get_allowed_access(account_uuid: str, property_uuid: str) -> Optional[Dict[str, any]]:
    """
    Return allowed athena targets and tables for given account/property UUID pair.
    Returns None if no access granted.
    """
    key = (account_uuid, property_uuid)
    return PERMISSIONS.get(key)


def validate_access(account_uuid: str, property_uuid: str, 
                     requested_target: str, requested_tables: List[str]) -> bool:
    """
    Validate if the account/property has access to the requested target and tables.
    
    Args:
        account_uuid: Account UUID from request
        property_uuid: Property UUID from request
        requested_target: Athena target name from request
        requested_tables: List of table names from request
        
    Returns:
        True if access is allowed, False otherwise
        
    Raises:
        ValueError: If account/property combination is not authorized
    """
    access = get_allowed_access(account_uuid, property_uuid)
    
    if access is None:
        raise ValueError(
            f"Access denied: No permissions found for account {account_uuid} "
            f"and property {property_uuid}"
        )
    
    # Check if requested target is allowed
    if requested_target not in access["athena_targets"]:
        raise ValueError(
            f"Access denied: Target '{requested_target}' not allowed. "
            f"Allowed targets: {access['athena_targets']}"
        )
    
    # Check if all requested tables are allowed
    for table in requested_tables:
        if table not in access["tables"]:
            raise ValueError(
                f"Access denied: Table '{table}' not allowed. "
                f"Allowed tables: {access['tables']}"
            )
    
    return True
