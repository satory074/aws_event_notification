import json
import os

import requests
from dotenv import load_dotenv

from webhook_data import WebhookData


def load_env():
    """For local testing"""
    if "accountId" not in os.environ:
        # read my_lambda.json
        with open("lambda.json", "r") as f:
            json_ = json.load(f)

        # make .env
        with open(".env", "w") as f:
            for k, v in json_["variables"].items():
                f.write(f"{k}={v}\n")

        load_dotenv()


def get_service_name(message, subject):
    """Get service name from message and subject"""
    if subject is None:
        if message["source"] == "aws.ec2":
            return "EC2"
    else:
        if "CodeDeploy" in subject:
            return "CodeDeploy"

        if "S3" in subject:
            return "S3"

    return None


def post(url, data):
    """Post webhook"""
    requests.post(url, json.dumps(data), headers={"Content-Type": "application/json"})


def lambda_handler(event, context):
    print(event)
    print(context)

    load_env()

    wd = WebhookData()

    for rec in event["Records"]:
        sns = rec["Sns"]
        subject = sns["Subject"]
        message = json.loads(sns["Message"])

        slack_data = None
        service_name = get_service_name(message, subject)

        if service_name is None:
            continue

        # Webhook data
        if service_name == "EC2":
            slack_data = wd.ec2(message)

        if service_name == "CodeDeploy":
            slack_data = wd.codedeploy(message)

        if service_name == "S3":
            slack_data = wd.s3(message)

        # Post
        for k, url in os.environ.items():
            # Error handling
            if slack_data is None:
                break

            if "Webhook" not in k:
                continue

            # Post
            if "slack" in url:
                post(url, slack_data)
                continue

            if "discord" in url:
                post(url, wd.convert_discord(slack_data))
                continue


# lambda_handler(None, None)
