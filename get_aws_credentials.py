# script1_get_aws_credentials.py
import requests
import boto3
import json
import os

# Entra ID (Azure AD) App details
TENANT_ID = os.environ["AZURE_TENANT_ID"]
CLIENT_ID = os.environ["AZURE_CLIENT_ID"]
CLIENT_SECRET = os.environ["AZURE_CLIENT_SECRET"]
OIDC_SCOPE = "api://e331bd64-25f4-4c4b-a58a-6a92a9ff94d7/.default"  # Replace with your scope

# AWS Role details
ROLE_ARN = os.environ["AWS_ROLE_ARN"]
AWS_REGION = "us-east-1"

def get_oidc_token():
    url = f"https://login.microsoftonline.com/ac877863-5f25-4759-8c09-4d7b336b9341/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "scope": OIDC_SCOPE,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    response = requests.post(url, data=data)
    if response.status_code != 200:
    print("Error response:", response.text)
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
    with open("aws_temp_creds.json", "w") as f:
        json.dump(creds, f)

if __name__ == "__main__":
    token = get_oidc_token()
    assume_role_with_oidc(token)
