import requests
import json
import logging
import threading
import queue
import time

from dotmap import DotMap

logger = logging.getLogger(__name__)

class People:
    """
    A class for interacting with the Harvard Person Data Service (PDS) API.

    Attributes:
    - apikey (str): The API key for accessing the PDS API.
    - batch_size (int): The number of results to return per API call.
    - retries (int): The number of times to retry an API call if it fails.
    - environment (str): The environment to use for the PDS API (dev, test, stage, or prod).
    - is_paginating (bool): Whether or not the API is currently paginating results.
    - pagination_type (str): The type of pagination to use (queue or session).
    - result_queue (queue.Queue): A queue for storing paginated results.
    - max_size (int): The maximum number of results to return.
    - results (list): A list of all results returned by the API.
    - count (int): The number of results returned by the last API call.
    - total_count (int): The total number of results available for the last API call.
    - paginate (bool): Whether or not to paginate results.
    - session_id (str): The ID of the current pagination session.
    """

    def __init__(self, apikey, batch_size=50, retries=3, environment='prod'):
        """
        Initializes a new instance of the People class.

        Args:
        - apikey (str): The API key for accessing the PDS API.
        - batch_size (int): The number of results to return per API call.
        - retries (int): The number of times to retry an API call if it fails.
        - environment (str): The environment to use for the PDS API (dev, test, stage, or prod).
        """
        if apikey is None:
            raise Exception("Error: apikey required")

        self.apikey = apikey
        self.last_query = None

        self.is_paginating = False
        self.pagination_type = 'queue' 
        self.result_queue = queue.Queue()
        self.max_size = 50000
        self.results = []

        self.count = 0
        self.total_count = 0
        self.batch_size = batch_size
        self.retries = retries
        if environment == 'dev':
            self.pds_url = "https://go.dev.apis.huit.harvard.edu/ats/person/v3/search"
        if environment == 'test':
            self.pds_url = "https://go.stage.apis.huit.harvard.edu/ats/person/v3/search?env=test"
        if environment == 'stage':
            self.pds_url = "https://go.stage.apis.huit.harvard.edu/ats/person/v3/search"
        else:
            # default should be prod
            self.pds_url = "https://go.apis.huit.harvard.edu/ats/person/v3/search"
        
        self.paginate = False
        self.session_id = None

    def get_people(self, query=''):
        """
        Searches the PDS API for people matching the given query.

        Args:
        - query (str): The query to search for.

        Returns:
        - A list of DotMap objects representing the people matching the query.
        """
        response = self.search(query=query)
        results = response['results']
        people = []
        if response['count'] > 0:
            for result in results:
                # dotmap allows us to access the items as names.name
                person = DotMap(result)
                people.append(person)
        return people

    def make_people(self, results):
        """
        Converts a list of PDS API results into a list of DotMap objects representing people.

        Args:
        - results (list): A list of PDS API results.

        Returns:
        - A list of DotMap objects representing the people in the results.
        """
        people = []
        for result in results:
            # dotmap allows us to access the items as names.name
            person = DotMap(result)
            people.append(person)
        return people


    def pds_request(self, url:str, headers:dict={}, params:dict={}, payload:dict={}):
        """
        Sends a request to the PDS API.

        Args:
        - url (str): The URL to send the request to.
        - headers (dict): The headers to include in the request.
        - params (dict): The query parameters to include in the request.
        - payload (dict): The payload to include in the request.

        Returns:
        - The response from the API.
        """
        logger = logging.getLogger(__name__)

        for i in range(self.retries):
            try:
                response = requests.post(url, 
                    headers = headers,
                    params = params,
                    data =  json.dumps(payload))
                if(response.status_code == 200):
                    if 'count' in response.json():
                        if(response.json()['count'] < 1 and payload):
                            if payload:
                                logger.warning(f"PDS returned no results for: {payload}")
                        

                        self.count = response.json()['count']
                        self.total_count = response.json()['total_count']

                        if 'session_id' in response.json():
                            self.session_id = response.json()['session_id']

                        return response

                elif(response.status_code >= 400 and response.status_code < 500):
                    # we don't need to retry client errors, right?
                    raise Exception(f"Error: failure with response from PDS: {response.status_code}:{response.text}")   
                else:
                    if (i+1) >= self.retries:
                        raise requests.exceptions.RetryError(f"Max retires ({self.retries}) reached on PDS.")
                    else:
                        logger.warning(f"WARNING: PDS returned a non-200 response: {response.status_code}:{response.text} for query: {self.last_query}")
                        logger.warning(f"WARNING: retrying {i+1} of {self.retries}")         
        
            except requests.exceptions.RetryError as re:
                raise re
            except Exception as e:
                logger.warning(f"WARNING: PDS returned an exception: {e} for query: {self.last_query}")
                logger.warning(f"WARNING: retrying {i+1} of {self.retries}")


    def search(self, query:str='', paginate: bool=False, session_timeout: int=None) -> dict:
        """
        Searches the PDS API for people matching the given query.

        Args:
        - query (str): The query to search for.
        - paginate (bool): Whether or not to paginate results.
        - session_timeout (int): The number of seconds to keep the pagination session alive.

        Returns:
        - A dictionary containing the results of the search.
        """
        if self.apikey is None:
            raise Exception("Error: apikey required")
        
        self.paginate = paginate
        self.session_id = None

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.apikey
        }

        params = {
            "size": self.batch_size
        }
        if paginate:
            self.paginate = True
            params['paginate'] = True
            if isinstance(session_timeout, int):
                params['session_timeout'] = session_timeout

        payload = query

        #calling PDS api
        response = self.pds_request(self.pds_url, headers, params, payload)
        
        self.last_query = query
        try: 
            return response.json()
        except AttributeError as ar:
            return {}

    def next(self) -> dict:
        """
        Gets the next page of results from the current pagination session.

        Returns:
        - A dictionary containing the next page of results.
        """
        if self.session_id is None:
            logger.warning(f"WARNING: trying to paginate with no session_id available.")
            return {}

        if self.apikey is None:
            raise Exception("Error: apikey required")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.apikey
        }

        #calling PDS api      
        next_url = f"{self.pds_url}/{self.session_id}"
        response = self.pds_request(next_url, headers)

        try: 
            return response.json()
        except AttributeError as ar:
            return {}

    def start_pagination(self, query:str='', type:str=None, wait:bool=False, max_size:int=None):
        """
        Starts a new pagination session.

        Args:
        - query (str): The query to search for.
        - type (str): The type of pagination to use (queue or session).
        - wait (bool): Whether or not to wait for the pagination session to complete.
        - max_size (int): The maximum number of results to return.
        """

        if max_size and not wait:
            self.max_size = max_size

        if type:
            self.pagination_type = type

        # do the first call
        response = self.search(query, paginate=True)

        if self.pagination_type == 'queue':
            self.result_queue.put(response['results'])
        elif self.pagination_type == 'list':
            self.results += response['results']
        else:
            raise ValueError(f"Invalid type for pagination: ({self.pagination_type})")

        if len(response['results']) < self.batch_size:
            logger.debug(f"No need to paginate.")
        else:
            self.pagination_thread = threading.Thread(target=self.pagination, args=())
            self.pagination_thread.start()

            if wait:
                self.wait_for_pagination()
    
    def pagination(self):
        self.is_paginating = True
        gotten_results = self.batch_size
        count = 2
        while True:
            try:
                if self.pagination_type == 'list':
                    current_results = len(self.results)
                elif self.pagination_type == 'queue':
                    current_results = self.batch_size * self.result_queue.qsize()
                else:
                    raise ValueError(f"Invalid pagination type: {self.pagination_type}")

                # if we have accumulated a backlog of results larger than the "max_size", 
                #   we should/can slow down. We can't stop as that would cause issues with pagination timeouts
                if current_results > self.max_size:
                    time.sleep(60)
                else:
                    # this sleep is necessary to not hit the 429 (rate limit)
                    time.sleep(1)
                response = self.next()
                if response is None or response is {}:
                    break
                results = response['results']
                total_results = response['total_count']

                gotten_results += len(results)
                logger.debug(f"{len(results)} results in page {count} -- {gotten_results}/{total_results}")

                count += 1
                if self.pagination_type == 'queue':
                    self.result_queue.put(results)
                elif self.pagination_type == 'list':
                    self.results += results
                else:
                    raise ValueError(f"Invalid type for pagination: ({self.pagination_type})")
                
                if len(results) < self.batch_size:
                    logger.debug(f"Pagination reached end.")
                    self.is_paginating = False
                    return True
            except Exception as e:
                logger.error(f"Failure in pagination: {e}")
                break
        
        self.is_paginating = False
        return False

    def wait_for_pagination(self) -> bool:
        # blocks the thread until pagination is finished
        # returns true if there's mroe to do and false if everything is already processed

        # we don't care about the max_size slowdown if we're just accumulating everything
        self.max_size = None

        self.pagination_thread.join()

        logger.debug(f"Finished thread")
        if not self.result_queue.empty():
            remaining = self.result_queue.qsize()
            logger.debug(f"There are still {remaining} remaining queue batches.")
            return True
        if len(self.results) > 0:
            remaining = len(self.results)
            logger.debug(f"There are still {remaining} remaining records in the results list.")
            return True
        
        return False
            
    def next_page_results(self):
        if self.pagination_type == 'queue':
            if self.result_queue.qsize() > 0:
                results = self.result_queue.get()
                self.result_queue.task_done()
            else:
                return []
        elif self.pagination_type == 'list': 
            results = self.results[:self.batch_size]
            self.results = self.results[self.batch_size:]
        return results





