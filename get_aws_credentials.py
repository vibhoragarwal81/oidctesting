# script1_get_aws_credentials.py
import requests
import boto3
import json
import os
import datetime

# Entra ID (Azure AD) App details
TENANT_ID = os.environ["AZURE_TENANT_ID"]
CLIENT_ID = os.environ["AZURE_CLIENT_ID"]
CLIENT_SECRET = os.environ["AZURE_CLIENT_SECRET"]
OIDC_SCOPE = "api://aws-oidc/.default"  # Replace with your scope

# AWS Role details
ROLE_ARN = os.environ["AWS_ROLE_ARN"]
AWS_REGION = "us-east-1"

def get_oidc_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "scope": OIDC_SCOPE,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    print("Requesting token from Azure...")
    print("POST URL:", url)
    print("POST Data:", data)

    response = requests.post(url, data=data)
    
    print("Status Code:", response.status_code)
    print("Response Headers:", response.headers)
    print("Response Text:", response.text)

    response.raise_for_status()
    return response.json()["access_token"]

def assume_role_with_oidc(token):

    client = boto3.client("sts", region_name=AWS_REGION)
    response = client.assume_role_with_web_identity(
        RoleArn=ROLE_ARN,
        RoleSessionName="OIDCSession",
        WebIdentityToken=token,
        DurationSeconds=3600
    )
    creds = response["Credentials"]
    creds["Expiration"] = creds["Expiration"].isoformat()
    with open("aws_temp_creds.json", "w") as f:
        json.dump(creds, f)
        print("Temporary AWS credentials saved.")

if __name__ == "__main__":
    token = get_oidc_token()
    assume_role_with_oidc(token)
