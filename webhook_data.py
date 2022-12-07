import json
import math
from datetime import datetime as dt

import boto3


class WebhookData:
    def __init__(self):
        self.COLORS = {
            "CodeDeploy": {"CREATED": "#008000", "SUCCEEDED": "#008000", "FAILED": "#FF6347"},
            "EC2": {"StartInstances": "#008000", "RebootInstances": "#008B8B", "StopInstances": "#FF6347"},
            "S3": {
                "ObjectCreated:CompleteMultipartUpload": "008000",
                "ObjectCreated:Put": "#008000",
                "ObjectCreated:Post": "#008000",
                "ObjectCreated:Copy": "#008B8B",
                "ObjectRemoved:Delete": "#FF6347",
                "ObjectRemoved:DeleteMarkerCreated": "#FF6347",
            },
        }

    def _convert_size(self, size):
        """ Convert size to readable format """

        if size == "":
            return ""

        units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB")
        i = math.floor(math.log(size, 1024)) if size > 0 else 0
        size = round(size / 1024 ** i, 2)

        return f"{size} {units[i]}"

    def codedeploy(self, message):
        """"Make webhook data for CodeDeploy"""
        color = self.COLORS["CodeDeploy"].get(message["status"], "#000000")

        description = ""
        if "errorInformation" in message:
            errors = json.loads(message["errorInformation"])
            for k, v in errors.items():
                description += f"{k}: {v}\n"

        # Webhook data
        fields = []

        fields.append({"title": "region", "value": message["region"], "short": True})
        fields.append({"title": "deploymentGroupName", "value": message["deploymentGroupName"], "short": True})

        data = {
            "attachments": [
                {
                    "title": message["applicationName"],
                    "text": description,
                    "color": color,
                    "author_name": "CodeDeploy",
                    "author_icon": "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist/DeveloperTools/CodeDeploy.png",
                    "fields": [],
                    "footer": message["status"],
                    "ts": dt.strptime(message["createTime"], "%a %b %d %H:%M:%S %Z %Y").timestamp(),
                }
            ],
        }

        return data

    def ec2(self, message):
        """Make webhook data for EC2"""
        instance_id = message["detail"]["requestParameters"]["instancesSet"]["items"][0]["instanceId"]

        client = boto3.client("ec2")
        response = client.describe_instances(InstanceIds=[instance_id])

        color = self.COLORS["EC2"].get(message["detail"]["eventName"], "#000000")

        # Webhook data
        fields = []

        fields.append({"title": "region", "value": message["region"], "short": True})

        for tag in response["Reservations"][0]["Instances"][0]["Tags"]:
            if tag["Key"] != "Name":
                continue

            fields.append({"title": "TagName", "value": tag["Value"], "short": True})

        data = {
            "attachments": [
                {
                    "title": instance_id,
                    "color": color,
                    "author_name": "EC2",
                    "author_icon": "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist/Compute/EC2.png",
                    "fields": fields,
                    "footer": message["detail"]["eventName"],
                    "ts": dt.strptime(message["time"], "%Y-%m-%dT%H:%M:%SZ").timestamp(),
                }
            ],
        }

        return data

    def s3(self, message):
        """Make webhook data for S3"""
        rec = message["Records"][0]

        color = self.COLORS["S3"].get(rec["eventName"], "#000000")
        size = self._convert_size(rec["s3"]["object"].get("size", ""))

        # Webhook data
        fields = []

        fields.append({"title": "awsRegion", "value": rec["awsRegion"], "short": True})
        fields.append({"title": "bucket", "value": rec["s3"]["bucket"]["name"], "short": True})

        data = {
            "attachments": [
                {
                    "title": rec["s3"]["object"]["key"],
                    "text": size,
                    "color": color,
                    "author_name": "S3",
                    "author_icon": "https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/main/dist/Storage/SimpleStorageService.png",
                    "fields": fields,
                    "footer": rec["eventName"],
                    "ts": dt.strptime(rec["eventTime"], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp(),
                }
            ],
        }

        return data

    def convert_discord(self, slack_data):
        """Convert Slack webhook data to Discord webhook data"""
        slack_data = slack_data["attachments"][0]

        data = {
            "username": slack_data["author_name"],
            "avatar_url": slack_data["author_icon"],
            "embeds": [
                {
                    "title": slack_data["title"],
                    "description": slack_data.get("text", ""),
                    "color": int(slack_data["color"][1:], 16),
                    "footer": {"text": slack_data["footer"]},
                    "timestamp": dt.fromtimestamp(slack_data["ts"]).strftime("%Y-%m-%d %H:%M:%S"),
                    "fields": [],
                }
            ],
        }

        for field in slack_data["fields"]:
            data["embeds"][0]["fields"].append(
                {"name": field["title"], "value": field["value"], "inline": field["short"]}
            )

        return data
