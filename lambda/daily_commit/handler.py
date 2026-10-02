import base64
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

import boto3

SECRET_NAME = os.environ["SECRET_NAME"]
REPO_OWNER = os.environ["REPO_OWNER"]
REPO_NAME = os.environ["REPO_NAME"]
FILE_PATH = os.environ["FILE_PATH"]
BRANCH = os.environ.get("BRANCH", "main")

GITHUB_API = "https://api.github.com"


def _github_request(url, token, method="GET", body=None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "daily-commit-lambda",
    }
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def handler(event, context):
    slot = (event or {}).get("slot", "run")

    secrets = boto3.client("secretsmanager")
    token = secrets.get_secret_value(SecretId=SECRET_NAME)["SecretString"]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    marker = f"- {today} ({slot})"
    contents_url = f"{GITHUB_API}/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"

    try:
        current = _github_request(contents_url, token)
        current_content = base64.b64decode(current["content"]).decode("utf-8")
        sha = current["sha"]
    except urllib.error.HTTPError as err:
        if err.code == 404:
            current_content = "# Daily commit log\n\n"
            sha = None
        else:
            raise

    if marker in current_content:
        print(f"Already committed for {today} ({slot}), skipping.")
        return {"status": "skipped", "date": today, "slot": slot}

    new_content = current_content + f"{marker}\n"
    encoded = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")

    body = {
        "message": f"chore: daily log {today} ({slot})",
        "content": encoded,
        "branch": BRANCH,
    }
    if sha:
        body["sha"] = sha

    _github_request(contents_url, token, method="PUT", body=body)
    print(f"Committed log entry for {today} ({slot}).")
    return {"status": "committed", "date": today, "slot": slot}
