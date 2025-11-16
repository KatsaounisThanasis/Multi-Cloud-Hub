# =========================================
# Google Cloud DNS - Terraform Template
# =========================================
# This template creates Cloud DNS resources with:
# - Public and private DNS zones
# - DNS records (A, AAAA, CNAME, MX, TXT, etc.)
# - DNSSEC configuration
# - DNS policies
# - Private zone forwarding
# - Peering zones
# - Service Directory integration
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

variable "zone_name" {
  description = "Name of the DNS zone"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,62}$", var.zone_name))
    error_message = "Zone name must start with lowercase letter, be 1-63 characters, contain only lowercase letters, numbers, and hyphens"
  }
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "dns_name" {
  description = "DNS name of the zone (must end with a dot, e.g., 'example.com.')"
  type        = string

  validation {
    condition     = can(regex("\\.$", var.dns_name))
    error_message = "DNS name must end with a dot (.)"
  }
}

variable "description" {
  description = "Description of the DNS zone"
  type        = string
  default     = ""
}

variable "visibility" {
  description = "Zone visibility (public or private)"
  type        = string
  default     = "public"

  validation {
    condition     = contains(["public", "private"], var.visibility)
    error_message = "Visibility must be public or private"
  }
}

variable "private_visibility_config_networks" {
  description = "List of VPC network self-links for private zone visibility"
  type        = list(string)
  default     = []
}

variable "enable_dnssec" {
  description = "Enable DNSSEC for the zone"
  type        = bool
  default     = false
}

variable "dnssec_config_state" {
  description = "DNSSEC state (on, off, transfer)"
  type        = string
  default     = "on"

  validation {
    condition     = contains(["on", "off", "transfer"], var.dnssec_config_state)
    error_message = "DNSSEC state must be on, off, or transfer"
  }
}

variable "dnssec_config_non_existence" {
  description = "DNSSEC non-existence proof type (nsec or nsec3)"
  type        = string
  default     = "nsec3"

  validation {
    condition     = contains(["nsec", "nsec3"], var.dnssec_config_non_existence)
    error_message = "DNSSEC non-existence must be nsec or nsec3"
  }
}

variable "enable_logging" {
  description = "Enable query logging"
  type        = bool
  default     = false
}

variable "forwarding_config_target_name_servers" {
  description = "Target name servers for forwarding zone"
  type = list(object({
    ipv4_address    = string
    forwarding_path = optional(string, "default")
  }))
  default = []
}

variable "peering_config_target_network" {
  description = "Target network for peering zone"
  type        = string
  default     = null
}

variable "reverse_lookup" {
  description = "Enable reverse lookup zone"
  type        = bool
  default     = false
}

variable "service_directory_namespace" {
  description = "Service Directory namespace URL"
  type        = string
  default     = null
}

variable "records" {
  description = "List of DNS records to create"
  type = list(object({
    name    = string
    type    = string  # A, AAAA, CNAME, MX, TXT, NS, PTR, SOA, SPF, SRV, etc.
    ttl     = optional(number, 300)
    rrdatas = list(string)
  }))
  default = []
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
      template   = "cloud-dns"
    }
  )
}

# =========================================
# RESOURCES
# =========================================

# DNS Managed Zone
resource "google_dns_managed_zone" "zone" {
  name        = var.zone_name
  project     = var.project_id
  dns_name    = var.dns_name
  description = var.description != "" ? var.description : "Managed by Terraform"
  visibility  = var.visibility
  labels      = local.common_labels

  dynamic "private_visibility_config" {
    for_each = var.visibility == "private" && length(var.private_visibility_config_networks) > 0 ? [1] : []
    content {
      dynamic "networks" {
        for_each = var.private_visibility_config_networks
        content {
          network_url = networks.value
        }
      }
    }
  }

  dynamic "dnssec_config" {
    for_each = var.enable_dnssec && var.visibility == "public" ? [1] : []
    content {
      state         = var.dnssec_config_state
      non_existence = var.dnssec_config_non_existence

      default_key_specs {
        algorithm  = "rsasha256"
        key_length = 2048
        key_type   = "keySigning"
      }

      default_key_specs {
        algorithm  = "rsasha256"
        key_length = 1024
        key_type   = "zoneSigning"
      }
    }
  }

  dynamic "cloud_logging_config" {
    for_each = var.enable_logging ? [1] : []
    content {
      enable_logging = true
    }
  }

  dynamic "forwarding_config" {
    for_each = length(var.forwarding_config_target_name_servers) > 0 ? [1] : []
    content {
      dynamic "target_name_servers" {
        for_each = var.forwarding_config_target_name_servers
        content {
          ipv4_address    = target_name_servers.value.ipv4_address
          forwarding_path = target_name_servers.value.forwarding_path
        }
      }
    }
  }

  dynamic "peering_config" {
    for_each = var.peering_config_target_network != null ? [1] : []
    content {
      target_network {
        network_url = var.peering_config_target_network
      }
    }
  }

  reverse_lookup = var.reverse_lookup

  dynamic "service_directory_config" {
    for_each = var.service_directory_namespace != null ? [1] : []
    content {
      namespace {
        namespace_url = var.service_directory_namespace
      }
    }
  }
}

# DNS Records
resource "google_dns_record_set" "records" {
  for_each = { for record in var.records : "${record.name}-${record.type}" => record }

  name         = each.value.name
  type         = each.value.type
  ttl          = each.value.ttl
  managed_zone = google_dns_managed_zone.zone.name
  project      = var.project_id
  rrdatas      = each.value.rrdatas
}

# =========================================
# OUTPUTS
# =========================================

output "zone_id" {
  description = "ID of the DNS zone"
  value       = google_dns_managed_zone.zone.id
}

output "zone_name" {
  description = "Name of the DNS zone"
  value       = google_dns_managed_zone.zone.name
}

output "dns_name" {
  description = "DNS name of the zone"
  value       = google_dns_managed_zone.zone.dns_name
}

output "name_servers" {
  description = "List of name servers for the zone"
  value       = google_dns_managed_zone.zone.name_servers
}

output "zone_visibility" {
  description = "Visibility of the zone"
  value       = google_dns_managed_zone.zone.visibility
}

output "record_names" {
  description = "List of created DNS record names"
  value       = [for record in google_dns_record_set.records : record.name]
}

output "dnssec_enabled" {
  description = "Whether DNSSEC is enabled"
  value       = var.enable_dnssec && var.visibility == "public"
}
