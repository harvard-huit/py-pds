import unittest
from unittest.mock import patch, Mock
import pds

class TestSearch(unittest.TestCase):
    def setUp(self):
        self.query = {'query': 'example'}  # Example JSON structure for parameters
        self.mock_json_response = {
            'results': ['item1'],  # Mock response with one item in the results array
            'count': 1,
            'total_count': 1,
            'session_id': "somesessionid"
        }
        # Constructing the mock response object
        self.mock_response = Mock()
        self.mock_response.json.return_value = self.mock_json_response
        self.mock_response.status_code = 200

        self.pds = pds.People(apikey="an api key")

    @patch('pds.requests.post')
    def test_search(self, mock_search):
        # Configure the mock to return a predefined response
        mock_search.return_value = self.mock_response

        response = self.pds.search(self.query)

        # Validate the response is a dictionary (JSON structure)
        self.assertIsInstance(response, dict)

        # Validate that 'results' is a key in the response dictionary
        self.assertIn('results', response)

        # Validate that 'results' key is associated with a list
        self.assertIsInstance(response['results'], list)

        # Validate that 'results' array has at least one element
        self.assertGreater(len(response['results']), 0)


    @patch('pds.requests.post')
    def test_search_pagination(self, mock_search):

        mock_paginated_json_response = {
            'results': ['item1'],  # Mock response with one item in the results array
            'count': 1,
            'total_count': 1,
            'session_id': "somesessionid"
        }
        # Constructing the mock response object
        mock_paginated_response = Mock()
        mock_paginated_response.json.return_value = mock_paginated_json_response
        mock_paginated_response.status_code = 200

        # Configure the mock to return a predefined response
        mock_search.return_value = mock_paginated_response

        response = self.pds.search(self.query, paginate=True)

        # Validate the response is a dictionary (JSON structure)
        self.assertIsInstance(response, dict)

        # Validate that 'results' is a key in the response dictionary
        self.assertIn('results', response)

        # Validate that 'results' key is associated with a list
        self.assertIsInstance(response['results'], list)

        # Validate that 'results' array has at least one element
        self.assertGreater(len(response['results']), 0)

        # Validate it has a session set
        self.assertIsNotNone(self.pds.session_id)
        self.assertEqual(self.pds.session_id, mock_paginated_json_response['session_id'])


    @patch('pds.requests.post')
    def test_search_context_error(self, mock_search):
        bad_search_context_mock_response = Mock()
        bad_search_context_mock_response.status_code = 401
        bad_search_context_mock_response.json.return_value = {
            "fault": {
                "faultstring": "failed."
            }
        }
        mock_search.return_value = bad_search_context_mock_response

        response = self.pds.search(self.query)
        
        # assert that we tried to call requests.post exactly 3 times
        self.assertEqual(mock_search.call_count, 3)





if __name__ == '__main__':
    unittest.main()
