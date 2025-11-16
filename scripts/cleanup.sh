#!/bin/bash
# Project Cleanup Script
# Removes temporary files, cache, and build artifacts

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Project Cleanup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Python cache
echo -e "${BLUE}Cleaning Python cache...${NC}"
find . -path ./venv -prune -o -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -path ./venv -prune -o -name "*.pyc" -delete 2>/dev/null || true
find . -path ./venv -prune -o -name "*.pyo" -delete 2>/dev/null || true
find . -path ./venv -prune -o -name "*.pyd" -delete 2>/dev/null || true
echo -e "${GREEN}✓ Python cache cleaned${NC}"
echo ""

# Test artifacts
echo -e "${BLUE}Cleaning test artifacts...${NC}"
rm -rf .pytest_cache 2>/dev/null || true
rm -rf .coverage 2>/dev/null || true
rm -rf htmlcov 2>/dev/null || true
rm -rf .mypy_cache 2>/dev/null || true
rm -rf .tox 2>/dev/null || true
rm -rf .benchmarks 2>/dev/null || true
rm -rf test-results 2>/dev/null || true
find . -name "*.coverage.*" -delete 2>/dev/null || true
echo -e "${GREEN}✓ Test artifacts cleaned${NC}"
echo ""

# Logs
echo -e "${BLUE}Cleaning log files...${NC}"
find . -path ./venv -prune -o -name "*.log" -delete 2>/dev/null || true
rm -rf logs/*.log 2>/dev/null || true
echo -e "${GREEN}✓ Log files cleaned${NC}"
echo ""

# Temporary files
echo -e "${BLUE}Cleaning temporary files...${NC}"
find . -path ./venv -prune -o -name "*.tmp" -delete 2>/dev/null || true
find . -path ./venv -prune -o -name "*.temp" -delete 2>/dev/null || true
find . -path ./venv -prune -o -name ".DS_Store" -delete 2>/dev/null || true
find . -path ./venv -prune -o -name "Thumbs.db" -delete 2>/dev/null || true
find . -path ./venv -prune -o -name "*~" -delete 2>/dev/null || true
echo -e "${GREEN}✓ Temporary files cleaned${NC}"
echo ""

# Python egg info
echo -e "${BLUE}Cleaning egg-info...${NC}"
find . -path ./venv -prune -o -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
find . -path ./venv -prune -o -type d -name "*.egg" -exec rm -rf {} + 2>/dev/null || true
echo -e "${GREEN}✓ Egg-info cleaned${NC}"
echo ""

# Build artifacts
echo -e "${BLUE}Cleaning build artifacts...${NC}"
rm -rf build 2>/dev/null || true
rm -rf dist 2>/dev/null || true
echo -e "${GREEN}✓ Build artifacts cleaned${NC}"
echo ""

# Empty directories
echo -e "${BLUE}Removing empty directories...${NC}"
find . -path ./venv -prune -o -path ./.git -prune -o -type d -empty -delete 2>/dev/null || true
echo -e "${GREEN}✓ Empty directories removed${NC}"
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Cleanup complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Show what remains
echo -e "${BLUE}Project structure:${NC}"
du -sh . 2>/dev/null | head -1
echo ""
echo -e "${BLUE}Main directories:${NC}"
du -sh backend templates tests docs 2>/dev/null || true
echo ""
