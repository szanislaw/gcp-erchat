# Security Best Practices

## AWS Credentials

This application uses AWS Athena for data queries. **Never commit AWS credentials to the repository.**

### Recommended Setup

**Option 1: AWS CLI Configuration (Recommended)**
```bash
aws configure
```
This stores credentials securely in `~/.aws/credentials` and is the preferred method for local development.

**Option 2: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_REGION="ap-east-1"
```

**Option 3: Using a .env file**
```bash
cp .env.example .env
# Edit .env with your credentials (already gitignored)
```

### IAM Permissions Required

The AWS user/role needs the following permissions:
- `athena:StartQueryExecution`
- `athena:GetQueryExecution`
- `athena:GetQueryResults`
- `glue:GetTable`
- `glue:GetDatabase`
- `s3:PutObject` (for query results)
- `s3:GetObject` (for query results)
- `s3:ListBucket` (for the Athena output bucket)

### Credential Rotation

1. Regularly rotate AWS access keys (every 90 days recommended)
2. Use AWS IAM roles when running on AWS infrastructure (EC2, ECS, Lambda)
3. Never share credentials via chat, email, or commit them to version control

### If Credentials Are Exposed

If you accidentally commit credentials:
1. **Immediately revoke them** in AWS IAM Console
2. Generate new credentials
3. Update your local configuration
4. Consider using `git-secrets` or similar tools to prevent future exposure
