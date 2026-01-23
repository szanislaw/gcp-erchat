# Deployment Guide

## 📋 Pre-Deployment Checklist

### ✅ Environment Setup
- [ ] Copy `.env.example` to `.env`
- [ ] Configure AWS credentials (access key, secret key, region)
- [ ] Set up Athena database and workgroup
- [ ] Configure account/property UUIDs in `app/permissions_config.py`
- [ ] **Configure user UUID to table mappings in `app/user_table_permissions.py`**
- [ ] Update `app/athena_config.py` with database details

### ✅ Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt

# Verify installation
python -c "import torch; import transformers; print('Dependencies OK')"
```

### ✅ Security
- [ ] Review `SECURITY.md`
- [ ] Update CORS settings in `app/main.py` (line 62)
- [ ] Configure rate limiting in `app/rate_limiter.py`
- [ ] Enable SQL validation in `app/security.py`
- [ ] Set up user UUID mappings for table access control
- [ ] Set up proper authentication/authorization

### ✅ Testing
```bash
# Run local tests
cd test/
python test_questions.py
python stress_test.py

# Check health endpoint
curl http://localhost:8080/health
```

---

## 🚀 Deployment Options

### Option 1: Bash Script Service (Recommended)

The application includes bash scripts for easy deployment and management.

#### Start the API Server
```bash
# Make scripts executable
chmod +x restart_servers.sh run_streamlit.sh

# Start API server in background
./restart_servers.sh

# Or start manually with uvicorn
nohup uvicorn app.main:app --host 0.0.0.0 --port 8080 > logs/api.log 2>&1 &
```

#### Start Streamlit UI (Optional)
```bash
# Start Streamlit UI
./run_streamlit.sh

# Or manually
nohup streamlit run streamlit_app.py --server.port 8501 > logs/streamlit.log 2>&1 &
```

#### Management Scripts
```bash
# Check if services are running
ps aux | grep uvicorn
ps aux | grep streamlit

# View logs
tail -f logs/api.log
tail -f logs/streamlit.log

# Stop services
pkill -f uvicorn
pkill -f streamlit

# Restart
./restart_servers.sh
```

### Option 2: Systemd Service (Production Linux)

```bash
# Copy service file
sudo cp scripts/nlq-api.service /etc/systemd/system/

# Edit service file to match your paths
sudo nano /etc/systemd/system/nlq-api.service

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable nlq-api
sudo systemctl start nlq-api
sudo systemctl status nlq-api
```

### Option 2: Systemd Service (Production Linux)

For production deployments with automatic restart and logging:

```bash
# Copy service file
sudo cp scripts/nlq-api.service /etc/systemd/system/

# Edit service file to match your paths
sudo nano /etc/systemd/system/nlq-api.service

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable nlq-api
sudo systemctl start nlq-api
sudo systemctl status nlq-api

# View logs
sudo journalctl -u nlq-api -f
```

### Option 3: Screen/Tmux Sessions

For persistent sessions that survive SSH disconnections:

#### Using Screen
```bash
# Start new screen session
screen -S nlq-api

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8080

# Detach: Ctrl+A then D
# Reattach: screen -r nlq-api
# List sessions: screen -ls
```

#### Using Tmux
```bash
# Start new tmux session
tmux new -s nlq-api

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8080

# Detach: Ctrl+B then D
# Reattach: tmux attach -t nlq-api
# List sessions: tmux ls
```

### Option 4: Docker (Advanced - Optional)

If you later decide to containerize:

Create `Dockerfile`:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY streamlit_app.py .
COPY static/ ./static/

# Expose ports
EXPOSE 8080 8501

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

Build and run:
```bash
docker build -t nlq-api .
docker run -d -p 8080:8080 --env-file .env nlq-api
```

---

## 🔧 User UUID Configuration

### Setting Up User Table Permissions

Edit `app/user_table_permissions.py` to configure which users can access which tables:

```python
USER_TABLE_PERMISSIONS: Dict[str, List[str]] = {
    # Admin with full access
    "user-00000000-0000-0000-0000-000000000000": ["*"],
    
    # Regular user with specific table access
    "user-123e4567-e89b-12d3-a456-426614174000": [
        "incident_combine",
        "incident_analytics"
    ],
    
    # Add your users here:
    "user-YOUR-UUID-HERE": [
        "table1",
        "table2"
    ],
}
```

### Testing User Access

```bash
# Test with user_uuid in payload
curl -X POST http://localhost:8080/nlq/execute \
  -H "Content-Type: application/json" \
  -d '{
    "text": "How many incidents?",
    "context": {
      "account_uuid": "acc-12345",
      "property_uuid": "prop-67890",
      "user_uuid": "user-YOUR-UUID-HERE"
    },
    "sql": {"dialect": "athena"},
    "execution": {"dry_run": true},
    "model": {},
    "trace": {}
  }'
