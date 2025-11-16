#!/usr/bin/env python3
"""
API Key Generator

This script generates a secure random API key for the Multi-Cloud Infrastructure API.
Use this to create API keys for production deployments.

Usage:
    python scripts/generate_api_key.py

The script will generate:
1. A secure random API key (plaintext - store this securely!)
2. The SHA-256 hash of the key (for verification)
"""

import secrets
import hashlib
import sys


def generate_api_key(length: int = 32) -> str:
    """
    Generate a secure random API key.

    Args:
        length: Length of the API key (default: 32)

    Returns:
        Secure random API key string
    """
    return secrets.token_urlsafe(length)


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage.

    Args:
        api_key: Plain text API key

    Returns:
        SHA-256 hash of the API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def main():
    """Generate and display a new API key."""
    print("=" * 80)
    print("Multi-Cloud Infrastructure API - API Key Generator")
    print("=" * 80)
    print()

    # Generate API key
    api_key = generate_api_key(32)
    api_key_hash = hash_api_key(api_key)

    print("✓ Generated secure API key")
    print()
    print("-" * 80)
    print("API Key (PLAINTEXT - Store this securely!):")
    print("-" * 80)
    print(api_key)
    print()
    print("-" * 80)
    print("API Key Hash (SHA-256):")
    print("-" * 80)
    print(api_key_hash)
    print()
    print("=" * 80)
    print("IMPORTANT INSTRUCTIONS:")
    print("=" * 80)
    print()
    print("1. Copy the API key (plaintext) above and store it securely")
    print("   - This is the ONLY time you will see the plaintext key")
    print("   - Store it in a password manager or secrets vault")
    print("   - You will need to provide this key in the X-API-Key header")
    print()
    print("2. Add the key to your environment:")
    print("   - For .env file:")
    print(f"     API_KEY={api_key}")
    print("   - For environment variable:")
    print(f"     export API_KEY='{api_key}'")
    print()
    print("3. Enable authentication:")
    print("   - Set API_AUTH_ENABLED=true in your .env file")
    print("   - Or: export API_AUTH_ENABLED=true")
    print()
    print("4. Restart the API server to apply changes")
    print()
    print("5. Test authentication:")
    print("   curl -H 'X-API-Key: <your-key>' http://localhost:8000/health")
    print()
    print("=" * 80)
    print()

    # Optionally generate multiple keys
    while True:
        response = input("Generate another key? (y/n): ").lower().strip()
        if response == 'y':
            print()
            api_key = generate_api_key(32)
            api_key_hash = hash_api_key(api_key)
            print(f"API Key: {api_key}")
            print(f"Hash:    {api_key_hash}")
            print()
        elif response == 'n':
            break
        else:
            print("Please enter 'y' or 'n'")

    print("Done! Thank you for using the Multi-Cloud Infrastructure API.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {str(e)}", file=sys.stderr)
        sys.exit(1)
