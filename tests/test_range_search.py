import copy
import json
import os
import unittest

from source import range_search
from source.range_search import SearchCondition
from source.range_search import SearchExecutor

base_station_name = 'BaseStationName'
upper_minute = 'UpperMinute'

class SearchConditionTest(unittest.TestCase):
    def test_parameter_is_valid(self):
        test_cases = [
            [{base_station_name: '津田沼', upper_minute: '20'}, {'result': True}],
            [{base_station_name: '', upper_minute: '20'}, {'result': False, 'msg': '起点駅を入力してください'}],
            [{base_station_name: 'aaa', upper_minute: '20'}, {'result': False, 'msg': 'aaa駅は存在しません'}],
            [{base_station_name: '津田沼', upper_minute: ''}, {'result': False, 'msg': '上限時間を入力してください'}],
            [{base_station_name: '津田沼', upper_minute: 'aaa'}, {'result': False, 'msg': '上限時間には半角数字を入力してください'}],
            [{base_station_name: '津田沼', upper_minute: '9'}, {'result': False, 'msg': '上限時間には10分以上200分以内を指定してください'}],
            [{base_station_name: '津田沼', upper_minute: '201'}, {'result': False, 'msg': '上限時間には10分以上200分以内を指定してください'}],
        ]

        for case, exepected in test_cases:
            search_condition = SearchCondition(case)
            with self.subTest(f'{case}'):
                if exepected['result']:
                    self.assertTrue(search_condition.parameter_is_valid())
                else:
                    self.assertFalse(search_condition.parameter_is_valid())
                    self.assertEqual(search_condition.error_message, exepected['msg'])
                del search_condition
    
    def test_set_station_code(self):
        # すでにbase_station_is_validでdynamodb上に対象駅が存在することが前提なので、存在しない駅名をしてするケースは不要
        condition = {base_station_name: '津田沼', upper_minute: '20'}
        search_condition = SearchCondition(condition)
        search_condition.set_station_code()
        self.assertEqual(search_condition.base_station_code, '22370')

class SearchExecutorTest(unittest.TestCase):
    def test_build_query_string(self):
        # APIキーの取り換えテスト用に仮の値を設定
        self.original_api_key = copy.copy(os.environ['EKISPART_API_KEY'])
        os.environ['EKISPART_API_KEY'] = 'aaa,bbb'

        test_cases = [
            {
                'conditions': [{base_station_name: '津田沼', upper_minute: '20'}],
                'api_key_num': 0,
                'expected': 'http://api.ekispert.jp/v1/json/search/multipleRange?key=aaa&baseList=22370&upperMinute=20'
            },
            {
                'conditions': [{base_station_name: '津田沼', upper_minute: '20'}, {base_station_name: '千葉', upper_minute: '10'}], 
                'api_key_num': 1,
                'expected': 'http://api.ekispert.jp/v1/json/search/multipleRange?key=bbb&baseList=22370:22361&upperMinute=20:10'
            }
        ]

        for case in test_cases:
            with self.subTest(case):
                conditions = [SearchCondition(condition) for condition in case['conditions']]
                for condition in conditions:
                    condition.set_station_code()
                search_executor = SearchExecutor(conditions)
                search_executor.build_query_string(case['api_key_num'])
                self.assertEqual(search_executor.query_string, case['expected'])

        # テスト用に設定したAPIキーを戻しておく
        os.environ['EKISPART_API_KEY'] = self.original_api_key

    def test_range_search(self):
        test_cases = [
            {
                'conditions': [{base_station_name: '津田沼', upper_minute: '20'}],
            },
            {
                'conditions': [{base_station_name: '津田沼', upper_minute: '20'}, {base_station_name: '千葉', upper_minute: '10'}], 
            },
            {
                'conditions': [{base_station_name: '津田沼', upper_minute: '20'}, {base_station_name: '上新庄', upper_minute: '10'}], 
            }
        ]

        for case in test_cases:
            with self.subTest(f'{case}'):
                conditions = [SearchCondition(condition) for condition in case['conditions']]
                for condition in conditions:
                    condition.set_station_code()
                search_executor = SearchExecutor(conditions)
                search_executor.build_query_string()
                search_executor.range_search()
                self.assertTrue(isinstance(search_executor.result['Stations'], list))

    def test_range_search_secondary_api_key(self):
        '''APIキー一つ目が無効なケース'''
        self.original_api_key = copy.copy(os.environ['EKISPART_API_KEY'])
        os.environ['EKISPART_API_KEY'] = 'aaa,' + self.original_api_key

        test_case = [{base_station_name: '津田沼', upper_minute: '20'}, {base_station_name: '千葉', upper_minute: '10'}]

        conditions = [SearchCondition(condition) for condition in test_case]
        for condition in conditions:
            condition.set_station_code()

        search_executor = SearchExecutor(conditions)
        search_executor.build_query_string()
        search_executor.range_search()
        self.assertTrue(isinstance(search_executor.result['Stations'], list))

        # テスト用に設定したAPIキーを戻しておく
        os.environ['EKISPART_API_KEY'] = self.original_api_key

    def test_lamda_handler(self):
        '''lambda_handlerのテスト兼、システムテスト'''
        search_conditions = json.dumps({'SearchConditions': [{base_station_name: '津田沼', upper_minute: '20'}, {base_station_name: '千葉', upper_minute: '10'}]})
        event = {
                'body': search_conditions
            }
        result = range_search.lambda_handler(event, {})
        self.assertEqual(result['statusCode'], 200)
        self.assertGreater(len(json.loads(result['body'])['Stations']), 0)

    def test_lamda_handler_input_errors(self):
        '''lambda_handlerのテスト兼、システムテスト, 入力エラーのケース'''
        search_conditions = json.dumps({'SearchConditions': [{base_station_name: '津田沼', upper_minute: '20'}, {base_station_name: '', upper_minute: '10'}]})
        event = {
                'body': search_conditions
            }
        result = range_search.lambda_handler(event, {})
        self.assertEqual(result['statusCode'], 200)
        self.assertEqual(json.loads(result['body'])['ErrorMessage'], '検索条件2: 起点駅を入力してください')
        
if __name__ == '__main__':
    unittest.main()
