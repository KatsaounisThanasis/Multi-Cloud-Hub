# Terraform Implementation Guide - Multi-Cloud Manager v3.0

## 📚 Research Summary (2025 Best Practices)

### Key Findings from Research

#### **1. Terraform Azure (AzureRM) Provider - 2025 Best Practices**

##### Version & Authentication
- **Always pin provider versions** to avoid breaking changes
- **Use Azure CLI for local development**: `az login`
- **For CI/CD**: Use Service Principal or Managed Identity
- **TLS 1.2+ Required**: Azure Services mandate TLS 1.2+ as of August 2025

##### Module Structure
Every Terraform module should contain:
- `variables.tf` - Input parameters with descriptions, types, defaults
- `main.tf` - Main resource definitions
- `outputs.tf` - Output values for module consumers
- `README.md` - Documentation with usage examples
- `versions.tf` - Provider version constraints

##### Variable Best Practices
```hcl
variable "resource_group_name" {
  description = "Name of the Azure Resource Group"
  type        = string

  validation {
    condition     = can(regex("^rg-", var.resource_group_name))
    error_message = "Resource group name must start with 'rg-' prefix"
  }
}

variable "environment" {
  description = "Environment name (dev, test, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "Environment must be dev, test, or prod"
  }
}
```

#### **2. Critical Azure Resources for 2025**

##### Compute
- **azurerm_linux_virtual_machine** - Replaces legacy azurerm_virtual_machine
- **azurerm_windows_virtual_machine** - Windows-specific VM resource
- **azurerm_kubernetes_cluster** - AKS (Azure Kubernetes Service)
  - ⚠️ **Note**: Azure Linux 2.0 support ends November 30, 2025
  - Node images removed March 31, 2026
- **azurerm_linux_virtual_machine_scale_set** - VM Scale Sets
- **azurerm_function_app** - Azure Functions (serverless)
- **azurerm_linux_web_app** - App Service Web Apps

##### Networking
- **azurerm_virtual_network** - Virtual networks with subnets
- **azurerm_subnet** - Subnets within VNet
- **azurerm_network_security_group** - NSG with security rules
- **azurerm_network_interface** - NIC for VMs
- **azurerm_public_ip** - Public IP addresses
- **azurerm_lb** - Load balancers

##### Storage
- **azurerm_storage_account** - Storage accounts
- **azurerm_storage_container** - Blob containers
- **azurerm_storage_blob** - Individual blobs
- **azurerm_storage_share** - File shares
- **azurerm_storage_queue** - Queue storage

##### Databases
- **azurerm_mssql_server** - Azure SQL Server
- **azurerm_mssql_database** - SQL Database
- **azurerm_mssql_firewall_rule** - SQL firewall rules
- **azurerm_cosmosdb_account** - Cosmos DB account
- **azurerm_cosmosdb_sql_database** - Cosmos DB SQL API database
- **azurerm_cosmosdb_sql_container** - Cosmos DB containers

##### Security & Monitoring
- **azurerm_key_vault** - Key Vault for secrets
- **azurerm_log_analytics_workspace** - Log Analytics
- **azurerm_monitor_diagnostic_setting** - Diagnostic settings

#### **3. GCP (Google Cloud) Provider - 2025 Best Practices**

##### Authentication
- **Local development**: `gcloud auth application-default login`
- **DO NOT download service account keys** - harder to manage and secure
- **Use Service Accounts with Least Privilege** - avoid roles/owner

##### Key GCP Resources
- **google_compute_instance** - Compute Engine VMs
- **google_storage_bucket** - Cloud Storage buckets
- **google_cloud_function** - Cloud Functions (Gen 2)
- **google_sql_database_instance** - Cloud SQL
- **google_container_cluster** - GKE (Google Kubernetes Engine)
- **google_compute_network** - VPC networks
- **google_compute_firewall** - Firewall rules

#### **4. Azure Resource Naming Conventions**

