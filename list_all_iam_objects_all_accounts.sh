#!/bin/bash

ROLE_NAME="OrganizationAccountAccessRole"
SESSION_NAME="ListIAMObjectsSession"
OUTPUT_FILE="iam_discovery_report.csv"

echo "Account ID,Users,Roles,Policies,IdentityProviders" > $OUTPUT_FILE

# Save original credentials
ORIG_AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
ORIG_AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
ORIG_AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN

ACCOUNT_IDS=$(aws organizations list-accounts --query "Accounts[?Status=='ACTIVE'].Id" --output text)

for ACCOUNT_ID in $ACCOUNT_IDS; do
  echo -e "\n🔄 Assuming role in account: $ACCOUNT_ID"

  export AWS_ACCESS_KEY_ID=$ORIG_AWS_ACCESS_KEY_ID
  export AWS_SECRET_ACCESS_KEY=$ORIG_AWS_SECRET_ACCESS_KEY
  export AWS_SESSION_TOKEN=$ORIG_AWS_SESSION_TOKEN

  CREDS=$(aws sts assume-role \
    --role-arn arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME \
    --role-session-name $SESSION_NAME \
    --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' \
    --output text)

  if [ $? -ne 0 ]; then
    echo "❌ Failed to assume role in account $ACCOUNT_ID"
    continue
  fi

  ACCESS_KEY=$(echo $CREDS | awk '{print $1}')
  SECRET_KEY=$(echo $CREDS | awk '{print $2}')
  SESSION_TOKEN=$(echo $CREDS | awk '{print $3}')

  export AWS_ACCESS_KEY_ID=$ACCESS_KEY
  export AWS_SECRET_ACCESS_KEY=$SECRET_KEY
  export AWS_SESSION_TOKEN=$SESSION_TOKEN

  USERS=$(aws iam list-users --query 'Users[*].UserName' --output json | jq length)
  ROLES=$(aws iam list-roles --query 'Roles[?contains(RoleName, \"AWSServiceRoleFor\") == \`false\`].[RoleName]' --output json | jq length)
  POLICIES=$(aws iam list-policies --scope Local --query 'Policies[*].PolicyName' --output json | jq length)
  IDPS=$(aws iam list-open-id-connect-providers --output json | jq '.OpenIDConnectProviderList | length')

  echo "$ACCOUNT_ID,$USERS,$ROLES,$POLICIES,$IDPS" >> $OUTPUT_FILE
done

echo -e "\n✅ IAM discovery report saved to $OUTPUT_FILE"
