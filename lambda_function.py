import json

def lambda_handler(event, context):
    # ここに処理を書く
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
