#!/usr/bin/env python3
import os

import aws_cdk as cdk

from commits.commits_stack import CommitsStack


app = cdk.App()
CommitsStack(app, "CommitsStack",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
    )

app.synth()
