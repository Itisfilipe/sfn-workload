def handler(event, context):
    print("read from dynamo db")
    print(event)
    print(context)
    return ["TEST", "DONE"]
