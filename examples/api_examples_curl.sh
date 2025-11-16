#!/bin/bash
# cURL Examples for Multi-Cloud Infrastructure Management API
#
# Usage:
#   chmod +x api_examples_curl.sh
#   ./api_examples_curl.sh
#
# Or run individual commands directly

API_BASE="http://localhost:8000"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function print_section() {
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}\n"
}

function print_command() {
    echo -e "${YELLOW}Command:${NC} $1\n"
}

# ==================== Example 1: Health Check ====================

print_section "Example 1: API Health Check"
print_command "curl ${API_BASE}/health"

curl -s "${API_BASE}/health" | jq '.'

# ==================== Example 2: List Providers ====================

print_section "Example 2: List Cloud Providers"
print_command "curl ${API_BASE}/providers"

curl -s "${API_BASE}/providers" | jq '.data.providers[] | {id, name, template_count}'

# ==================== Example 3: List All Templates ====================

print_section "Example 3: List All Templates"
print_command "curl ${API_BASE}/templates"

curl -s "${API_BASE}/templates" | jq '.data | {count, templates: .templates[] | {name, cloud_provider, format}}'

# ==================== Example 4: List AWS Templates ====================

print_section "Example 4: List AWS Templates Only"
print_command "curl ${API_BASE}/templates?cloud=aws"

curl -s "${API_BASE}/templates?cloud=aws" | jq '.data.templates[] | {name, display_name}'

# ==================== Example 5: Get Template Details ====================

print_section "Example 5: Get Specific Template Details"
print_command "curl ${API_BASE}/templates/terraform-aws/storage-bucket"

curl -s "${API_BASE}/templates/terraform-aws/storage-bucket" | jq '.'

# ==================== Example 6: Get Template Content ====================

print_section "Example 6: Get Template Source Code"
print_command "curl ${API_BASE}/templates/terraform-aws/storage-bucket/content"

echo "First 20 lines of template:"
curl -s "${API_BASE}/templates/terraform-aws/storage-bucket/content" | jq -r '.content' | head -20

# ==================== Example 7: Deploy to AWS (Requires Credentials) ====================

print_section "Example 7: Deploy S3 Bucket to AWS"

cat << 'EOF' > /tmp/deploy_aws.json
{
  "template_name": "storage-bucket",
  "provider_type": "terraform-aws",
  "subscription_id": "123456789012",
  "resource_group": "my-app-resources",
  "location": "us-east-1",
  "parameters": {
    "bucket_name": "my-unique-test-bucket-xyz123",
    "enable_versioning": true,
    "tags": {
      "Environment": "Development",
      "Project": "API-Testing"
    }
  }
}
EOF

print_command "curl -X POST ${API_BASE}/deploy -H 'Content-Type: application/json' -d @deploy_aws.json"

echo "${YELLOW}Note: This requires AWS credentials configured${NC}"
echo "Payload:"
cat /tmp/deploy_aws.json | jq '.'

# Uncomment to actually deploy (requires credentials)
# curl -X POST "${API_BASE}/deploy" \
#   -H "Content-Type: application/json" \
#   -d @/tmp/deploy_aws.json | jq '.'

# ==================== Example 8: Deploy to GCP ====================

print_section "Example 8: Deploy Cloud Storage to GCP"

cat << 'EOF' > /tmp/deploy_gcp.json
{
  "template_name": "storage-bucket",
  "provider_type": "terraform-gcp",
  "subscription_id": "my-gcp-project-id",
  "resource_group": "my-gcp-resources",
  "location": "us-central1",
  "parameters": {
    "bucket_name": "my-gcp-bucket-unique-name",
    "storage_class": "STANDARD",
    "enable_versioning": true
  }
}
EOF

print_command "curl -X POST ${API_BASE}/deploy -d @deploy_gcp.json"

echo "${YELLOW}Note: This requires GCP credentials configured${NC}"
echo "Payload:"
cat /tmp/deploy_gcp.json | jq '.'

# ==================== Example 9: Deploy to Azure ====================

print_section "Example 9: Deploy Storage Account to Azure"