##### Official Azure CAF (Cloud Adoption Framework) Prefixes
```
rg-       Resource Group
vm-       Virtual Machine
vnet-     Virtual Network
snet-     Subnet
nsg-      Network Security Group
nic-      Network Interface
pip-      Public IP
st-       Storage Account (must be lowercase, no hyphens)
kv-       Key Vault
sql-      SQL Server
cosmos-   Cosmos DB
aks-      AKS Cluster
func-     Function App
app-      App Service
```

##### Validation Patterns
```hcl
# Storage Account: 3-24 chars, lowercase, numbers only
validation {
  condition     = can(regex("^[a-z0-9]{3,24}$", var.storage_account_name))
  error_message = "Storage account name must be 3-24 lowercase letters/numbers"
}

# Resource Group: alphanumeric, underscore, parentheses, hyphen, period
validation {
  condition     = can(regex("^[-\\w\\._\\(\\)]+$", var.resource_group_name))
  error_message = "Invalid resource group name"
}
```

---

## 🎯 Implementation Plan

### Phase 1: Core Infrastructure Templates (Priority: CRITICAL)

#### 1.1 Virtual Machine Template
**File**: `templates/terraform/azure/virtual-machine.tf`

**Required Variables:**
```hcl
variable "vm_name" {
  description = "Name of the virtual machine"
  type        = string
  validation {
    condition     = can(regex("^vm-[a-z0-9-]{1,60}$", var.vm_name))
    error_message = "VM name must start with 'vm-' and be 1-64 characters"
  }
}

variable "location" {
  description = "Azure region for deployment"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "vm_size" {
  description = "Size of the virtual machine"
  type        = string
  default     = "Standard_B2s"
}

variable "admin_username" {
  description = "Admin username for the VM"
  type        = string
  default     = "azureuser"
}

variable "admin_password" {
  description = "Admin password for the VM (Windows) or SSH key (Linux)"
  type        = string
  sensitive   = true
}

variable "os_type" {
  description = "Operating system type"
  type        = string
  default     = "Linux"
  validation {
    condition     = contains(["Linux", "Windows"], var.os_type)
    error_message = "OS type must be Linux or Windows"
  }
}

variable "image_publisher" {
  description = "OS image publisher"
  type        = string
  default     = "Canonical"
}

variable "image_offer" {
  description = "OS image offer"
  type        = string
  default     = "0001-com-ubuntu-server-jammy"
}

variable "image_sku" {
  description = "OS image SKU"
  type        = string
  default     = "22_04-lts-gen2"
}

variable "image_version" {
  description = "OS image version"
  type        = string
  default     = "latest"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
```

**Resources to Create:**
1. Virtual Network (10.0.0.0/16)
2. Subnet (10.0.0.0/24)
3. Network Security Group with default rules
4. Public IP (Dynamic)
5. Network Interface
6. Linux or Windows Virtual Machine

#### 1.2 Virtual Network Template
**File**: `templates/terraform/azure/virtual-network.tf`

**Variables:**
- vnet_name
- location
- resource_group_name
- address_space (default: ["10.0.0.0/16"])
- subnets (list of objects with name and address_prefix)
- dns_servers (optional)
- tags

#### 1.3 Network Security Group Template
**File**: `templates/terraform/azure/network-security-group.tf`

**Variables:**
- nsg_name
- location
- resource_group_name
- security_rules (list of rule objects)
- tags

### Phase 2: Application Services (Priority: HIGH)

#### 2.1 Storage Account Template
**File**: `templates/terraform/azure/storage-account.tf`

**Variables:**
- storage_account_name (3-24 chars, lowercase, numbers)
- location
- resource_group_name
- account_tier (Standard/Premium)
- account_replication_type (LRS/GRS/RAGRS/ZRS)
- enable_https_traffic_only (default: true)
- min_tls_version (default: "TLS1_2")
- blob_soft_delete_retention_days
- container_soft_delete_retention_days
- tags

#### 2.2 Function App Template
**File**: `templates/terraform/azure/function-app.tf`

