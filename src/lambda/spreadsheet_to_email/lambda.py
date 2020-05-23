import os

import boto3
from botocore.exceptions import ClientError


client = boto3.client("ses")
BUCKET_NAME = os.environ["BUCKET_NAME"]

# TODO: remember to create a SQS queue for those emails


def format_html_email(file_link):
    return f"""<html>
        <head></head>
        <body>
          <p>Download the spreadsheet <a href='{file_link}'>Download Link</a>.</p>
        </body>
        </html>
    """


def format_text_email(file_link):
    return f"Download the spreadsheet <a href='{file_link}'>Download Link"


def handler(event, context):
    recipient = event["ClientData"][0]["Email"]
    file_link = f"https://{BUCKET_NAME}.s3.amazonaws.com/{event['FileName']}"
    try:
        response = client.send_email(
            Destination={"ToAddresses": [recipient]},
            Message={
                "Body": {
                    "Html": {"Charset": "UTF-8", "Data": format_html_email(file_link)},
                    "Text": {"Charset": "UTF-8", "Data": format_text_email(file_link)},
                },
                "Subject": {
                    "Charset": "UTF-8",
                    "Data": "Daily delivery of the spreadsheet",
                },
            },
            Source="reports <no-reply@someemail.com.br>",
        )
    except ClientError as e:
        # TODO: add better error handling/logging
        print(e.response["Error"]["Message"])
    else:
        print("Email sent! Message ID:"),
        print(response["MessageId"])
    return event
