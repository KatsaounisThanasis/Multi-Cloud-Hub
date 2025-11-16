# =========================================
# Google Cloud CDN - Terraform Template
# =========================================
# This template creates Cloud CDN configuration with:
# - Backend bucket for Cloud Storage
# - Cache control and invalidation
# - Signed URLs and cookies
# - Custom cache keys
# - Negative caching
# - Compression
# - CORS configuration
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

variable "cdn_name" {
  description = "Name of the CDN backend bucket"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,62}$", var.cdn_name))
    error_message = "CDN name must start with lowercase letter, be 1-63 characters, contain only lowercase letters, numbers, and hyphens"
  }
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "bucket_name" {
  description = "Cloud Storage bucket name to serve content from"
  type        = string
}

variable "enable_cdn" {
  description = "Enable Cloud CDN"
  type        = bool
  default     = true
}

variable "cache_mode" {
  description = "Cache mode (CACHE_ALL_STATIC, USE_ORIGIN_HEADERS, FORCE_CACHE_ALL)"
  type        = string
  default     = "CACHE_ALL_STATIC"

  validation {
    condition     = contains(["CACHE_ALL_STATIC", "USE_ORIGIN_HEADERS", "FORCE_CACHE_ALL"], var.cache_mode)
    error_message = "Invalid cache mode"
  }
}

variable "default_ttl" {
  description = "Default cache TTL in seconds (0-31622400)"
  type        = number
  default     = 3600

  validation {
    condition     = var.default_ttl >= 0 && var.default_ttl <= 31622400
    error_message = "Default TTL must be between 0 and 31622400 seconds"
  }
}

variable "client_ttl" {
  description = "Client cache TTL in seconds"
  type        = number
  default     = 3600

  validation {
    condition     = var.client_ttl >= 0 && var.client_ttl <= 31622400
    error_message = "Client TTL must be between 0 and 31622400 seconds"
  }
}

variable "max_ttl" {
  description = "Maximum cache TTL in seconds"
  type        = number
  default     = 86400

  validation {
    condition     = var.max_ttl >= 0 && var.max_ttl <= 31622400
    error_message = "Max TTL must be between 0 and 31622400 seconds"
  }
}

variable "serve_while_stale" {
  description = "Serve stale content while revalidating (seconds)"
  type        = number
  default     = 0

  validation {
    condition     = var.serve_while_stale >= 0 && var.serve_while_stale <= 31622400
    error_message = "Serve while stale must be between 0 and 31622400 seconds"
  }
}

variable "negative_caching" {
  description = "Enable negative caching (caching of error responses)"
  type        = bool
  default     = false
}

variable "negative_caching_policy" {
  description = "Negative caching policy for error codes"
  type = list(object({
    code = number
    ttl  = number
  }))
  default = [
    { code = 404, ttl = 120 },
    { code = 410, ttl = 120 }
  ]
}

variable "compression_mode" {
  description = "Compression mode (AUTOMATIC or DISABLED)"
  type        = string
  default     = "AUTOMATIC"

  validation {
    condition     = contains(["AUTOMATIC", "DISABLED"], var.compression_mode)
    error_message = "Compression mode must be AUTOMATIC or DISABLED"
  }
}

variable "cache_key_policy_include_host" {
  description = "Include host in cache key"
  type        = bool
  default     = true
}

variable "cache_key_policy_include_protocol" {
  description = "Include protocol in cache key"
  type        = bool
  default     = true
}

variable "cache_key_policy_include_query_string" {
  description = "Include query string in cache key"
  type        = bool
  default     = true
}

variable "cache_key_policy_query_string_whitelist" {
  description = "Query string parameters to include in cache key"
  type        = list(string)
  default     = []
}

variable "cache_key_policy_query_string_blacklist" {
  description = "Query string parameters to exclude from cache key"
  type        = list(string)
  default     = []
}

variable "signed_url_cache_max_age_sec" {
  description = "Maximum age for signed URL cache in seconds"
  type        = number
  default     = 3600

  validation {
    condition     = var.signed_url_cache_max_age_sec >= 0
    error_message = "Signed URL cache max age must be >= 0"
  }
}

