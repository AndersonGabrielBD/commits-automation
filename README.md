# commits-automation

Keeps the [`daily-log`](https://github.com/AndersonGabrielBD/daily-log) repo green: a scheduled AWS Lambda commits a line to it twice a day.

## How it works

- **AWS CDK** (Python) provisions the infrastructure in `commits/commits_stack.py`.
- A **Lambda function** (`lambda/daily_commit/handler.py`) reads a GitHub fine-grained PAT from
  AWS Secrets Manager and uses the GitHub Contents API to append a line to `commits.md` in the
  target repo.
- Two **EventBridge rules** trigger the Lambda daily at 10:00 and 15:00 (America/Sao_Paulo):
  each run is tagged with a `slot` (`morning` / `afternoon`) so both commits land even on the
  same day, and reruns within the same slot are idempotent (no duplicate commits).
- **GitHub Actions** (`.github/workflows/deploy.yml`) deploys on every push to `main` via OIDC
  (no long-lived AWS keys): pull requests get a `cdk synth` + `cdk diff` check, merges to `main`
  run `cdk deploy`.

## Local development

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cdk synth
cdk diff
cdk deploy
```

## Useful commands

* `cdk ls` — list all stacks in the app
* `cdk synth` — emit the synthesized CloudFormation template
* `cdk deploy` — deploy this stack to the configured AWS account/region
* `cdk diff` — compare the deployed stack with current state
