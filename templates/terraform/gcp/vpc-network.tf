# =========================================
# Google Cloud VPC Network - Terraform Template
# =========================================
# This template creates a VPC network with:
# - Custom subnets with secondary IP ranges
# - Cloud Router and Cloud NAT
# - Firewall rules
# - Private Google Access
# - VPC peering (optional)
# - Flow logs
#
# Version: 1.0
# Last Updated: 2025-11-15
# =========================================

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# =========================================
# VARIABLES
# =========================================

variable "network_name" {
  description = "Name of the VPC network"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,62}$", var.network_name))
    error_message = "Network name must start with lowercase letter, be 1-63 characters, contain only lowercase letters, numbers, and hyphens"
  }
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "auto_create_subnetworks" {
  description = "Create subnets automatically in each region (not recommended for production)"
  type        = bool
  default     = false
}

variable "routing_mode" {
  description = "Network routing mode (REGIONAL or GLOBAL)"
  type        = string
  default     = "REGIONAL"

  validation {
    condition     = contains(["REGIONAL", "GLOBAL"], var.routing_mode)
    error_message = "Routing mode must be REGIONAL or GLOBAL"
  }
}

variable "mtu" {
  description = "Maximum Transmission Unit in bytes (1460-1500)"
  type        = number
  default     = 1460

  validation {
    condition     = var.mtu >= 1460 && var.mtu <= 1500
    error_message = "MTU must be between 1460 and 1500"
  }
}

variable "delete_default_routes_on_create" {
  description = "Delete default routes on network creation"
  type        = bool
  default     = false
}

variable "subnets" {
  description = "List of subnets to create"
  type = list(object({
    name                     = string
    region                   = string
    ip_cidr_range            = string
    private_ip_google_access = optional(bool, true)
    enable_flow_logs         = optional(bool, false)
    flow_logs_interval       = optional(string, "INTERVAL_5_SEC")
    flow_logs_sampling       = optional(number, 0.5)
    secondary_ip_ranges = optional(list(object({
      range_name    = string
      ip_cidr_range = string
    })), [])
  }))
  default = []
}

variable "enable_cloud_nat" {
  description = "Enable Cloud NAT for outbound internet access"
  type        = bool
  default     = false
}

variable "cloud_nat_regions" {
  description = "List of regions to create Cloud NAT (empty = all regions with subnets)"
  type        = list(string)
  default     = []
}

variable "nat_ip_allocate_option" {
  description = "NAT IP allocation option (AUTO_ONLY or MANUAL_ONLY)"
  type        = string
  default     = "AUTO_ONLY"

  validation {
    condition     = contains(["AUTO_ONLY", "MANUAL_ONLY"], var.nat_ip_allocate_option)
    error_message = "NAT IP allocation option must be AUTO_ONLY or MANUAL_ONLY"
  }
}

variable "nat_min_ports_per_vm" {
  description = "Minimum number of ports allocated to a VM for NAT"
  type        = number
  default     = 64

  validation {
    condition     = var.nat_min_ports_per_vm >= 64 && var.nat_min_ports_per_vm <= 65536
    error_message = "Minimum ports per VM must be between 64 and 65536"
  }
}

variable "nat_log_config_enabled" {
  description = "Enable Cloud NAT logging"
  type        = bool
  default     = false
}

variable "nat_log_config_filter" {
  description = "NAT log filter (ERRORS_ONLY, TRANSLATIONS_ONLY, ALL)"
  type        = string
  default     = "ERRORS_ONLY"

  validation {
    condition     = contains(["ERRORS_ONLY", "TRANSLATIONS_ONLY", "ALL"], var.nat_log_config_filter)
    error_message = "NAT log filter must be ERRORS_ONLY, TRANSLATIONS_ONLY, or ALL"
  }
}

variable "firewall_rules" {
  description = "List of firewall rules to create"
  type = list(object({
    name          = string
    description   = optional(string, "")
    priority      = optional(number, 1000)
    direction     = optional(string, "INGRESS")
    source_ranges = optional(list(string), [])
    target_tags   = optional(list(string), [])
    allow = optional(list(object({
      protocol = string
      ports    = optional(list(string), [])
    })), [])
    deny = optional(list(object({
      protocol = string
      ports    = optional(list(string), [])
    })), [])
  }))
  default = []
}

variable "enable_vpc_peering" {
  description = "Enable VPC peering with another network"
  type        = bool
  default     = false
}

variable "peer_network" {
  description = "Self link of peer network (required if enable_vpc_peering is true)"
  type        = string
  default     = null
}

variable "peer_export_custom_routes" {
  description = "Export custom routes to peer network"
  type        = bool
  default     = false
}

variable "peer_import_custom_routes" {
  description = "Import custom routes from peer network"
  type        = bool
  default     = false
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}

# =========================================
# LOCAL VARIABLES
# =========================================

