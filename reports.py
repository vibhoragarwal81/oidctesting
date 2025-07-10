import boto3
import json
import csv
import os
import time
from botocore.exceptions import ClientError

def load_temp_credentials():
    with open("aws_temp_creds.json") as f:
        creds = json.load(f)
    return creds

def get_org_accounts(org_client):
    paginator = org_client.get_paginator("list_accounts")
    accounts = []
    for page in paginator.paginate():
        accounts.extend(page["Accounts"])
    return accounts

def assume_role(account_id, role_name, creds):
    sts = boto3.client("sts",
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"]
    )
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName="CrossAccountSession"
    )
    return response["Credentials"]

def list_iam_objects(iam_client):
    users = iam_client.list_users()["Users"]
    roles = iam_client.list_roles()["Roles"]
    groups = iam_client.list_groups()["Groups"]
    return users, roles, groups

def save_to_csv(data, filename):
    if not data:
        print(f"No data to write for {filename}")
        return
    fieldnames = sorted({key for item in data for key in item.keys()})
    dir_name = os.path.dirname(filename)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def save_json(data, filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as f:
        json.dump(data, f, indent=2, default=str)

def gather_iam_evidence(iam_client):
    print("Gathering IAM evidence")
    os.makedirs("iam_reports/IAM/groups", exist_ok=True)

    # Generate credentials report
    iam_client.generate_credential_report()
    time.sleep(5)
    credential_report = iam_client.get_credential_report()
    save_json(credential_report, "iam_reports/IAM/credentials_report.json")

    decoded_report = credential_report["Content"].decode("utf-8")
    with open("iam_reports/IAM/credentials_report.csv", "w") as f:
        f.write(decoded_report)

    # Get administrative entities
    admin_entities = iam_client.list_entities_for_policy(
        PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess"
    )
    save_json(admin_entities, "iam_reports/IAM/administrative_entities.json")

    for group in admin_entities.get("PolicyGroups", []):
        group_name = group["GroupName"]
        group_members = iam_client.get_group(GroupName=group_name)
        save_json(group_members, f"iam_reports/IAM/groups/{group_name}_members.json")

    # Get password policy
    try:
        password_policy = iam_client.get_account_password_policy()
        save_json(password_policy, "iam_reports/IAM/password_policy.json")
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            print("WARNING: IAM Password Policy has not been set.")
        else:
            raise

if __name__ == "__main__":
    creds = load_temp_credentials()
    org_client = boto3.client("organizations",
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"]
    )

    management_account_id = org_client.describe_organization()["Organization"]["MasterAccountId"]
    accounts = get_org_accounts(org_client)

    all_users, all_roles, all_groups = [], [], []

    for acct in accounts:
        acct_id = acct["Id"]
        if acct_id == management_account_id:
            print(f"Skipping management account: {acct_id}")
            continue
        try:
            temp_creds = assume_role(acct_id, "OrganizationAccountAccessRole", creds)
            iam = boto3.client("iam",
                aws_access_key_id=temp_creds["AccessKeyId"],
                aws_secret_access_key=temp_creds["SecretAccessKey"],
                aws_session_token=temp_creds["SessionToken"]
            )
            users, roles, groups = list_iam_objects(iam)
            all_users.extend(users)
            all_roles.extend(roles)
            all_groups.extend(groups)

            gather_iam_evidence(iam)

        except Exception as e:
            print(f"Failed for account {acct_id}: {e}")

    save_to_csv(all_users, "iam_users.csv")
    save_to_csv(all_roles, "iam_roles.csv")
    save_to_csv(all_groups, "iam_groups.csv")
