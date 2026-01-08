# app/athena_config.py
import os

# AWS credentials will be loaded from environment variables or AWS credential chain
# Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables if needed
# Or use AWS CLI configuration (~/.aws/credentials)

ATHENA_TARGETS = {
    "peninsula_incident": {
        "region": os.getenv("AWS_REGION", "ap-east-1"),
        "database": "peninsula-incident2",
        "tables": ["incident_combine"],
        "s3_output": "s3://athena-query-results-ap-east-1/nlq/",
    },
    "londoner_granded": {
        "region": os.getenv("AWS_REGION", "ap-east-1"),
        "database": "londoner_granded",
        "tables": ["ldco_testing"],
        "s3_output": "s3://athena-query-results-ap-east-1/nlq/",
    }
}
