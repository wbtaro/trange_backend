import json
import unittest

from source import incremental_search

class IncrementalSearchTonditionTest(unittest.TestCase):
    def test_incremental_search(self):
        test_cases = [
            [{'queryStringParameters': {"baseStationName": "相"}}, {"hasOneOrManyResults": True}],
            [{'queryStringParameters': {"baseStationName": "aaa"}}, {"hasOneOrManyResults": False}],
            [{'queryStringParameters': {"baseStationName": ""}}, {"hasOneOrManyResults": False}],
        ]
        for case, expected in test_cases:
            with self.subTest(case):
                result = incremental_search.lambda_handler(case, {})
                self.assertTrue(isinstance(json.loads(result['body'])['PossibleStations'], list))
                if expected['hasOneOrManyResults']:
                    self.assertGreater(len(json.loads(result['body'])['PossibleStations']), 0)
                else:
                    self.assertEqual(len(json.loads(result['body'])['PossibleStations']), 0)

if __name__ == '__main__':
    unittest.main()
