import os
from datetime import datetime

import boto3

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def retrieve_all_items():
    response = table.scan()
    data = response["Items"]
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        data.extend(response["Items"])
    return data


def handler(event, context):
    data = retrieve_all_items()
    # TODO: move this to somewhere else
    # THIS IS FOR TESTING. If the database is empty then use this data
    if not data:
        client1_data = {
            "Email": "email1@fakeemail.com",
            "Keywords": ["thinkpad t430", "macbook 16 polegadas"],
            "Created": f"{datetime.now():%Y-%m-%d %H:%M:%S%z}",
        }
        client2_data = {
            "Email": "email2@fakeemail.com",
            "Keywords": ["jeep compass", "jeep renegade"],
            "Created": f"{datetime.now():%Y-%m-%d %H:%M:%S%z}",
        }
        table.put_item(Item=client1_data)
        table.put_item(Item=client2_data)
        data = retrieve_all_items()

    # flag the stepFunction to indicated the end of the loop
    data.append("DONE")

    return {"ClientData": data}
