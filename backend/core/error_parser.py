"""
Terraform Error Parser

Translates technical Terraform errors into user-friendly messages.
"""

import re
from typing import Dict, Optional, Tuple

# Error patterns and their friendly translations
ERROR_PATTERNS = [
    # Password validation errors
    {
        "pattern": r"admin_password.*fulfill.*conditions.*Has lower.*Has upper.*Has a digit.*Has a special character",
        "title": "Password Too Weak",
        "message": "Your password needs to be stronger.",
        "solution": "Use a password with: uppercase (A-Z), lowercase (a-z), numbers (0-9), and special characters (!@#$%)",
        "example": "Example: MyP@ssw0rd123"
    },
    {
        "pattern": r"admin_password.*at least (\d+) characters",
        "title": "Password Too Short",
        "message": "Your password is too short.",
        "solution": "Use a password with at least 12 characters.",
        "example": "Example: MyP@ssw0rd123"
    },

    # SSH Key errors
    {
        "pattern": r"admin_ssh_key.*not a complete SSH2 Public Key",
        "title": "Invalid SSH Key",
        "message": "The SSH public key format is incorrect.",
        "solution": "Use a valid SSH public key starting with 'ssh-rsa' or 'ssh-ed25519'.",
        "example": "Generate one with: ssh-keygen -t rsa -b 4096"
    },

    # Address space errors
    {
        "pattern": r"address_space requires \d+ item minimum.*has only 0",
        "title": "Missing Network Address",
        "message": "Virtual network address space is required.",
        "solution": "Enter a CIDR block for the virtual network.",
        "example": "Example: 10.0.0.0/16"
    },
    {
        "pattern": r"not.*valid CIDR",
        "title": "Invalid Network Address",
        "message": "The network address format is incorrect.",
        "solution": "Use CIDR notation (IP/prefix).",
        "example": "Example: 10.0.0.0/16 or 192.168.1.0/24"
    },

    # Azure Policy errors
    {
        "pattern": r"RequestDisallowedByAzure.*policy.*regions",
        "title": "Region Not Allowed",
        "message": "Your Azure subscription restricts deployments to certain regions.",
        "solution": "Try a different region that's allowed by your organization's policy.",
        "example": "Common regions: westeurope, northeurope, eastus"
    },

    # Resource Group errors
    {
        "pattern": r"Resource group.*not found|ResourceGroupNotFound",
        "title": "Resource Group Not Found",
        "message": "The specified resource group doesn't exist.",
        "solution": "Create the resource group first or select an existing one.",
        "example": None
    },

    # Quota errors
    {
        "pattern": r"QuotaExceeded|exceeds.*quota",
        "title": "Quota Exceeded",
        "message": "You've reached your Azure resource limit.",
        "solution": "Request a quota increase in Azure Portal or delete unused resources.",
        "example": None
    },

    # Name validation errors
    {
        "pattern": r"name.*can only contain|invalid.*name|naming convention",
        "title": "Invalid Resource Name",
        "message": "The resource name contains invalid characters.",
        "solution": "Use only lowercase letters, numbers, and hyphens. Start with a letter.",
        "example": "Example: my-storage-account-01"
    },
    {
        "pattern": r"Storage account name must be between (\d+) and (\d+) characters",
        "title": "Invalid Storage Account Name",
        "message": "Storage account name length is incorrect.",
        "solution": "Use 3-24 characters, only lowercase letters and numbers.",
        "example": "Example: mystorageaccount01"
    },
    {
        "pattern": r"already exists|is already taken|AlreadyExists",
        "title": "Name Already Taken",
        "message": "This resource name is already in use.",
        "solution": "Choose a different, unique name.",
        "example": None
    },

    # Authentication errors
    {
        "pattern": r"AuthorizationFailed|403.*Forbidden|Access Denied",
        "title": "Access Denied",
        "message": "You don't have permission to perform this action.",
        "solution": "Check your Azure credentials and permissions.",
        "example": None
    },
    {
        "pattern": r"authentication failed|invalid.*credentials|AADSTS",
        "title": "Authentication Failed",
        "message": "Azure login failed.",
        "solution": "Check your Azure credentials in the environment settings.",
        "example": None
    },

    # GCP Errors
    {
        "pattern": r"googleapi.*403|Permission.*denied.*GCP",
        "title": "GCP Access Denied",
        "message": "You don't have permission in Google Cloud.",
        "solution": "Check your GCP service account permissions.",
        "example": None
    },
    {
        "pattern": r"project.*not found|Project.*does not exist",
        "title": "GCP Project Not Found",
        "message": "The specified GCP project doesn't exist.",
        "solution": "Verify the project ID is correct.",
        "example": None
    },

    # Network/connectivity errors
    {
        "pattern": r"timeout|connection refused|network.*unreachable",
        "title": "Connection Failed",
        "message": "Could not connect to cloud provider.",
        "solution": "Check your internet connection and try again.",
        "example": None
    },

    # ===========================================
    # Validation/Security Errors (from security.py)
    # ===========================================
    {
        "pattern": r"Too many parameters.*max:\s*(\d+)",
        "title": "Too Many Parameters",
        "message": "You've provided too many configuration parameters.",
        "solution": "Reduce the number of parameters to 100 or fewer.",
        "example": None
    },
    {
        "pattern": r"Parameter name too long",
        "title": "Parameter Name Too Long",
        "message": "One of your parameter names exceeds the maximum length.",
        "solution": "Use shorter parameter names (max 100 characters).",
        "example": None
    },
    {
        "pattern": r"Parameter value too long for '([^']+)'",
        "title": "Parameter Value Too Long",
        "message": "The value for a parameter exceeds the maximum allowed length.",
        "solution": "Shorten the parameter value (max 10,000 characters).",
        "example": None
    },
    {
        "pattern": r"Invalid content.*contains shell metacharacters|[;&|`]",
        "title": "Invalid Characters Detected",
        "message": "Your input contains characters that aren't allowed for security reasons.",
        "solution": "Remove special characters like ; & | ` from your input.",
        "example": None
    },
    {
        "pattern": r"Invalid content.*contains path traversal|\.\./",
        "title": "Invalid Path Detected",
        "message": "Your input contains path patterns that aren't allowed.",
        "solution": "Remove '../' or '..\\ patterns from your input.",
        "example": None
    },
    {
        "pattern": r"Invalid content.*contains script tags|<script",
        "title": "Script Not Allowed",
        "message": "Your input contains script content that isn't allowed.",
        "solution": "Remove any script tags from your input.",
        "example": None
    },
    {
        "pattern": r"Invalid content.*contains SQL injection|DROP\s+TABLE",
        "title": "Invalid SQL Detected",
        "message": "Your input contains SQL patterns that aren't allowed.",
        "solution": "Remove any SQL commands from your input.",
        "example": None
    },
    {
        "pattern": r"Invalid content.*contains code execution|eval\s*\(",
        "title": "Code Execution Not Allowed",
        "message": "Your input contains code execution patterns that aren't allowed.",
        "solution": "Remove any eval() or similar patterns from your input.",
        "example": None
    },
    {
        "pattern": r"Invalid content in '([^']+)'",
        "title": "Invalid Input Detected",
        "message": "Your input contains content that isn't allowed for security reasons.",
        "solution": "Review your input and remove any special patterns or scripts.",
        "example": None
    },

    # ===========================================
    # Parameter Validation Errors
    # ===========================================
    {
        "pattern": r"Storage account name must be.*3.*24.*lowercase",
        "title": "Invalid Storage Account Name",
        "message": "Azure storage account names have specific requirements.",
        "solution": "Use 3-24 characters, only lowercase letters and numbers (no hyphens).",
        "example": "Example: mystorageaccount01"
    },
    {
        "pattern": r"Resource group name.*invalid|Resource group.*1-90 characters",
        "title": "Invalid Resource Group Name",
        "message": "The resource group name doesn't meet Azure requirements.",
        "solution": "Use 1-90 characters: letters, numbers, hyphens, underscores, periods, or parentheses.",
        "example": "Example: my-resource-group-01"
    },
    {
        "pattern": r"GCP bucket name.*invalid|Bucket name must be.*3-63",
        "title": "Invalid Bucket Name",
        "message": "The GCP bucket name doesn't meet requirements.",
        "solution": "Use 3-63 characters: lowercase letters, numbers, hyphens. Start/end with letter or number.",
        "example": "Example: my-storage-bucket-01"
    },
    {
        "pattern": r"Project ID.*invalid|project_id.*6-30 characters",
        "title": "Invalid GCP Project ID",
        "message": "The GCP project ID doesn't meet requirements.",
        "solution": "Use 6-30 characters: lowercase letters, numbers, hyphens. Start with a letter.",
        "example": "Example: my-project-123"
    },
    {
        "pattern": r"CIDR.*invalid|Invalid CIDR",
        "title": "Invalid Network Address",
        "message": "The network address (CIDR) format is incorrect.",
        "solution": "Use CIDR notation: IP address followed by /prefix.",
        "example": "Example: 10.0.0.0/16 or 192.168.1.0/24"
    },
    {
        "pattern": r"IP address.*invalid|Invalid IP",
        "title": "Invalid IP Address",
        "message": "The IP address format is incorrect.",
        "solution": "Use standard IPv4 format.",
        "example": "Example: 192.168.1.1"
    },
    {
        "pattern": r"app_name.*reserved word|name.*reserved|is a reserved word",
        "title": "Reserved Name",
        "message": "You can't use this name because it's reserved.",
        "solution": "Choose a different name that isn't a reserved word.",
        "example": None
    },
    {
        "pattern": r"app_name.*3-24 characters|name.*must be.*characters",
        "title": "Invalid Application Name",
        "message": "The application name length is incorrect.",
        "solution": "Use 3-24 characters: lowercase letters, numbers, and hyphens.",
        "example": "Example: my-web-app"
    },
]


