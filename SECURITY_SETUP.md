# Security Setup Guide

## 🔒 Environment Variables & Secrets Management

### Quick Setup

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your actual credentials:**
   ```bash
   nano .env
   ```

3. **Verify `.env` is git-ignored:**
   ```bash
   git check-ignore -v .env
   # Should output: .gitignore:14:.env    .env
   ```

## 📋 Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key for Athena | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | `********` |
| `AWS_REGION` | AWS region | `ap-east-1` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_PORT` | FastAPI port | `8000` |
| `API_HOST` | FastAPI host | `0.0.0.0` |
| `STREAMLIT_PORT` | Streamlit port | `8501` |

## 🛡️ Security Best Practices

### ✅ DO

- ✅ Use `.env` file for local development
- ✅ Use AWS IAM roles for production (EC2, ECS, Lambda)
- ✅ Rotate credentials regularly (every 90 days)
- ✅ Use least-privilege IAM policies
- ✅ Store production secrets in AWS Secrets Manager
- ✅ Review `.gitignore` before committing

### ❌ DON'T

- ❌ Commit `.env` to version control
- ❌ Share credentials via email/chat
- ❌ Use production credentials in development
- ❌ Hardcode credentials in code
- ❌ Use root AWS account credentials
- ❌ Expose `.env` in Docker builds

## 🔍 Files Protected by `.gitignore`

The following files/patterns are automatically excluded from git:

```
.env                    # Your actual credentials
.env.*                  # Any .env variants (e.g., .env.local)
venv/, .venv/          # Python virtual environments
__pycache__/           # Python cache
*.pyc, *.pyo           # Compiled Python files
logs/*.json            # Application logs
app/athena_config.py   # Config with potential sensitive data
app/permissions_config.py
```

**Note:** `.env.example` is **not** ignored - it's a template with placeholder values.

## 🚀 Production Deployment

### Option 1: AWS IAM Roles (Recommended)

For EC2, ECS, or Lambda:

```bash
# No environment variables needed!
# AWS SDK automatically uses instance role
```

### Option 2: AWS Secrets Manager

```python
# Example integration (not yet implemented)
import boto3

client = boto3.client('secretsmanager')
response = client.get_secret_value(SecretId='prod/nlq-api/credentials')
```

### Option 3: Environment Variables

Set via deployment platform:
- **EC2**: Use `/etc/environment` or systemd service file
- **Docker**: Use `docker run -e` or docker-compose
- **Kubernetes**: Use Secrets and ConfigMaps

## 🔐 Credential Verification

Check what credentials are currently active:

```bash
# Check AWS configuration
aws sts get-caller-identity

# Should output:
# {
#     "UserId": "AIDA...",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/your-user"
# }
```

## 🆘 Troubleshooting

### "NoCredentialsError: Unable to locate credentials"

**Solution:**
1. Verify `.env` file exists in project root
2. Check variables are set: `cat .env`
3. Restart the API server
4. Alternative: Configure AWS CLI: `aws configure`

### ".env file is tracked by git"

**Solution:**
```bash
# Remove from git tracking
git rm --cached .env

# Verify it's in .gitignore
git check-ignore -v .env
```

### "Credentials exposed in repository"

**URGENT ACTION:**
1. Immediately rotate the exposed credentials in AWS IAM
2. Remove from git history:
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all
   ```
3. Force push: `git push origin --force --all`
4. Notify your security team

## 📞 Support

For security-related issues, contact your DevSecOps team immediately.

**Never share credentials in:**
- Chat applications
- Email
- GitHub issues/discussions
- Documentation files
- Code comments