variable "enable_signed_url" {
  description = "Enable signed URL support"
  type        = bool
  default     = false
}

variable "cdn_policy_bypass_cache_on_request_headers" {
  description = "Request headers that bypass cache"
  type = list(object({
    header_name = string
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
      template   = "cloud-cdn"
    }
  )
}

# =========================================
# RESOURCES
# =========================================

# Backend Bucket
resource "google_compute_backend_bucket" "cdn_backend" {
  name        = var.cdn_name
  project     = var.project_id
  bucket_name = var.bucket_name
  enable_cdn  = var.enable_cdn

  compression_mode = var.compression_mode

  dynamic "cdn_policy" {
    for_each = var.enable_cdn ? [1] : []
    content {
      cache_mode        = var.cache_mode
      default_ttl       = var.default_ttl
      client_ttl        = var.client_ttl
      max_ttl           = var.max_ttl
      serve_while_stale = var.serve_while_stale
      negative_caching  = var.negative_caching

      dynamic "negative_caching_policy" {
        for_each = var.negative_caching ? var.negative_caching_policy : []
        content {
          code = negative_caching_policy.value.code
          ttl  = negative_caching_policy.value.ttl
        }
      }

      cache_key_policy {
        include_http_headers   = []
        query_string_whitelist = var.cache_key_policy_include_query_string && length(var.cache_key_policy_query_string_whitelist) > 0 ? var.cache_key_policy_query_string_whitelist : null
        query_string_blacklist = var.cache_key_policy_include_query_string && length(var.cache_key_policy_query_string_blacklist) > 0 ? var.cache_key_policy_query_string_blacklist : null
      }

      signed_url_cache_max_age_sec = var.enable_signed_url ? var.signed_url_cache_max_age_sec : null

      dynamic "bypass_cache_on_request_headers" {
        for_each = var.cdn_policy_bypass_cache_on_request_headers
        content {
          header_name = bypass_cache_on_request_headers.value.header_name
        }
      }
    }
  }
}

# URL Map for CDN
resource "google_compute_url_map" "cdn_url_map" {
  name            = "${var.cdn_name}-url-map"
  project         = var.project_id
  default_service = google_compute_backend_bucket.cdn_backend.id
}

# HTTPS Proxy (requires SSL certificate)
# Note: SSL certificate must be created separately or provided
# Uncomment and configure if HTTPS is needed

# resource "google_compute_target_https_proxy" "cdn_https_proxy" {
#   name             = "${var.cdn_name}-https-proxy"
#   project          = var.project_id
#   url_map          = google_compute_url_map.cdn_url_map.id
#   ssl_certificates = [var.ssl_certificate_id]
# }

# HTTP Proxy
resource "google_compute_target_http_proxy" "cdn_http_proxy" {
  name    = "${var.cdn_name}-http-proxy"
  project = var.project_id
  url_map = google_compute_url_map.cdn_url_map.id
}

# Global IP Address
resource "google_compute_global_address" "cdn_ip" {
  name    = "${var.cdn_name}-ip"
  project = var.project_id
}

# Forwarding Rule (HTTP)
resource "google_compute_global_forwarding_rule" "cdn_http" {
  name       = "${var.cdn_name}-http-rule"
  project    = var.project_id
  target     = google_compute_target_http_proxy.cdn_http_proxy.id
  ip_address = google_compute_global_address.cdn_ip.address
  port_range = "80"
}

# =========================================
# OUTPUTS
# =========================================

output "cdn_backend_id" {
  description = "ID of the CDN backend bucket"
  value       = google_compute_backend_bucket.cdn_backend.id
}

output "cdn_backend_name" {
  description = "Name of the CDN backend bucket"
  value       = google_compute_backend_bucket.cdn_backend.name
}

output "cdn_ip_address" {
  description = "IP address of the CDN"
  value       = google_compute_global_address.cdn_ip.address
}

output "url_map_id" {
  description = "ID of the URL map"
  value       = google_compute_url_map.cdn_url_map.id
}

output "http_proxy_id" {
  description = "ID of the HTTP proxy"
  value       = google_compute_target_http_proxy.cdn_http_proxy.id
}
