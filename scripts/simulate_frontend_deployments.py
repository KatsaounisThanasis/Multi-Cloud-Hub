
import requests
import time
import os
import random
import string
import json
from dotenv import load_dotenv

# Load env for verification but use API for everything else
load_dotenv()

API_URL = "http://localhost:8000"
USER_EMAIL = f"tester_{int(time.time())}@example.com"
PASSWORD = "SecurePass123!"
USERNAME = "TestUser"

def get_random_string(length=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def register_and_login():
    print(f"[*] Registering user {USER_EMAIL}...")
    try:
        # Register
        reg_payload = {"email": USER_EMAIL, "username": USERNAME, "password": PASSWORD}
        resp = requests.post(f"{API_URL}/auth/register", json=reg_payload)
        if resp.status_code not in [200, 201]:
            # Try login if already exists
            print("    User might exist, trying login...")
        
        # Login
        login_payload = {"email": USER_EMAIL, "password": PASSWORD}
        resp = requests.post(f"{API_URL}/auth/login", json=login_payload)
        resp.raise_for_status()
        token = resp.json()["data"]["access_token"]
        print("    [+] Login successful!")
        return token
    except Exception as e:
        print(f"    [-] Auth failed: {e}")
        try: 
            print(f"    Response: {resp.text}")
        except: pass
        exit(1)

def monitor_deployment(token, deployment_id):
    print(f"    Monitoring deployment {deployment_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    
    start_time = time.time()
    while True:
        resp = requests.get(f"{API_URL}/deployments/{deployment_id}/status", headers=headers)
        if resp.status_code != 200:
            print(f"    [-] Failed to get status: {resp.text}")
            return False
            
        data = resp.json()["data"]
        status = data["status"]
        
        print(f"    -> Status: {status} (Elapsed: {int(time.time() - start_time)}s)")
        
        if status.lower() == "completed":
            print(f"    [+] Deployment COMPLETED!")
            return True
        elif status.lower() == "failed":
            print(f"    [-] Deployment FAILED!")
            if "error_message" in data:
                print(f"    Error: {data['error_message']}")
            return False
            
        time.sleep(5)
        
        # Timeout after 10 minutes
        if time.time() - start_time > 600:
            print("    [-] Timeout waiting for deployment")
            return False

def deploy_azure_storage(token):
    print("\n[1/4] Deploying Azure Storage Account...")
    suffix = get_random_string()
    payload = {
        "template_name": "storage-account",
        "provider_type": "terraform-azure",
        "resource_group": "multicloud-test-rg",
        "location": "norwayeast",
        "parameters": {
            "app_name": f"testsa{suffix}",
            "storage_account_name": f"testsa{suffix}",
            "account_tier": "Standard",
            "account_replication_type": "LRS",
            "resource_group_name": "multicloud-test-rg"
        }
    }
    return trigger_deploy(token, payload)

def deploy_azure_vnet(token):
    print("\n[2/4] Deploying Azure Virtual Network...")
    suffix = get_random_string()
    payload = {
        "template_name": "virtual-network",
        "provider_type": "terraform-azure",
        "resource_group": "multicloud-test-rg",
        "location": "norwayeast",
        "parameters": {
            "app_name": f"test-vnet-{suffix}",
            "vnet_name": f"test-vnet-{suffix}",
            "address_space": ["10.0.0.0/16"],
            "resource_group_name": "multicloud-test-rg"
        }
    }
    return trigger_deploy(token, payload)

def deploy_gcp_bucket(token):
    print("\n[3/4] Deploying GCP Storage Bucket...")
    suffix = get_random_string()
    project_id = os.getenv("GOOGLE_PROJECT_ID")
    if not project_id:
        print("    [-] GOOGLE_PROJECT_ID not found in env, skipping GCP tests")
        return None

    payload = {
        "template_name": "storage-bucket",
        "provider_type": "terraform-gcp",
        "resource_group": "gcp-test-group", # Logical grouping
        "location": "US",
        "parameters": {
            "app_name": f"test-bucket-{suffix}",
            "bucket_name": f"test-bucket-{suffix}",
            "project_id": project_id,
            "storage_class": "STANDARD",
            "location": "US"
        }
    }
    return trigger_deploy(token, payload)

def deploy_gcp_pubsub(token):
    print("\n[4/4] Deploying GCP Pub/Sub Topic...")
    suffix = get_random_string()
    project_id = os.getenv("GOOGLE_PROJECT_ID")
    if not project_id:
        return None

    payload = {
        "template_name": "pub-sub",
        "provider_type": "terraform-gcp",
        "resource_group": "gcp-test-group",
        "location": "us-central1",
        "parameters": {
            "app_name": f"test-topic-{suffix}",
            "topic_name": f"test-topic-{suffix}",
            "project_id": project_id
        }
    }
    return trigger_deploy(token, payload)

def trigger_deploy(token, payload):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.post(f"{API_URL}/deploy", json=payload, headers=headers)
        if resp.status_code == 202:
            data = resp.json()["data"]
            dep_id = data["deployment_id"]
            print(f"    [+] Deployment Queued: {dep_id}")
            return dep_id
        else:
            print(f"    [-] Failed to queue: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"    [-] Request failed: {e}")
        return None

if __name__ == "__main__":
    print("=== Starting Actual Cloud Deployment Tests ===")
    
    token = register_and_login()
    results = {}
    
    # 1. Azure Storage
    dep_id = deploy_azure_storage(token)
    if dep_id:
        success = monitor_deployment(token, dep_id)
        results["Azure Storage"] = "SUCCESS" if success else "FAILED"
    
    # 2. Azure VNet
    # dep_id = deploy_azure_vnet(token)
    # if dep_id:
    #     success = monitor_deployment(token, dep_id)
    #     results["Azure VNet"] = "SUCCESS" if success else "FAILED"
        
    # 3. GCP Bucket
    dep_id = deploy_gcp_bucket(token)
    if dep_id:
        success = monitor_deployment(token, dep_id)
        results["GCP Bucket"] = "SUCCESS" if success else "FAILED"
        
    # 4. GCP PubSub
    # dep_id = deploy_gcp_pubsub(token)
    # if dep_id:
    #     success = monitor_deployment(token, dep_id)
    #     results["GCP PubSub"] = "SUCCESS" if success else "FAILED"
    
    print("\n=== Test Summary ===")
    for test, res in results.items():
        print(f"{test}: {res}")
        
    print("\nNOTE: Resources were created in 'multicloud-test-rg' (Azure) and your GCP Project.")
    print("Please manually delete them or run 'terraform destroy' locally if needed.")
