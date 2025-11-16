#!/bin/bash
# Multi-Cloud API - Cloud Credentials Setup Helper
# This script helps you set up credentials for Azure, AWS, and GCP

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================"
echo "Multi-Cloud API - Credentials Setup"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if .env exists
if [ ! -f ".env" ]; then
    print_info "Creating .env file from .env.example..."
    cp .env.example .env
    print_status ".env file created"
else
    print_info ".env file already exists"
fi

echo ""
echo "======================================"
echo "1. Azure Credentials Setup"
echo "======================================"
echo ""

print_info "Azure requires a Service Principal with Contributor role"
echo ""
echo "Choose your Azure authentication method:"
echo "  a) Create new Service Principal (recommended)"
echo "  b) Use Azure CLI (az login)"
echo "  c) Skip Azure setup"
echo ""
read -p "Choose option (a/b/c): " azure_choice

case "$azure_choice" in
    a)
        echo ""
        print_info "Creating Azure Service Principal..."
        read -p "Enter your Azure Subscription ID: " AZURE_SUBSCRIPTION_ID

        echo ""
        print_info "Running: az ad sp create-for-rbac..."
        SP_OUTPUT=$(az ad sp create-for-rbac \
            --name "multicloud-api-sp-$(date +%s)" \
            --role contributor \
            --scopes "/subscriptions/$AZURE_SUBSCRIPTION_ID" \
            --sdk-auth 2>/dev/null)

        if [ $? -eq 0 ]; then
            print_status "Service Principal created successfully!"
            echo ""
            echo "$SP_OUTPUT"
            echo ""

            # Parse JSON and update .env
            CLIENT_ID=$(echo "$SP_OUTPUT" | grep -o '"clientId": *"[^"]*"' | sed 's/"clientId": *"\([^"]*\)"/\1/')
            CLIENT_SECRET=$(echo "$SP_OUTPUT" | grep -o '"clientSecret": *"[^"]*"' | sed 's/"clientSecret": *"\([^"]*\)"/\1/')
            TENANT_ID=$(echo "$SP_OUTPUT" | grep -o '"tenantId": *"[^"]*"' | sed 's/"tenantId": *"\([^"]*\)"/\1/')

            # Update .env file
            sed -i "s|AZURE_SUBSCRIPTION_ID=.*|AZURE_SUBSCRIPTION_ID=$AZURE_SUBSCRIPTION_ID|" .env
            sed -i "s|AZURE_TENANT_ID=.*|AZURE_TENANT_ID=$TENANT_ID|" .env
            sed -i "s|AZURE_CLIENT_ID=.*|AZURE_CLIENT_ID=$CLIENT_ID|" .env
            sed -i "s|AZURE_CLIENT_SECRET=.*|AZURE_CLIENT_SECRET=$CLIENT_SECRET|" .env

            print_status "Azure credentials added to .env file"
        else
            print_error "Failed to create Service Principal"
            print_warning "Please run 'az login' first or check your permissions"
        fi
        ;;
    b)
        print_info "Using Azure CLI authentication"
        print_warning "Make sure you've run 'az login' before starting the containers"
        ;;
    c)
        print_warning "Skipping Azure setup"
        ;;
esac

echo ""
echo "======================================"
echo "2. GCP Credentials Setup"
echo "======================================"
echo ""

print_info "GCP requires a Service Account key file"
echo ""
echo "Choose your GCP authentication method:"
echo "  a) Create new Service Account"
echo "  b) I already have a key file"
echo "  c) Skip GCP setup"
echo ""
read -p "Choose option (a/b/c): " gcp_choice

case "$gcp_choice" in
    a)
        echo ""
        read -p "Enter your GCP Project ID: " GCP_PROJECT_ID

        print_info "Creating GCP Service Account..."

        # Create service account
        gcloud iam service-accounts create multicloud-api \
            --description="Service account for Multi-Cloud API" \
            --display-name="Multi-Cloud API" \
            --project="$GCP_PROJECT_ID" 2>/dev/null

        # Grant editor role
        gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
            --member="serviceAccount:multicloud-api@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
            --role="roles/editor" >/dev/null 2>&1

        # Create and download key
        mkdir -p credentials
        gcloud iam service-accounts keys create credentials/gcp-service-account.json \
            --iam-account="multicloud-api@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
            --project="$GCP_PROJECT_ID"

        if [ $? -eq 0 ]; then
            chmod 600 credentials/gcp-service-account.json
            print_status "Service Account created and key saved to credentials/gcp-service-account.json"

            # Update .env
            sed -i "s|GOOGLE_PROJECT_ID=.*|GOOGLE_PROJECT_ID=$GCP_PROJECT_ID|" .env
            print_status "GCP credentials added to .env file"
        else
            print_error "Failed to create Service Account"
        fi
        ;;
    b)
        echo ""
        print_info "Looking for existing GCP key file..."

        if [ -f "credentials/gcp-service-account.json" ]; then
            print_status "Found: credentials/gcp-service-account.json"
            read -p "Enter your GCP Project ID: " GCP_PROJECT_ID
            sed -i "s|GOOGLE_PROJECT_ID=.*|GOOGLE_PROJECT_ID=$GCP_PROJECT_ID|" .env
            print_status "GCP Project ID added to .env file"
        else
            print_warning "Key file not found at credentials/gcp-service-account.json"
            echo "Please copy your key file to: $PROJECT_ROOT/credentials/gcp-service-account.json"
        fi
        ;;
    c)
        print_warning "Skipping GCP setup"
        ;;
esac

echo ""
echo "======================================"
echo "3. AWS Credentials Setup"
echo "======================================"
echo ""

print_info "AWS requires Access Key ID and Secret Access Key"
echo ""
echo "Choose your AWS authentication method:"
echo "  a) Enter AWS credentials manually"
echo "  b) Use AWS CLI credentials (~/.aws/credentials)"
echo "  c) Skip AWS setup"
echo ""
read -p "Choose option (a/b/c): " aws_choice

case "$aws_choice" in
    a)
        echo ""
        read -p "Enter your AWS Access Key ID: " AWS_ACCESS_KEY_ID
        read -sp "Enter your AWS Secret Access Key: " AWS_SECRET_ACCESS_KEY
        echo ""
        read -p "Enter your AWS Default Region [us-east-1]: " AWS_REGION
        AWS_REGION=${AWS_REGION:-us-east-1}

        # Update .env
        sed -i "s|AWS_ACCESS_KEY_ID=.*|AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID|" .env
        sed -i "s|AWS_SECRET_ACCESS_KEY=.*|AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY|" .env
        sed -i "s|AWS_DEFAULT_REGION=.*|AWS_DEFAULT_REGION=$AWS_REGION|" .env

        print_status "AWS credentials added to .env file"
        ;;
    b)
        print_info "Using AWS CLI credentials"
        print_warning "Make sure ~/.aws/credentials exists and is mounted in docker-compose.yml"
        ;;
    c)
        print_warning "Skipping AWS setup"
        ;;
esac

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
print_status "Credentials configuration finished"
echo ""
print_info "Next steps:"
echo "  1. Review your .env file: nano .env"
echo "  2. Start the services: docker compose up -d"
echo "  3. Check logs: docker compose logs -f"
echo ""
print_info "API will be available at: http://localhost:8000"
print_info "API documentation: http://localhost:8000/docs"
echo ""