**Variables:**
- function_app_name
- location
- resource_group_name
- storage_account_name (for function app storage)
- app_service_plan_id
- runtime_stack (python/node/dotnet/java)
- runtime_version
- tags

#### 2.3 Web App Template
**File**: `templates/terraform/azure/web-app.tf`

**Variables:**
- web_app_name
- location
- resource_group_name
- app_service_plan_id
- runtime_stack
- runtime_version
- always_on (default: true)
- tags

### Phase 3: Database Services (Priority: HIGH)

#### 3.1 SQL Server & Database Template
**File**: `templates/terraform/azure/sql-database.tf`

**Variables:**
- sql_server_name
- location
- resource_group_name
- administrator_login
- administrator_login_password (sensitive)
- sql_database_name
- sku_name (e.g., "S0", "P1")
- max_size_gb
- tags

#### 3.2 Cosmos DB Template
**File**: `templates/terraform/azure/cosmos-db.tf`

**Variables:**
- cosmos_account_name
- location
- resource_group_name
- consistency_level (default: "Session")
- api_type (SQL/MongoDB/Cassandra/Gremlin/Table)
- enable_free_tier (default: false)
- enable_automatic_failover (default: false)
- database_name
- tags

### Phase 4: Container & Kubernetes (Priority: HIGH)

#### 4.1 AKS Cluster Template
**File**: `templates/terraform/azure/aks-cluster.tf`

**Variables:**
- cluster_name
- location
- resource_group_name
- dns_prefix
- kubernetes_version
- default_node_pool_name
- default_node_pool_vm_size
- default_node_pool_node_count
- enable_auto_scaling
- min_count / max_count (if auto-scaling enabled)
- network_plugin (azure/kubenet)
- tags

#### 4.2 VM Scale Set Template
**File**: `templates/terraform/azure/vm-scale-set.tf`

**Variables:**
- vmss_name
- location
- resource_group_name
- sku
- instances
- admin_username
- admin_password
- os_type
- image_reference
- upgrade_mode (Automatic/Manual/Rolling)
- tags

### Phase 5: Security & Monitoring (Priority: MEDIUM)

#### 5.1 Key Vault Template
**File**: `templates/terraform/azure/key-vault.tf`

**Variables:**
- key_vault_name
- location
- resource_group_name
- tenant_id
- sku_name (standard/premium)
- enabled_for_disk_encryption
- enabled_for_deployment
- enabled_for_template_deployment
- soft_delete_retention_days (default: 90)
- purge_protection_enabled
- access_policies (list of objects)
- tags

#### 5.2 Log Analytics Workspace Template
**File**: `templates/terraform/azure/log-analytics.tf`

**Variables:**
- workspace_name
- location
- resource_group_name
- sku (PerGB2018/Free/Standalone/PerNode/Premium)
- retention_in_days (default: 30)
- tags

#### 5.3 Load Balancer Template
**File**: `templates/terraform/azure/load-balancer.tf`

**Variables:**
- lb_name
- location
- resource_group_name
- sku (Basic/Standard)
- frontend_ip_configuration
- backend_pool_name
- health_probe_config
- lb_rules
- tags

#### 5.4 Public IP Template
**File**: `templates/terraform/azure/public-ip.tf`

**Variables:**
- public_ip_name
- location
- resource_group_name
- allocation_method (Dynamic/Static)
- sku (Basic/Standard)
- ip_version (IPv4/IPv6)
- domain_name_label (optional)
- tags

---

## 🌐 GCP Templates (Phase 6)

### 6.1 Compute Instance (Existing - Enhance)
**File**: `templates/terraform/gcp/compute-instance.tf`

### 6.2 Cloud Storage Bucket (Existing - Enhance)
**File**: `templates/terraform/gcp/storage-bucket.tf`

### 6.3 Cloud Function (Existing - Enhance)
**File**: `templates/terraform/gcp/cloud-function.tf`

### 6.4 Cloud SQL (NEW)
**File**: `templates/terraform/gcp/cloud-sql.tf`

