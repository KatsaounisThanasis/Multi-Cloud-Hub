# =========================================
# Google Cloud HTTP(S) Load Balancer - Terraform Template
# =========================================
# This template creates an HTTP(S) Load Balancer with:
# - Global external load balancing
# - Backend services with health checks
# - URL maps for routing
# - SSL certificates (managed or self-managed)
# - Cloud CDN integration
# - Cloud Armor security policies
# - Custom headers and redirects
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

variable "load_balancer_name" {
  description = "Name of the load balancer"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,62}$", var.load_balancer_name))
    error_message = "Load balancer name must start with lowercase letter, be 1-63 characters, contain only lowercase letters, numbers, and hyphens"
  }
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "enable_ssl" {
  description = "Enable HTTPS with SSL certificates"
  type        = bool
  default     = true
}

variable "ssl_policy" {
  description = "SSL policy name (optional)"
  type        = string
  default     = null
}

variable "managed_ssl_certificate_domains" {
  description = "List of domains for managed SSL certificates"
  type        = list(string)
  default     = []
}

variable "ssl_certificates" {
  description = "List of self-managed SSL certificate IDs"
  type        = list(string)
  default     = []
}

variable "enable_http" {
  description = "Enable HTTP (port 80)"
  type        = bool
  default     = true
}

variable "http_redirect_to_https" {
  description = "Redirect HTTP traffic to HTTPS"
  type        = bool
  default     = false
}

variable "enable_cdn" {
  description = "Enable Cloud CDN"
  type        = bool
  default     = false
}

variable "cdn_cache_mode" {
  description = "CDN cache mode (CACHE_ALL_STATIC, USE_ORIGIN_HEADERS, FORCE_CACHE_ALL)"
  type        = string
  default     = "CACHE_ALL_STATIC"

  validation {
    condition     = contains(["CACHE_ALL_STATIC", "USE_ORIGIN_HEADERS", "FORCE_CACHE_ALL"], var.cdn_cache_mode)
    error_message = "Invalid CDN cache mode"
  }
}

variable "cdn_default_ttl" {
  description = "Default CDN cache TTL in seconds"
  type        = number
  default     = 3600

  validation {
    condition     = var.cdn_default_ttl >= 0
    error_message = "CDN TTL must be >= 0"
  }
}

variable "cdn_max_ttl" {
  description = "Maximum CDN cache TTL in seconds"
  type        = number
  default     = 86400

  validation {
    condition     = var.cdn_max_ttl >= 0
    error_message = "CDN max TTL must be >= 0"
  }
}

variable "enable_iap" {
  description = "Enable Identity-Aware Proxy"
  type        = bool
  default     = false
}

variable "iap_oauth2_client_id" {
  description = "OAuth2 client ID for IAP"
  type        = string
  default     = ""
  sensitive   = true
}

variable "iap_oauth2_client_secret" {
  description = "OAuth2 client secret for IAP"
  type        = string
  default     = ""
  sensitive   = true
}

variable "backend_services" {
  description = "List of backend services"
  type = list(object({
    name                  = string
    protocol              = optional(string, "HTTP")
    port_name             = optional(string, "http")
    timeout_sec           = optional(number, 30)
    connection_draining_timeout_sec = optional(number, 300)
    session_affinity      = optional(string, "NONE")
    affinity_cookie_ttl_sec = optional(number, 0)

    # Health check
    health_check_path              = optional(string, "/")
    health_check_port              = optional(number, 80)
    health_check_interval_sec      = optional(number, 5)
    health_check_timeout_sec       = optional(number, 5)
    health_check_healthy_threshold = optional(number, 2)
    health_check_unhealthy_threshold = optional(number, 2)

    # Backends (instance groups or NEGs)
    backends = list(object({
      group                 = string
      balancing_mode        = optional(string, "UTILIZATION")
      capacity_scaler       = optional(number, 1.0)
      max_utilization       = optional(number, 0.8)
    }))

    # Security
    security_policy = optional(string, null)
  }))
  default = []
}

variable "url_map_host_rules" {
  description = "URL map host rules for routing"
  type = list(object({
    hosts        = list(string)
    path_matcher = string
  }))
  default = []
}

variable "url_map_path_matchers" {
  description = "URL map path matchers"
  type = list(object({
    name            = string
    default_service = string
    path_rules = optional(list(object({
      paths   = list(string)
      service = string
    })), [])
  }))
  default = []
}

variable "default_backend_service" {
  description = "Default backend service name (must be in backend_services list)"
  type        = string
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
      template   = "load-balancer"
    }
  )
}

# =========================================
# RESOURCES
# =========================================

# Health Checks
resource "google_compute_health_check" "health_checks" {
  for_each = { for backend in var.backend_services : backend.name => backend }

  name    = "${var.load_balancer_name}-${each.value.name}-hc"
  project = var.project_id

  check_interval_sec  = each.value.health_check_interval_sec
  timeout_sec         = each.value.health_check_timeout_sec
  healthy_threshold   = each.value.health_check_healthy_threshold
  unhealthy_threshold = each.value.health_check_unhealthy_threshold

  dynamic "http_health_check" {
    for_each = each.value.protocol == "HTTP" ? [1] : []
    content {
      port         = each.value.health_check_port
      request_path = each.value.health_check_path
    }
  }

  dynamic "https_health_check" {
    for_each = each.value.protocol == "HTTPS" ? [1] : []
    content {
      port         = each.value.health_check_port
      request_path = each.value.health_check_path
    }
  }
}

