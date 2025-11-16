# =========================================
# Google Cloud Armor - Terraform Template
# =========================================
# This template creates Cloud Armor security policies with:
# - DDoS protection
# - WAF rules (OWASP Top 10, ModSecurity CRS)
# - IP allowlist/blocklist
# - Geo-blocking
# - Rate limiting
# - Adaptive protection
# - Custom rules with conditions
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

variable "policy_name" {
  description = "Name of the Cloud Armor security policy"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,62}$", var.policy_name))
    error_message = "Policy name must start with lowercase letter, be 1-63 characters, contain only lowercase letters, numbers, and hyphens"
  }
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "description" {
  description = "Description of the security policy"
  type        = string
  default     = ""
}

variable "enable_adaptive_protection" {
  description = "Enable adaptive protection (DDoS detection)"
  type        = bool
  default     = false
}

variable "adaptive_protection_auto_deploy" {
  description = "Auto-deploy adaptive protection rules"
  type        = bool
  default     = false
}

variable "json_parsing" {
  description = "JSON parsing mode (DISABLED, STANDARD)"
  type        = string
  default     = "STANDARD"

  validation {
    condition     = contains(["DISABLED", "STANDARD"], var.json_parsing)
    error_message = "JSON parsing must be DISABLED or STANDARD"
  }
}

variable "log_level" {
  description = "Log level (NORMAL, VERBOSE)"
  type        = string
  default     = "NORMAL"

  validation {
    condition     = contains(["NORMAL", "VERBOSE"], var.log_level)
    error_message = "Log level must be NORMAL or VERBOSE"
  }
}

variable "rules" {
  description = "List of security rules"
  type = list(object({
    priority    = number
    action      = string  # allow, deny(403), deny(404), deny(502), rate_based_ban, redirect, throttle
    description = optional(string, "")
    preview     = optional(bool, false)

    # Match conditions
    src_ip_ranges        = optional(list(string), [])
    src_region_codes     = optional(list(string), [])
    expression           = optional(string, null)

    # Rate limiting
    rate_limit_threshold_count          = optional(number, null)
    rate_limit_threshold_interval_sec   = optional(number, null)
    rate_limit_conform_action           = optional(string, "allow")
    rate_limit_exceed_action            = optional(string, "deny(429)")
    rate_limit_enforce_on_key           = optional(string, "ALL")  # ALL, IP, HTTP_HEADER, etc.
    rate_limit_enforce_on_key_name      = optional(string, null)
    rate_limit_ban_duration_sec         = optional(number, 600)

    # Redirect (for redirect action)
    redirect_type   = optional(string, null)  # EXTERNAL_302, GOOGLE_RECAPTCHA
    redirect_target = optional(string, null)

    # Preconfigured WAF rules
    preconfigured_waf_config_exclusions = optional(list(object({
      target_rule_set = string
      target_rule_ids = optional(list(string), [])
      request_header = optional(list(object({
        operator = string
        value    = string
      })), [])
      request_uri = optional(list(object({
        operator = string
        value    = string
      })), [])
      request_query_param = optional(list(object({
        operator = string
        value    = string
      })), [])
    })), [])
  }))
  default = []
}

variable "preconfigured_waf_rules" {
  description = "Enable preconfigured WAF rule sets"
  type = list(object({
    priority             = number
    action               = string
    sensitivity_level    = optional(number, 1)  # 0-4, higher = more sensitive
    target_rule_set      = string  # sqli, xss, lfi, rfi, rce, methodenforcement, scannerdetection, protocolattack, etc.
    exclude_rule_ids     = optional(list(string), [])
  }))
  default = []
}