**Variables:**
- instance_name
- database_version (POSTGRES_14/MYSQL_8_0)
- region
- tier (db-f1-micro/db-n1-standard-1)
- database_name
- user_name
- user_password

### 6.5 GKE Cluster (NEW)
**File**: `templates/terraform/gcp/gke-cluster.tf`

**Variables:**
- cluster_name
- location
- initial_node_count
- node_config (machine_type, disk_size_gb)
- network
- subnetwork

### 6.6 VPC Network (NEW)
**File**: `templates/terraform/gcp/vpc-network.tf`

**Variables:**
- network_name
- auto_create_subnetworks
- routing_mode (REGIONAL/GLOBAL)
- subnets (list of objects)

---

## 📋 Template Development Checklist

For each template, ensure:

### ✅ Required Files
- [ ] `<service-name>.tf` - Main template file
- [ ] Comprehensive variable definitions with:
  - [ ] Clear descriptions
  - [ ] Type constraints
  - [ ] Default values where appropriate
  - [ ] Validation rules
- [ ] Output values (IDs, names, endpoints)
- [ ] Comments explaining resource purposes

### ✅ Code Quality
- [ ] Follow Azure/GCP naming conventions
- [ ] Use latest stable API versions
- [ ] Include all common parameters (location, tags, etc.)
- [ ] Implement proper dependencies between resources
- [ ] Use data sources where appropriate
- [ ] Add lifecycle blocks if needed

### ✅ Security
- [ ] Mark sensitive variables as `sensitive = true`
- [ ] Use secure defaults (HTTPS only, TLS 1.2+, etc.)
- [ ] Implement proper access controls
- [ ] Follow least privilege principle

### ✅ Testing
- [ ] Test with minimal required variables
- [ ] Test with all optional variables
- [ ] Validate outputs are correct
- [ ] Verify resource creation in Azure/GCP portal
- [ ] Test cleanup (terraform destroy)

---

## 🔄 Dynamic Form Generation Strategy

### Backend API Enhancement

1. **Endpoint**: `/templates/{provider_type}/{template_name}/parameters`
   - Already exists! ✅
   - Returns parsed variables from template

2. **Endpoint**: `/templates/catalog` (NEW - Optional)
   - Returns organized service catalog
   - Groups templates by category
   - Includes service descriptions

### Frontend Implementation

1. **Service Selection**
   - Provider: Azure / GCP
   - Category: Compute / Storage / Database / Networking / Security
   - Service: Dropdown of available templates

2. **Tool Selection** (Azure only)
   - Bicep (existing templates)
   - Terraform (new templates)

3. **Dynamic Form Generation**
   - Fetch template parameters from API
   - Generate form fields based on variable types:
     - `string` → Text input
     - `number` → Number input
     - `bool` → Checkbox
     - `enum` (via validation) → Dropdown
     - `list` → Multi-select or repeated fields
     - `map` → Key-value pairs
   - Apply validation rules from template
   - Show/hide fields based on conditionals

4. **Parameter Submission**
   - Collect all form values
   - POST to `/deploy` endpoint
   - Parameters dynamically filled into template

---

## 🎯 Success Metrics

### Coverage Goals
- [x] 15 Azure services (100% from Bicep inventory)
- [ ] 14 Azure Terraform templates created
- [ ] 6+ GCP services (double current coverage)
- [ ] Dynamic frontend for all templates

### Quality Goals
- [ ] All templates follow 2025 best practices
- [ ] Complete variable documentation
- [ ] Validation rules on critical inputs
- [ ] Tested deployments for each template
- [ ] User can deploy without technical knowledge

---

## 📚 References

- [Terraform AzureRM Provider Registry](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Microsoft Learn - Terraform on Azure](https://learn.microsoft.com/en-us/azure/developer/terraform/)
- [Terraform GCP Provider Registry](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Azure Naming Conventions CAF](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-naming)
- [Terraform Best Practices 2025](https://www.terraform-best-practices.com/)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-15
**Status**: Research Complete - Ready for Implementation Phase
