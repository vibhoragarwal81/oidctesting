import boto3
import json
import csv

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
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

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
        except Exception as e:
            print(f"Failed for account {acct_id}: {e}")

    save_to_csv(all_users, "iam_users.csv")
    save_to_csv(all_roles, "iam_roles.csv")
    save_to_csv(all_groups, "iam_groups.csv")
