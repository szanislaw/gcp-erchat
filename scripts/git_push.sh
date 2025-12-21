#!/bin/bash
# Git add, commit, and push script

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if commit message is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Commit message required${NC}"
    echo "Usage: $0 \"Your commit message\""
    echo "Example: $0 \"Added systemd service and README\""
    exit 1
fi

COMMIT_MSG="$1"

echo -e "${YELLOW}=== Git Status ===${NC}"
git status

echo ""
echo -e "${YELLOW}=== Adding all changes ===${NC}"
git add .

echo ""
echo -e "${YELLOW}=== Committing with message: ${NC}\"$COMMIT_MSG\""
git commit -m "$COMMIT_MSG"

if [ $? -ne 0 ]; then
    echo -e "${RED}Commit failed. Check for errors above.${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}=== Pushing to remote ===${NC}"
git push

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Successfully pushed to GitHub!${NC}"
else
    echo ""
    echo -e "${RED}✗ Push failed. Check your network connection and credentials.${NC}"
    exit 1
fi