# Backend Services
resource "google_compute_backend_service" "backend_services" {
  for_each = { for backend in var.backend_services : backend.name => backend }

  name        = "${var.load_balancer_name}-${each.value.name}"
  project     = var.project_id
  protocol    = each.value.protocol
  port_name   = each.value.port_name
  timeout_sec = each.value.timeout_sec

  health_checks = [google_compute_health_check.health_checks[each.key].id]

  session_affinity        = each.value.session_affinity
  affinity_cookie_ttl_sec = each.value.affinity_cookie_ttl_sec

  connection_draining_timeout_sec = each.value.connection_draining_timeout_sec

  dynamic "backend" {
    for_each = each.value.backends
    content {
      group           = backend.value.group
      balancing_mode  = backend.value.balancing_mode
      capacity_scaler = backend.value.capacity_scaler
      max_utilization = backend.value.max_utilization
    }
  }

  dynamic "cdn_policy" {
    for_each = var.enable_cdn ? [1] : []
    content {
      cache_mode  = var.cdn_cache_mode
      default_ttl = var.cdn_default_ttl
      max_ttl     = var.cdn_max_ttl
    }
  }

  enable_cdn = var.enable_cdn

  dynamic "iap" {
    for_each = var.enable_iap ? [1] : []
    content {
      oauth2_client_id     = var.iap_oauth2_client_id
      oauth2_client_secret = var.iap_oauth2_client_secret
    }
  }

  security_policy = each.value.security_policy
}

# Managed SSL Certificates
resource "google_compute_managed_ssl_certificate" "managed_certs" {
  count = length(var.managed_ssl_certificate_domains) > 0 ? 1 : 0

  name    = "${var.load_balancer_name}-cert"
  project = var.project_id

  managed {
    domains = var.managed_ssl_certificate_domains
  }
}

# URL Map
resource "google_compute_url_map" "url_map" {
  name            = "${var.load_balancer_name}-url-map"
  project         = var.project_id
  default_service = google_compute_backend_service.backend_services[var.default_backend_service].id

  dynamic "host_rule" {
    for_each = var.url_map_host_rules
    content {
      hosts        = host_rule.value.hosts
      path_matcher = host_rule.value.path_matcher
    }
  }

  dynamic "path_matcher" {
    for_each = var.url_map_path_matchers
    content {
      name            = path_matcher.value.name
      default_service = google_compute_backend_service.backend_services[path_matcher.value.default_service].id

      dynamic "path_rule" {
        for_each = path_matcher.value.path_rules
        content {
          paths   = path_rule.value.paths
          service = google_compute_backend_service.backend_services[path_rule.value.service].id
        }
      }
    }
  }
}

# HTTP(S) Target Proxy
resource "google_compute_target_https_proxy" "https_proxy" {
  count = var.enable_ssl ? 1 : 0

  name    = "${var.load_balancer_name}-https-proxy"
  project = var.project_id
  url_map = google_compute_url_map.url_map.id

  ssl_certificates = concat(
    length(var.managed_ssl_certificate_domains) > 0 ? [google_compute_managed_ssl_certificate.managed_certs[0].id] : [],
    var.ssl_certificates
  )

  ssl_policy = var.ssl_policy
}

resource "google_compute_target_http_proxy" "http_proxy" {
  count = var.enable_http && !var.http_redirect_to_https ? 1 : 0

  name    = "${var.load_balancer_name}-http-proxy"
  project = var.project_id
  url_map = google_compute_url_map.url_map.id
}

# HTTP to HTTPS Redirect
resource "google_compute_url_map" "https_redirect" {
  count = var.enable_http && var.http_redirect_to_https ? 1 : 0

  name    = "${var.load_balancer_name}-https-redirect"
  project = var.project_id

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "https_redirect_proxy" {
  count = var.enable_http && var.http_redirect_to_https ? 1 : 0

  name    = "${var.load_balancer_name}-https-redirect-proxy"
  project = var.project_id
  url_map = google_compute_url_map.https_redirect[0].id
}

# Global Forwarding Rules
resource "google_compute_global_address" "lb_ip" {
  name    = "${var.load_balancer_name}-ip"
  project = var.project_id
}

resource "google_compute_global_forwarding_rule" "https" {
  count = var.enable_ssl ? 1 : 0

  name       = "${var.load_balancer_name}-https-rule"
  project    = var.project_id
  target     = google_compute_target_https_proxy.https_proxy[0].id
  ip_address = google_compute_global_address.lb_ip.address
  port_range = "443"
}

resource "google_compute_global_forwarding_rule" "http" {
  count = var.enable_http ? 1 : 0

  name       = "${var.load_balancer_name}-http-rule"
  project    = var.project_id
  target     = var.http_redirect_to_https ? google_compute_target_http_proxy.https_redirect_proxy[0].id : google_compute_target_http_proxy.http_proxy[0].id
  ip_address = google_compute_global_address.lb_ip.address
  port_range = "80"
}

# =========================================
# OUTPUTS
# =========================================

output "load_balancer_ip" {
  description = "IP address of the load balancer"
  value       = google_compute_global_address.lb_ip.address
}

output "backend_service_ids" {
  description = "Map of backend service names to IDs"
  value       = { for name, backend in google_compute_backend_service.backend_services : name => backend.id }
}

output "url_map_id" {
  description = "ID of the URL map"
  value       = google_compute_url_map.url_map.id
}

output "ssl_certificate_ids" {
  description = "IDs of managed SSL certificates"
  value       = length(var.managed_ssl_certificate_domains) > 0 ? [google_compute_managed_ssl_certificate.managed_certs[0].id] : []
}

output "https_proxy_id" {
  description = "ID of the HTTPS proxy"
  value       = var.enable_ssl ? google_compute_target_https_proxy.https_proxy[0].id : null
}

output "http_proxy_id" {
  description = "ID of the HTTP proxy"
  value       = var.enable_http && !var.http_redirect_to_https ? google_compute_target_http_proxy.http_proxy[0].id : null
}