cat << 'EOF' > /tmp/deploy_azure.json
{
  "template_name": "Storage Account",
  "provider_type": "azure",
  "subscription_id": "your-azure-subscription-id",
  "resource_group": "my-azure-rg",
  "location": "eastus",
  "parameters": {
    "storageAccountName": "myuniquestorage123",
    "skuName": "Standard_LRS"
  }
}
EOF

print_command "curl -X POST ${API_BASE}/deploy -d @deploy_azure.json"

echo "${YELLOW}Note: This requires Azure credentials (az login)${NC}"
echo "Payload:"
cat /tmp/deploy_azure.json | jq '.'

# ==================== Example 10: List Resource Groups ====================

print_section "Example 10: List Resource Groups (Azure)"

SUBSCRIPTION_ID="your-subscription-id"

print_command "curl '${API_BASE}/resource-groups?provider_type=azure&subscription_id=${SUBSCRIPTION_ID}'"

echo "${YELLOW}Note: Requires valid Azure subscription ID${NC}"

# curl -s "${API_BASE}/resource-groups?provider_type=azure&subscription_id=${SUBSCRIPTION_ID}" | jq '.'

# ==================== Example 11: Create Resource Group ====================

print_section "Example 11: Create Resource Group"

cat << 'EOF' > /tmp/create_rg.json
{
  "name": "test-resource-group",
  "location": "eastus",
  "subscription_id": "your-subscription-id",
  "provider_type": "azure",
  "tags": {
    "Environment": "Test",
    "CreatedBy": "API"
  }
}
EOF

print_command "curl -X POST ${API_BASE}/resource-groups -d @create_rg.json"

echo "Payload:"
cat /tmp/create_rg.json | jq '.'

# ==================== Example 12: Get Deployment Status ====================

print_section "Example 12: Check Deployment Status"

DEPLOYMENT_ID="deployment-20250106-123456"
PROVIDER="terraform-aws"
SUBSCRIPTION="123456789012"
RG="my-resources"

print_command "curl '${API_BASE}/deployments/${DEPLOYMENT_ID}/status?provider_type=${PROVIDER}&subscription_id=${SUBSCRIPTION}&resource_group=${RG}'"

echo "${YELLOW}Note: Use actual deployment ID from deploy response${NC}"

# ==================== Example 13: List Resources in Group ====================

print_section "Example 13: List Resources in Resource Group"

RG_NAME="my-app-resources"
PROVIDER="azure"
SUBSCRIPTION="your-subscription-id"

print_command "curl '${API_BASE}/resource-groups/${RG_NAME}/resources?provider_type=${PROVIDER}&subscription_id=${SUBSCRIPTION}'"

# ==================== Example 14: Delete Resource Group ====================

print_section "Example 14: Delete Resource Group"

RG_NAME="test-resource-group"
PROVIDER="azure"
SUBSCRIPTION="your-subscription-id"

print_command "curl -X DELETE '${API_BASE}/resource-groups/${RG_NAME}?provider_type=${PROVIDER}&subscription_id=${SUBSCRIPTION}'"

echo "${YELLOW}Warning: This is a destructive operation!${NC}"

# ==================== Example 15: Multi-Cloud Deployment Comparison ====================

print_section "Example 15: Multi-Cloud Template Comparison"

echo "Comparing storage solutions across clouds:"
echo ""

for CLOUD in azure aws gcp; do
    echo -e "${GREEN}${CLOUD^^}:${NC}"
    curl -s "${API_BASE}/templates?cloud=${CLOUD}" | jq -r '.data.templates[] | select(.name | contains("storage")) | "  - \(.display_name) (\(.format))"'
    echo ""
done

# ==================== Summary ====================

print_section "Examples Complete!"

echo "All examples have been demonstrated."
echo ""
echo "To actually deploy resources:"
echo "  1. Configure cloud credentials (az login, aws configure, gcloud auth)"
echo "  2. Update subscription/account IDs in examples"
echo "  3. Uncomment the curl commands above"
echo ""
echo "API Documentation: ${API_BASE}/docs"
echo "Alternative Docs: ${API_BASE}/redoc"

# Cleanup
rm -f /tmp/deploy_*.json /tmp/create_rg.json

print_section "Done!"
