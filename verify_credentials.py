#!/usr/bin/env python3
"""
Credential Verification Script
Checks if all AWS credentials are properly configured for the application.
"""

import os
import sys
from dotenv import load_dotenv

# Colors for terminal output
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


def print_header(text):
    print(f"\n{BLUE}{'=' * 60}{NC}")
    print(f"{BLUE}{text.center(60)}{NC}")
    print(f"{BLUE}{'=' * 60}{NC}\n")


def print_success(text):
    print(f"{GREEN}✓ {text}{NC}")


def print_warning(text):
    print(f"{YELLOW}⚠ {text}{NC}")


def print_error(text):
    print(f"{RED}✗ {text}{NC}")


def check_env_file():
    """Check if .env file exists"""
    print_header("1. Checking .env File")
    
    if os.path.exists('.env'):
        print_success(".env file exists")
        return True
    else:
        print_error(".env file not found")
        print_warning("Create .env from template: cp .env.example .env")
        return False


def load_environment():
    """Load environment variables from .env file"""
    print_header("2. Loading Environment Variables")
    
    try:
        load_dotenv()
        print_success("Environment variables loaded from .env")
        return True
    except Exception as e:
        print_error(f"Failed to load .env: {e}")
        return False


def check_required_vars():
    """Check if all required environment variables are set"""
    print_header("3. Checking Required Variables")
    
    required_vars = {
        'AWS_ACCESS_KEY_ID': 'AWS Access Key ID',
        'AWS_SECRET_ACCESS_KEY': 'AWS Secret Access Key',
        'AWS_REGION': 'AWS Region'
    }
    
    all_present = True
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask the credential for security
            if 'KEY' in var or 'SECRET' in var:
                masked = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '***'
                print_success(f"{description}: {masked}")
            else:
                print_success(f"{description}: {value}")
        else:
            print_error(f"{description} is not set")
            all_present = False
    
    return all_present


def check_optional_vars():
    """Check optional configuration variables"""
    print_header("4. Checking Optional Variables")
    
    optional_vars = {
        'API_PORT': ('API Port', '8000'),
        'API_HOST': ('API Host', '0.0.0.0'),
        'STREAMLIT_PORT': ('Streamlit Port', '8501')
    }
    
    for var, (description, default) in optional_vars.items():
        value = os.getenv(var, default)
        if value == default:
            print_warning(f"{description}: {value} (using default)")
        else:
            print_success(f"{description}: {value}")


def test_aws_connection():
    """Test AWS credentials by making a simple API call"""
    print_header("5. Testing AWS Connection")
    
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        
        # Try to create a client and get caller identity
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()
        
        print_success("AWS credentials are valid")
        print(f"   Account: {identity['Account']}")
        print(f"   User/Role: {identity['Arn']}")
        return True
        
    except NoCredentialsError:
        print_error("No AWS credentials found")
        return False
    except ClientError as e:
        print_error(f"AWS credential error: {e}")
        return False
    except ImportError:
        print_warning("boto3 not installed - skipping AWS connection test")
        return None
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def check_athena_access():
    """Check if Athena access is available"""
    print_header("6. Testing Athena Access")
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        region = os.getenv('AWS_REGION', 'ap-east-1')
        athena_client = boto3.client('athena', region_name=region)
        
        # Try to list work groups (doesn't execute queries, just checks permissions)
        response = athena_client.list_work_groups(MaxResults=1)
        
        print_success(f"Athena access verified in region: {region}")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDeniedException':
            print_error("No Athena access - check IAM permissions")
        else:
            print_error(f"Athena error: {error_code}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def check_gitignore():
    """Verify .env is in .gitignore"""
    print_header("7. Checking Git Security")
    
    try:
        with open('.gitignore', 'r') as f:
            gitignore_content = f.read()
        
        if '.env' in gitignore_content:
            print_success(".env is in .gitignore")
        else:
            print_error(".env is NOT in .gitignore - credentials may be exposed!")
            return False
        
        # Check if .env is actually ignored by git
        import subprocess
        result = subprocess.run(
            ['git', 'check-ignore', '-v', '.env'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print_success(".env is properly ignored by git")
            return True
        else:
            print_warning(".env might not be properly ignored by git")
            return False
            
    except FileNotFoundError:
        print_warning(".gitignore not found")
        return False
    except Exception as e:
        print_warning(f"Could not verify git status: {e}")
        return None


def main():
    print_header("AWS Credential Verification")
    print("This script verifies your AWS credentials setup\n")
    
    results = []
    
    # Run all checks
    results.append(("ENV File", check_env_file()))
    results.append(("Load ENV", load_environment()))
    results.append(("Required Vars", check_required_vars()))
    check_optional_vars()  # Just informational
    results.append(("AWS Connection", test_aws_connection()))
    results.append(("Athena Access", check_athena_access()))
    results.append(("Git Security", check_gitignore()))
    
    # Summary
    print_header("Summary")
    
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)
    
    print(f"Passed:  {passed}")
    print(f"Failed:  {failed}")
    print(f"Skipped: {skipped}\n")
    
    if failed == 0:
        print_success("✓ All credential checks passed!")
        print_success("Your application is properly configured.\n")
        return 0
    else:
        print_error("✗ Some checks failed")
        print_warning("Please fix the issues above before running the application.\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