```

### Access Control Hierarchy

The system validates access at **two levels**:

1. **Account/Property Level** (`permissions_config.py`)
   - Controls which databases and tables the account/property can access
   - Required for all requests

2. **User Level** (`user_table_permissions.py`) 
   - Controls which specific tables individual users can query
   - Optional - only checked if `user_uuid` is provided
   - Provides fine-grained access control within an account

**Both levels must pass for access to be granted.**

---

## 🔧 Configuration Files

### Production Environment Variables
```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=us-east-1

# Athena Configuration
ATHENA_DATABASE=your_database
ATHENA_WORKGROUP=primary
ATHENA_OUTPUT_LOCATION=s3://your-bucket/athena-results/

# Application Configuration
API_HOST=0.0.0.0
API_PORT=8080
LOG_LEVEL=INFO
RATE_LIMIT_REQUESTS_PER_SECOND=2
RATE_LIMIT_BURST_SIZE=10

# Model Configuration
MODEL_NAME=Ellbendls/Qwen-2.5-3b-Text_to_SQL
MODEL_DEVICE=cuda  # or cpu
```

---

## 📊 Monitoring & Logging

### Log Files
- `logs/api_requests.json` - API request logs
- Application logs via stdout/stderr

### Health Check Endpoint
```bash
curl http://localhost:8080/health
# Expected: {"status": "healthy", "model": "loaded"}
```

### Metrics to Monitor
- Request latency (p50, p95, p99)
- Error rate
- Model inference time
- Athena query execution time
- Rate limit hits
- Memory usage (model loaded ~6GB)

---

## 🔒 Production Security Best Practices

1. **API Security**
   - Enable authentication (JWT, API keys)
   - Use HTTPS only
   - Implement request signing
   - Rate limiting per user/tenant

2. **SQL Security**
   - Enable SQL validation (already implemented)
   - Whitelist allowed tables
   - Restrict DDL operations
   - Use IAM roles for AWS

3. **Network Security**
   - Use VPC for AWS resources
   - Configure security groups
   - Enable AWS WAF
   - Use private subnets

4. **Secrets Management**
   - Use AWS Secrets Manager or Parameter Store
   - Never commit `.env` files
   - Rotate credentials regularly

---

## 🔄 Post-Deployment

### Verify Deployment
```bash
# Test API endpoint
curl -X POST http://your-domain:8080/nlq/execute \
  -H "Content-Type: application/json" \
  -d @test/sample_payloads.json

# Check logs
tail -f logs/api_requests.json

# Monitor system resources
htop  # or your monitoring tool
```

### Rollback Plan
1. Keep previous version tagged in Git
2. Have docker image backup
3. Document rollback procedure
4. Test rollback in staging first

---

## 📞 Support & Troubleshooting

### Common Issues

**Model fails to load:**
- Check available RAM (needs ~6GB)
- Verify HuggingFace model download
- Check disk space

**Athena queries fail:**
- Verify AWS credentials
- Check IAM permissions
- Validate database/table names
- Review query logs

**High latency:**
- Check model inference time
- Monitor Athena query performance
- Review rate limiting settings
- Consider caching strategies

**Out of Memory:**
- Reduce batch size
- Use smaller model
- Increase instance size
- Enable model quantization

---

## 🎯 Performance Optimization

1. **Model Optimization**
   - Use quantized models (int8)
   - Enable GPU inference
   - Implement request batching

2. **Caching**
   - Cache frequent queries
   - Cache schema information
   - Use Redis for distributed cache

3. **Database**
   - Optimize Athena partitions
   - Use columnar formats (Parquet)
   - Pre-aggregate common queries

4. **Infrastructure**
   - Use CDN for static assets
   - Load balancer for multiple instances
   - Auto-scaling based on load

---

## 📈 Scaling Considerations

- **Horizontal:** Add more API instances behind load balancer
- **Vertical:** Increase instance size for model performance
- **Database:** Athena scales automatically
- **Caching:** Add Redis/Memcached layer
- **Async:** Queue heavy requests for background processing

---

## 📚 Additional Resources

- [README.md](README.md) - Project overview
- [QUICK_START.md](QUICK_START.md) - Quick start guide
- [SECURITY.md](SECURITY.md) - Security guidelines
- [documentation/](documentation/) - Technical documentation