variable "default_rule_action" {
  description = "Default action for requests that don't match any rule (allow or deny)"
  type        = string
  default     = "allow"

  validation {
    condition     = contains(["allow", "deny(403)", "deny(404)", "deny(502)"], var.default_rule_action)
    error_message = "Default action must be allow, deny(403), deny(404), or deny(502)"
  }
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
      template   = "cloud-armor"
    }
  )

  # Combine custom rules and preconfigured WAF rules
  all_rules = concat(
    var.rules,
    [for waf in var.preconfigured_waf_rules : {
      priority                            = waf.priority
      action                              = waf.action
      description                         = "Preconfigured WAF: ${waf.target_rule_set}"
      preview                             = false
      src_ip_ranges                       = []
      src_region_codes                    = []
      expression                          = "evaluatePreconfiguredExpr('${waf.target_rule_set}', ${length(waf.exclude_rule_ids) > 0 ? jsonencode({target_rule_set = waf.target_rule_set, exclude_rule_ids = waf.exclude_rule_ids}) : "{}"})"
      rate_limit_threshold_count          = null
      rate_limit_threshold_interval_sec   = null
      rate_limit_conform_action           = null
      rate_limit_exceed_action            = null
      rate_limit_enforce_on_key           = null
      rate_limit_enforce_on_key_name      = null
      rate_limit_ban_duration_sec         = null
      redirect_type                       = null
      redirect_target                     = null
      preconfigured_waf_config_exclusions = []
    }]
  )
}

# =========================================
# RESOURCES
# =========================================

# Cloud Armor Security Policy
resource "google_compute_security_policy" "policy" {
  name        = var.policy_name
  project     = var.project_id
  description = var.description

  dynamic "adaptive_protection_config" {
    for_each = var.enable_adaptive_protection ? [1] : []
    content {
      layer_7_ddos_defense_config {
        enable          = true
        rule_visibility = var.adaptive_protection_auto_deploy ? "STANDARD" : "PREMIUM"
      }
    }
  }

  advanced_options_config {
    json_parsing = var.json_parsing
    log_level    = var.log_level
  }

  # Custom and WAF rules
  dynamic "rule" {
    for_each = { for r in local.all_rules : r.priority => r }
    content {
      priority    = rule.value.priority
      action      = rule.value.action
      description = rule.value.description
      preview     = rule.value.preview

      match {
        dynamic "config" {
          for_each = length(rule.value.src_ip_ranges) > 0 ? [1] : []
          content {
            src_ip_ranges = rule.value.src_ip_ranges
          }
        }

        dynamic "expr" {
          for_each = rule.value.expression != null ? [1] : []
          content {
            expression = rule.value.expression
          }
        }

        versioned_expr = length(rule.value.src_region_codes) > 0 ? "SRC_IPS_V1" : null
      }

      dynamic "rate_limit_options" {
        for_each = rule.value.rate_limit_threshold_count != null ? [1] : []
        content {
          conform_action = rule.value.rate_limit_conform_action
          exceed_action  = rule.value.rate_limit_exceed_action
          enforce_on_key = rule.value.rate_limit_enforce_on_key

          enforce_on_key_name = rule.value.rate_limit_enforce_on_key_name

          ban_duration_sec = rule.value.rate_limit_ban_duration_sec

          rate_limit_threshold {
            count        = rule.value.rate_limit_threshold_count
            interval_sec = rule.value.rate_limit_threshold_interval_sec
          }
        }
      }

      dynamic "redirect_options" {
        for_each = rule.value.redirect_type != null ? [1] : []
        content {
          type   = rule.value.redirect_type
          target = rule.value.redirect_target
        }
      }
    }
  }

  # Default rule (lowest priority)
  rule {
    priority    = 2147483647
    action      = var.default_rule_action
    description = "Default rule"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
  }
}

# =========================================
# OUTPUTS
# =========================================

output "policy_id" {
  description = "ID of the Cloud Armor security policy"
  value       = google_compute_security_policy.policy.id
}

output "policy_name" {
  description = "Name of the Cloud Armor security policy"
  value       = google_compute_security_policy.policy.name
}

output "policy_self_link" {
  description = "Self link of the security policy"
  value       = google_compute_security_policy.policy.self_link
}

output "policy_fingerprint" {
  description = "Fingerprint of the security policy"
  value       = google_compute_security_policy.policy.fingerprint
}