locals {
  # Common labels
  common_labels = merge(
    var.labels,
    {
      managed_by = "terraform"
      template   = "vpc-network"
    }
  )

  # Extract unique regions from subnets for Cloud NAT
  subnet_regions = distinct([for subnet in var.subnets : subnet.region])

  # Regions to create NAT (use specified regions or all subnet regions)
  nat_regions = length(var.cloud_nat_regions) > 0 ? var.cloud_nat_regions : local.subnet_regions
}

# =========================================
# RESOURCES
# =========================================

# VPC Network
resource "google_compute_network" "main" {
  name                            = var.network_name
  project                         = var.project_id
  auto_create_subnetworks         = var.auto_create_subnetworks
  routing_mode                    = var.routing_mode
  mtu                             = var.mtu
  delete_default_routes_on_create = var.delete_default_routes_on_create
}

# Subnets
resource "google_compute_subnetwork" "subnets" {
  for_each = { for subnet in var.subnets : subnet.name => subnet }

  name                     = each.value.name
  project                  = var.project_id
  region                   = each.value.region
  network                  = google_compute_network.main.id
  ip_cidr_range            = each.value.ip_cidr_range
  private_ip_google_access = each.value.private_ip_google_access

  dynamic "secondary_ip_range" {
    for_each = each.value.secondary_ip_ranges
    content {
      range_name    = secondary_ip_range.value.range_name
      ip_cidr_range = secondary_ip_range.value.ip_cidr_range
    }
  }

  dynamic "log_config" {
    for_each = each.value.enable_flow_logs ? [1] : []
    content {
      aggregation_interval = each.value.flow_logs_interval
      flow_sampling        = each.value.flow_logs_sampling
      metadata             = "INCLUDE_ALL_METADATA"
    }
  }
}

# Cloud Router (required for Cloud NAT)
resource "google_compute_router" "router" {
  for_each = var.enable_cloud_nat ? toset(local.nat_regions) : []

  name    = "${var.network_name}-router-${each.value}"
  project = var.project_id
  region  = each.value
  network = google_compute_network.main.id

  bgp {
    asn = 64514
  }
}

# Cloud NAT
resource "google_compute_router_nat" "nat" {
  for_each = var.enable_cloud_nat ? toset(local.nat_regions) : []

  name                               = "${var.network_name}-nat-${each.value}"
  project                            = var.project_id
  region                             = each.value
  router                             = google_compute_router.router[each.value].name
  nat_ip_allocate_option             = var.nat_ip_allocate_option
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  min_ports_per_vm                   = var.nat_min_ports_per_vm

  dynamic "log_config" {
    for_each = var.nat_log_config_enabled ? [1] : []
    content {
      enable = true
      filter = var.nat_log_config_filter
    }
  }
}

# Firewall Rules
resource "google_compute_firewall" "rules" {
  for_each = { for rule in var.firewall_rules : rule.name => rule }

  name        = each.value.name
  project     = var.project_id
  network     = google_compute_network.main.id
  description = each.value.description
  priority    = each.value.priority
  direction   = each.value.direction

  source_ranges = each.value.direction == "INGRESS" ? each.value.source_ranges : null
  target_tags   = each.value.target_tags

  dynamic "allow" {
    for_each = each.value.allow
    content {
      protocol = allow.value.protocol
      ports    = allow.value.ports
    }
  }

  dynamic "deny" {
    for_each = each.value.deny
    content {
      protocol = deny.value.protocol
      ports    = deny.value.ports
    }
  }
}

# VPC Peering
resource "google_compute_network_peering" "peering" {
  count = var.enable_vpc_peering && var.peer_network != null ? 1 : 0

  name                 = "${var.network_name}-peering"
  network              = google_compute_network.main.id
  peer_network         = var.peer_network
  export_custom_routes = var.peer_export_custom_routes
  import_custom_routes = var.peer_import_custom_routes
}

# =========================================
# OUTPUTS
# =========================================

output "network_id" {
  description = "ID of the VPC network"
  value       = google_compute_network.main.id
}

output "network_name" {
  description = "Name of the VPC network"
  value       = google_compute_network.main.name
}

output "network_self_link" {
  description = "Self link of the VPC network"
  value       = google_compute_network.main.self_link
}

output "subnet_ids" {
  description = "Map of subnet names to IDs"
  value       = { for subnet in google_compute_subnetwork.subnets : subnet.name => subnet.id }
}

output "subnet_self_links" {
  description = "Map of subnet names to self links"
  value       = { for subnet in google_compute_subnetwork.subnets : subnet.name => subnet.self_link }
}

output "subnet_ip_cidr_ranges" {
  description = "Map of subnet names to IP CIDR ranges"
  value       = { for subnet in google_compute_subnetwork.subnets : subnet.name => subnet.ip_cidr_range }
}

output "cloud_router_names" {
  description = "List of Cloud Router names"
  value       = var.enable_cloud_nat ? [for router in google_compute_router.router : router.name] : []
}

output "cloud_nat_names" {
  description = "List of Cloud NAT names"
  value       = var.enable_cloud_nat ? [for nat in google_compute_router_nat.nat : nat.name] : []
}

output "firewall_rule_names" {
  description = "List of firewall rule names"
  value       = [for rule in google_compute_firewall.rules : rule.name]
}
