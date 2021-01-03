import json
import logging
import os
import traceback

import boto3
from boto3.dynamodb.conditions import Key
import requests

DYNAMODB = 'dynamodb'
TABLE_NAME = 'stations'
EKISPART_API_URL = 'http://api.ekispert.jp/v1/json/search/multipleRange?'

logger = logging.getLogger()
logLevel = logging.WARNING

class SearchCondition:
    '''検索条件クラス'''
    def __init__(self, condition):
        self.base_station_name = condition.get('BaseStationName')
        self.upper_minute = condition.get('UpperMinute')

    def parameter_is_valid(self):
        '''検索条件の入力値チェック'''
        if not self.base_station_name_is_valid():
            return False

        if not self.upper_minute_is_valid():
            return False

        return True

    def set_station_code(self):
        '''Dynamodbのstationsテーブルを利用して駅名から駅コードを取得'''
        db_station_data = self.get_station_data_from_dynamodb()
        self.base_station_code = db_station_data['Items'][0]['Station_code']

    def base_station_name_is_valid(self):
        '''起点駅の入力値チェック'''
        # 起点駅は入力必須
        if not self.base_station_name:
            self.error_message = '起点駅を入力してください'
            return False

        # 起点駅がDynamoDBにあるかチェック
        db_station_data = self.get_station_data_from_dynamodb()
        if not db_station_data['Items']:
            self.error_message = f'{self.base_station_name}駅は存在しません'
            return False

        return True

    def upper_minute_is_valid(self):
        # 上限時間は入力必須
        if not self.upper_minute:
            self.error_message = '上限時間を入力してください'
            return False

        # 上限時間は整数限定
        if not self.upper_minute.isdecimal():
            self.error_message = '上限時間には半角数字を入力してください'
            return False

        # 上限時間は10分以上200分以内
        if int(self.upper_minute) < 10 or int(self.upper_minute) > 200:
            self.error_message = '上限時間には10分以上200分以内を指定してください'
            return False

        return True
    
    def get_station_data_from_dynamodb(self):
        dynamodb = boto3.resource(DYNAMODB)
        table = dynamodb.Table(TABLE_NAME)
        db_station_data = table.query(
            IndexName='forward_matching_index',
            KeyConditionExpression=Key('Station_Type').eq("train") & Key('Station_Name').eq(self.base_station_name)
        )
        return db_station_data

class SearchExecutor():
    '''範囲検索用クラス'''
    def __init__(self, conditions):
        self.conditions = conditions

    def build_query_string(self, api_key_num=0):
        '''駅すぱあとAPIの範囲検索に合わせた検索用urlを組み立てる'''
        self.query_string = EKISPART_API_URL
        # APIキーが切れた場合はapi_key_numに0以外の値が渡され、再度検索用URLを作成する
        self.query_string += 'key=' + os.environ['EKISPART_API_KEY'].split(',')[api_key_num] + '&'

        stations_query_string = 'baseList='
        upper_minute_query_string = 'upperMinute='
        for condition in self.conditions:
            stations_query_string += condition.base_station_code
            upper_minute_query_string += condition.upper_minute
            # 駅すぱあとAPIは:区切り
            if condition != self.conditions[-1]:
                stations_query_string += ':'
                upper_minute_query_string += ':'

        self.query_string += stations_query_string + '&' + upper_minute_query_string

    def range_search(self):
        '''範囲検索実行'''
        response = requests.get(self.query_string).json()
        # APIキーが回数切れの場合は別のキーを指定して再実行
        if 'Error' in response['ResultSet'].keys() and response['ResultSet']['Error']['code'] == 'W403':
            logger.warning('APIキーが無効になっています')
            self.build_query_string(api_key_num=1)
            response = requests.get(self.query_string).json()

        self.result = {}

        # 検索結果が0件の場合
        if 'Point' not in response['ResultSet'].keys():
            self.result['Stations'] = []
            return

        # 駅すぱあとAPIは結果が一個だとリストでなく単体で返してくるので、リスト形式に統一。テスト困難
        if isinstance(response["ResultSet"]["Point"], list):
            self.result['Stations'] = response["ResultSet"]["Point"]
        else:
            self.result['Stations'] = [response["ResultSet"]["Point"]]
        
        # 検索条件が一つだとCost属性は単体で返ってくるので、リスト形式に統一
        for station in self.result['Stations']:
            if not isinstance(station['Cost'], list):
                station['Cost'] =[station['Cost']]

def lambda_handler(event, context):
    try:
        search_conditions = [SearchCondition(condition) for condition in json.loads(event['body']).get('SearchConditions')]
        for i, condition in enumerate(search_conditions):
            if not condition.parameter_is_valid():
                return {
                    'statusCode': 200,
                    'body': json.dumps({'ErrorMessage': f'検索条件{i+1}: {condition.error_message}'})
                }
            # DynamoDBは空文字を検索しようとすると怒るので、チェックを通過してから駅コードをセットする必要がある
            condition.set_station_code()

        search_executor = SearchExecutor(search_conditions)
        search_executor.build_query_string()
        search_executor.range_search()
        
        return {
            'statusCode': 200,
            'body': json.dumps(search_executor.result)
        }

    except Exception as e:
        logger.warning(traceback.format_exc())
        logger.warning(event)
        return {
            'statusCode': 500,
            'body': json.dumps({'ErrorMessage': 'システムエラー'})
        }
