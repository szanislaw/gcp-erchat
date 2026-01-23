# app/permissions_config.py
# UUID to database access mapping configuration

from typing import Dict

# Maps (account_uuid, property_uuid) tuples to allowed Athena targets and tables
PERMISSIONS_MAPPING: Dict[tuple, Dict[str, any]] = {
    # ============================================================================
    # SUPER ADMIN - Full access
    # ============================================================================
    ("00000000-0000-0000-0000-000000000000", "00000000-0000-0000-0000-000000000000"): {
        "athena_targets": ["peninsula_incident", "londoner_granded"],
        "tables": ["incident_combine", "incident_history", "incident_analytics", "ldco_testing"]
    },
    
    # ============================================================================
    # PENINSULA HOTELS - Main Account
    # ============================================================================
    # The Peninsula Hong Kong
    ("149cd8f0-00e1-43a4-840b-6a54b4f857f6", "8afe7e5e-22e5-4318-b5c7-f967fc44e81f"): {
        "athena_targets": ["peninsula_incident"],
        "tables": ["incident_combine", "incident_history", "incident_analytics"]
    },
    # The Peninsula Manila
    ("149cd8f0-00e1-43a4-840b-6a54b4f857f6", "c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"): {
        "athena_targets": ["peninsula_incident"],
        "tables": ["incident_combine", "incident_history", "incident_analytics"]
    },
    # The Peninsula Tokyo
    ("149cd8f0-00e1-43a4-840b-6a54b4f857f6", "1ef8175a-6d1d-418e-8a51-31848b147b53"): {
        "athena_targets": ["peninsula_incident"],
        "tables": ["incident_combine", "incident_history", "incident_analytics"]
    },
    # The Peninsula Bangkok
    ("149cd8f0-00e1-43a4-840b-6a54b4f857f6", "c0abc579-6ef4-47a3-8290-16cf26964aec"): {
        "athena_targets": ["peninsula_incident"],
        "tables": ["incident_combine", "incident_history", "incident_analytics"]
    },
    
    # ============================================================================
    # DEMO ACCOUNT
    # ============================================================================
    ("449b762c-a17c-425c-958b-bea436d531f6", "44cfe549-4eef-4ab8-890a-7ed2df45ea8f"): {
        "athena_targets": ["peninsula_incident"],
        "tables": ["incident_combine"]
    },
    
    # ============================================================================
    # LEGACY MAPPINGS (keep for backwards compatibility)
    # ============================================================================
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
}
