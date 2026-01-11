# app/permissions_config.py
# UUID to database access mapping configuration

from typing import Dict

# Maps (account_uuid, property_uuid) tuples to allowed Athena targets and tables
PERMISSIONS_MAPPING: Dict[tuple, Dict[str, any]] = {
    # Super user - full access to all targets and tables
    ("00000000-0000-0000-0000-000000000000", "00000000-0000-0000-0000-000000000000"): {
        "athena_targets": ["peninsula_incident", "londoner_granded"],
        "tables": ["incident_combine", "ldco_testing"]
    },
    
    # All 1s UUID - Peninsula access only
    ("11111111-1111-1111-1111-111111111111", "11111111-1111-1111-1111-111111111111"): {
        "athena_targets": ["peninsula_incident"],
        "tables": ["incident_combine"]
    },
    
    # Peninsula Hotel - Peninsula database access
    ("acc-123e4567-e89b-12d3-a456-426614174000", "prop-987f6543-e21a-45d6-b789-123456789abc"): {
        "athena_targets": ["peninsula_incident"],
        "tables": ["incident_combine"]
    },
    
    # The Londoner Hotel - Londoner Granded database access
    ("acc-234e5678-e89b-12d3-a456-426614174001", "prop-876f5432-e21a-45d6-b789-123456789def"): {
        "athena_targets": ["londoner_granded"],
        "tables": ["ldco_testing"]
    },
    
    # Another Peninsula property
    ("acc-345e6789-e89b-12d3-a456-426614174002", "prop-765f4321-e21a-45d6-b789-123456789ghi"): {
        "athena_targets": ["peninsula_incident"],
        "tables": ["incident_combine"]
    },
    
    # Another Londoner property
    ("acc-456e7890-e89b-12d3-a456-426614174003", "prop-654f3210-e21a-45d6-b789-123456789jkl"): {
        "athena_targets": ["londoner_granded"],
        "tables": ["ldco_testing"]
    },
    
    # Multi-database access example (user with access to both)
    ("acc-567e8901-e89b-12d3-a456-426614174004", "prop-543f2109-e21a-45d6-b789-123456789mno"): {
        "athena_targets": ["peninsula_incident", "londoner_granded"],
        "tables": ["incident_combine", "ldco_testing"]
    }
}
