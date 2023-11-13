import unittest
from unittest.mock import MagicMock
from pds import People

class TestPagination(unittest.TestCase):
    def setUp(self):
        self.pds = People(apikey="12345")

    def test_start_pagination_queue(self):
        # Mock the search method to return a response with 3 results
        self.pds.search = MagicMock(return_value={'results': [1, 2, 3]})

        # Start a pagination session with type='queue'
        self.pds.start_pagination(query='test', type='queue')

        # Check that the result queue has 1 item
        self.assertEqual(self.pds.result_queue.qsize(), 1)

    def test_start_pagination_list(self):
        # Mock the search method to return a response with 3 results
        self.pds.search = MagicMock(return_value={'results': [1, 2, 3]})

        # Start a pagination session with type='list'
        self.pds.start_pagination(query='test', type='list')

        # Check that the results list has 3 items
        self.assertEqual(len(self.pds.results), 3)

    def test_start_pagination_invalid_type(self):
        # Start a pagination session with an invalid type
        with self.assertRaises(ValueError):
            self.pds.start_pagination(query='test', type='invalid')

if __name__ == '__main__':
    unittest.main()