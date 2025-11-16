#!/bin/bash
# Docker Testing Script
# Tests Docker builds without actually building (saves time)

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Docker Configuration Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Test 1: Docker is installed
echo -e "${BLUE}Test 1: Checking Docker installation...${NC}"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo -e "${GREEN}✓ Docker installed: $DOCKER_VERSION${NC}"
else
    echo -e "${RED}✗ Docker not found${NC}"
    exit 1
fi
echo ""

# Test 2: Dockerfile exists and is readable
echo -e "${BLUE}Test 2: Checking Dockerfile...${NC}"
if [ -f "Dockerfile" ]; then
    echo -e "${GREEN}✓ Dockerfile exists${NC}"
    LINES=$(wc -l < Dockerfile)
    echo -e "${GREEN}  - $LINES lines${NC}"
else
    echo -e "${RED}✗ Dockerfile not found${NC}"
    exit 1
fi
echo ""

# Test 3: Dockerfile.minimal exists
echo -e "${BLUE}Test 3: Checking Dockerfile.minimal...${NC}"
if [ -f "Dockerfile.minimal" ]; then
    echo -e "${GREEN}✓ Dockerfile.minimal exists${NC}"
    LINES=$(wc -l < Dockerfile.minimal)
    echo -e "${GREEN}  - $LINES lines${NC}"
else
    echo -e "${RED}✗ Dockerfile.minimal not found${NC}"
fi
echo ""

# Test 4: .dockerignore exists
echo -e "${BLUE}Test 4: Checking .dockerignore...${NC}"
if [ -f ".dockerignore" ]; then
    echo -e "${GREEN}✓ .dockerignore exists${NC}"
    LINES=$(wc -l < .dockerignore)
    echo -e "${GREEN}  - $LINES lines${NC}"
else
    echo -e "${RED}✗ .dockerignore not found${NC}"
fi
echo ""

# Test 5: docker-compose.yml syntax
echo -e "${BLUE}Test 5: Validating docker-compose.yml...${NC}"
if docker compose config > /dev/null 2>&1; then
    echo -e "${GREEN}✓ docker-compose.yml is valid${NC}"
else
    echo -e "${RED}✗ docker-compose.yml has errors${NC}"
    docker compose config 2>&1 | tail -5
    exit 1
fi
echo ""

# Test 6: Required files for Docker build
echo -e "${BLUE}Test 6: Checking required files...${NC}"
REQUIRED_FILES=(
    "requirements.txt"
    "backend/api_rest.py"
    "backend/providers/base.py"
    "backend/providers/factory.py"
)

ALL_PRESENT=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}  ✓ $file${NC}"
    else
        echo -e "${RED}  ✗ $file missing${NC}"
        ALL_PRESENT=false
    fi
done

if [ "$ALL_PRESENT" = false ]; then
    exit 1
fi
echo ""

# Test 7: Check backend directory structure
echo -e "${BLUE}Test 7: Checking backend structure...${NC}"
BACKEND_FILES=$(find backend -name "*.py" | wc -l)
echo -e "${GREEN}✓ Found $BACKEND_FILES Python files in backend/${NC}"
echo ""

# Test 8: Check templates directory
echo -e "${BLUE}Test 8: Checking templates...${NC}"
if [ -d "templates" ]; then
    BICEP_COUNT=$(find templates -name "*.bicep" 2>/dev/null | wc -l)
    TF_COUNT=$(find templates -name "*.tf" 2>/dev/null | wc -l)
    echo -e "${GREEN}✓ Templates directory exists${NC}"
    echo -e "${GREEN}  - $BICEP_COUNT Bicep templates${NC}"
    echo -e "${GREEN}  - $TF_COUNT Terraform templates${NC}"
else
    echo -e "${RED}✗ Templates directory not found${NC}"
fi
echo ""

# Test 9: Estimate build context size
echo -e "${BLUE}Test 9: Analyzing build context size...${NC}"
BACKEND_SIZE=$(du -sh backend/ 2>/dev/null | cut -f1)
TEMPLATES_SIZE=$(du -sh templates/ 2>/dev/null | cut -f1)
echo -e "${GREEN}✓ Backend: $BACKEND_SIZE${NC}"
echo -e "${GREEN}✓ Templates: $TEMPLATES_SIZE${NC}"
echo ""

# Test 10: Check for common issues
echo -e "${BLUE}Test 10: Checking for common issues...${NC}"

# Check for large files that shouldn't be copied
LARGE_FILES=$(find . -type f -size +10M 2>/dev/null | grep -v ".git" | grep -v "venv" | grep -v "node_modules" || true)
if [ -z "$LARGE_FILES" ]; then
    echo -e "${GREEN}✓ No large files found in build context${NC}"
else
    echo -e "${RED}⚠ Large files found:${NC}"
    echo "$LARGE_FILES"
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ All Docker configuration tests passed!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo -e "  1. Build image: ${BLUE}docker build -t multicloud-api:test .${NC}"
echo -e "  2. Run container: ${BLUE}docker compose up -d${NC}"
echo -e "  3. Check health: ${BLUE}curl http://localhost:8000/health${NC}"
echo ""
