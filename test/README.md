# Test & Development Files

This directory contains testing scripts, development tools, and archived files that are not needed for production deployment.

## 📁 Contents

### Testing Scripts
- **`test_questions.py`** - Test suite with sample NLQ queries
- **`test_suggestions.py`** - Tests for query suggestion functionality
- **`stress_test.py`** - Load/stress testing tool
- **`stress_test_report_*.txt`** - Stress test results
- **`stress_test_final.log`** - Final stress test logs

### Development Tools
- **`generate_payloads.py`** - Tool to generate sample API payloads
- **`sample_payloads.json`** - Sample request payloads for testing
- **`debug_query.py`** - Debugging utility for query analysis
- **`health_check.py`** - Health check testing utility

### Archives
- **`archive/`** - Old code versions and deprecated files
- **`clis/`** - CLI commands reference and templates
  - `clis.txt` - Various CLI commands
  - `curl-request-template.txt` - cURL request examples
  - `git-cmds.txt` - Git commands reference
  - `systemctl-cmds.txt` - Systemctl commands

## 🧪 Running Tests

### Basic Tests
```bash
# Run test questions
python test/test_questions.py

# Test query suggestions
python test/test_suggestions.py
```

### Stress Testing
```bash
# Run stress test
python test/stress_test.py

# View results
cat test/stress_test_report_*.txt
```

### Payload Generation
```bash
# Generate and test payloads
python test/generate_payloads.py

# View sample payloads
cat test/sample_payloads.json
```

## 📝 Notes

- These files are excluded from production deployments
- Keep test files updated when API changes
- Review stress test reports before major releases
- Archive folder contains historical references only

## 🚫 Not for Production

**Do not deploy this folder to production environments.**
It contains development tools, test data, and archived code.
