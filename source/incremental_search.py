import json
import logging
import traceback

import boto3
from boto3.dynamodb.conditions import Key

DYNAMODB = 'dynamodb'
TABLE_NAME = 'stations'

logger = logging.getLogger()
logLevel = logging.WARNING

def get_station_data_from_dynamodb(base_station_name):
    result = {'PossibleStations': []}

    # DynamoDBは空文字が検索できないので、空文字が来た場合は空のリストを返す
    if not base_station_name:
        return result

    dynamodb = boto3.resource(DYNAMODB)
    table = dynamodb.Table(TABLE_NAME)
    db_station_data = table.query(
        IndexName='forward_matching_index',
        KeyConditionExpression=Key('Station_Type').eq("train") & Key('Station_Name').begins_with(base_station_name)
    )

    for station in db_station_data['Items']:
        result['PossibleStations'].append(station['Station_Name'])

    return result

def lambda_handler(event, context):
    try:
        result = get_station_data_from_dynamodb(event['queryStringParameters'].get('baseStationName'))

        return {
            "isBase64Encoded": False,
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                # POSTではないのでAccess-Control-Allow-Headersは不要
            },
            'body': json.dumps(result)
        }
    except Exception as e:
        logger.warning(traceback.format_exc())
        logger.warning(event)
        return {
            "isBase64Encoded": False,
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                # POSTではないのでAccess-Control-Allow-Headersは不要
            },
            'body': json.dumps({'ErrorMessage': 'システムエラー'})
        }