def parse_terraform_error(error_message: str) -> Dict[str, str]:
    """
    Parse a Terraform error message and return a user-friendly version.

    Args:
        error_message: Raw Terraform error output

    Returns:
        Dictionary with title, message, solution, and optionally example
    """
    if not error_message:
        return {
            "title": "Unknown Error",
            "message": "An unexpected error occurred.",
            "solution": "Please try again or contact support.",
            "original": ""
        }

    # Normalize the error message
    normalized = error_message.lower()

    # Try to match against known patterns
    for pattern_info in ERROR_PATTERNS:
        if re.search(pattern_info["pattern"], error_message, re.IGNORECASE | re.DOTALL):
            result = {
                "title": pattern_info["title"],
                "message": pattern_info["message"],
                "solution": pattern_info["solution"],
                "original": _extract_key_error(error_message)
            }
            if pattern_info.get("example"):
                result["example"] = pattern_info["example"]
            return result

    # No pattern matched - return a cleaned up version
    return {
        "title": "Deployment Error",
        "message": _extract_key_error(error_message),
        "solution": "Review the error details and adjust your configuration.",
        "original": error_message[:500] if len(error_message) > 500 else error_message
    }


def _extract_key_error(error_message: str) -> str:
    """Extract the most relevant error line from Terraform output."""
    lines = error_message.split('\n')

    # Look for lines starting with "Error:"
    for line in lines:
        if line.strip().startswith('Error:'):
            return line.strip().replace('Error:', '').strip()

    # Look for lines containing common error indicators
    error_indicators = ['error:', 'failed:', 'invalid', 'not found', 'denied']
    for line in lines:
        lower_line = line.lower()
        if any(ind in lower_line for ind in error_indicators):
            clean_line = line.strip()
            if len(clean_line) > 10:  # Ignore very short lines
                return clean_line[:200]  # Truncate long lines

    # Return first non-empty line as fallback
    for line in lines:
        if line.strip():
            return line.strip()[:200]

    return "Deployment failed"


def format_friendly_error(error_message: str) -> str:
    """
    Format error for display in logs/UI.

    Returns a formatted string suitable for showing to users.
    """
    parsed = parse_terraform_error(error_message)

    parts = [
        f"❌ {parsed['title']}",
        f"   {parsed['message']}",
        f"   💡 {parsed['solution']}"
    ]

    if parsed.get("example"):
        parts.append(f"   📝 {parsed['example']}")

    return '\n'.join(parts)
