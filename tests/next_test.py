import unittest
from unittest.mock import patch, Mock
import pds

class TestNext(unittest.TestCase):
    def setUp(self):
        self.query = {'query': 'example'}  # Example JSON structure for parameters
        self.mock_next_success_json_response = {
            'results': ['item1'],  # Mock response with one item in the results array
            'count': 1,
            'total_count': 1,
            'session_id': "some session id"

        }
        # Constructing the mock response object
        self.mock_next_success_response = Mock()
        self.mock_next_success_response.json.return_value = self.mock_next_success_json_response
        self.mock_next_success_response.status_code = 200


        self.pds = pds.People(apikey="an api key")
        self.pds.session_id = self.mock_next_success_json_response['session_id']

    @patch('pds.requests.post')
    def test_next_success(self, mock_search):
        # Configure the mock to return a predefined response
        mock_search.return_value = self.mock_next_success_response
        starting_session_id = self.pds.session_id
    
        next_response = self.pds.next()

        # Validate the response is a dictionary (JSON structure)
        self.assertIsInstance(next_response, dict)

        # Validate that 'results' is a key in the response dictionary
        self.assertIn('results', next_response)

        # Validate that 'results' key is associated with a list
        self.assertIsInstance(next_response['results'], list)

        # Validate that 'results' array has at least one element
        self.assertGreater(len(next_response['results']), 0)

        # Validate it has session still set
        self.assertIsNotNone(self.pds.session_id)
        self.assertEqual(self.pds.session_id, starting_session_id)


    @patch('pds.requests.post')
    def test_search_context_error(self, mock_search):
        bad_search_context_mock_response = Mock()
        bad_search_context_mock_response.status_code = 401
        bad_search_context_mock_response.json.return_value = {
            "fault": {
                "faultstring": "Search context not found. Either the search session has timed out or otherwise does not exist. Default timeout is 3 minutes."
            }
        }
        mock_search.return_value = bad_search_context_mock_response

        response = self.pds.next()
        
        # assert that we tried to call requests.post exactly 3 times
        self.assertEqual(mock_search.call_count, 3)




if __name__ == '__main__':
    unittest.main()
