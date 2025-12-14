# app/athena_config.py

ATHENA_TARGETS = {
    "peninsula_incident": {
        "region": "ap-east-1",
        "database": "peninsula-incident2",
        "tables": ["incident_combine"],
        "s3_output": "s3://athena-query-results-ap-east-1/nlq/",
        "aws_access_key_id": "AKIAS32K2RHTLENNC44O",
        "aws_secret_access_key": "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"
    },
    "londoner_granded": {
        "region": "ap-east-1",
        "database": "londoner_granded",
        "tables": ["ldco_testing"],
        "s3_output": "s3://athena-query-results-ap-east-1/nlq/",
        "aws_access_key_id": "AKIAS32K2RHTLENNC44O",
        "aws_secret_access_key": "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"
    }
}
