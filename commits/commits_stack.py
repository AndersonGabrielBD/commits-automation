from aws_cdk import (
    Duration,
    Stack,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct

SECRET_NAME = "github-daily-commit-token"
REPO_OWNER = "AndersonGabrielBD"
REPO_NAME = "daily-log"
FILE_PATH = "commits.md"

# Repo that hosts this CDK project's CI/CD pipeline (GitHub Actions).
CI_REPO = "AndersonGabrielBD/commits-automation"


class CommitsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        github_token_secret = secretsmanager.Secret.from_secret_name_v2(
            self, "GitHubTokenSecret", SECRET_NAME
        )

        log_group = logs.LogGroup(
            self, "DailyCommitLogGroup",
            retention=logs.RetentionDays.ONE_MONTH,
        )

        daily_commit_fn = _lambda.Function(
            self, "DailyCommitFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambda/daily_commit"),
            timeout=Duration.seconds(30),
            memory_size=128,
            log_group=log_group,
            environment={
                "SECRET_NAME": SECRET_NAME,
                "REPO_OWNER": REPO_OWNER,
                "REPO_NAME": REPO_NAME,
                "FILE_PATH": FILE_PATH,
            },
        )

        github_token_secret.grant_read(daily_commit_fn)

        # 10:00 and 15:00 America/Sao_Paulo (UTC-3, no DST) -> 13:00 and 18:00 UTC.
        schedules = {
            "Morning": ("13", "morning"),
            "Afternoon": ("18", "afternoon"),
        }
        for label, (hour, slot) in schedules.items():
            rule = events.Rule(
                self, f"DailyCommitSchedule{label}",
                schedule=events.Schedule.cron(minute="0", hour=hour),
            )
            rule.add_target(
                targets.LambdaFunction(
                    daily_commit_fn,
                    retry_attempts=2,
                    event=events.RuleTargetInput.from_object({"slot": slot}),
                )
            )

        # --- CI/CD: let GitHub Actions deploy this stack via OIDC, no long-lived keys. ---
        github_provider = iam.OpenIdConnectProvider(
            self, "GitHubOidcProvider",
            url="https://token.actions.githubusercontent.com",
            client_ids=["sts.amazonaws.com"],
        )

        deploy_role = iam.Role(
            self, "GitHubActionsDeployRole",
            role_name="github-actions-cdk-deploy",
            max_session_duration=Duration.hours(1),
            assumed_by=iam.FederatedPrincipal(
                github_provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                    },
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub": f"repo:{CI_REPO}:*",
                    },
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity",
            ),
        )

        # The CDK bootstrap roles already hold the permissions needed to deploy
        # (file publishing, lookups, and CloudFormation execution via AdministratorAccess).
        # The CI role only needs to be able to assume them.
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                actions=["sts:AssumeRole"],
                resources=[f"arn:aws:iam::{self.account}:role/cdk-hnb659fds-*"],
            )
        )
