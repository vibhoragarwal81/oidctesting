import re

with open("get_aws_credentials.py", "r", encoding="utf-8") as f:
    content = f.read()

# Remove non-printable characters
cleaned = re.sub(r"[^\x20-\x7E\n\r\t]", "", content)

with open("get_aws_credentials.py", "w", encoding="utf-8") as f:
    f.write(cleaned)

print("Script cleaned successfully.")
