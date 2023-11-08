import requests
import json
import logging
import threading
import queue
import time

from dotmap import DotMap

logger = logging.getLogger(__name__)

class People:
    def __init__(self, apikey, batch_size=50, retries=3, environment='prod'):
        if apikey == None:
            raise Exception("Error: apikey required")

        self.apikey = apikey
        self.last_query = None
        # self.response = {}

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
        people = []
        for result in results:
            # dotmap allows us to access the items as names.name
            person = DotMap(result)
            people.append(person)
        return people


    def search(self, query:str='', paginate: bool=False, session_timeout: int=None) -> dict:
        if self.apikey == None:
            raise Exception("Error: apikey required")
        
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
        for i in range(self.retries):
            try:
                response = requests.post(self.pds_url, 
                    headers = headers,
                    params = params,
                    data =  json.dumps(payload))
                if(response.status_code == 200):
                    if 'count' in response.json():
                        if(response.json()['count'] < 1):
                            logger.warning(f"PDS returned no results for: {query}")

                        self.count = response.json()['count']
                        self.total_count = response.json()['total_count']

                    break
                elif(response.status_code >= 400 and response.status_code < 500):
                    # we don't need to retry client errors
                    raise Exception(f"Error: failure with response from PDS: {response.status_code}:{response.text}")   
                else:
                    logger.warning(f"WARNING: PDS returned a non-200 response: {response.status_code}:{response.text} for query: {query}")
                    logger.warning(f"WARNING: retrying {i+1} of {self.retries}")         

            except Exception as e:
                logger.warning(f"WARNING: PDS returned an exception: {e} for query: {query}")
                logger.warning(f"WARNING: retrying {i+1} of {self.retries}")


        if 'session_id' in response.json():
            self.session_id = response.json()['session_id']
        
        self.last_query = query
        return response.json()

    def next(self) -> dict:
        if self.session_id is None:
            logger.warning(f"WARNING: trying to paginate with no session_id available.")
            return []

        if self.apikey == None:
            raise Exception("Error: apikey required")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.apikey
        }

        #calling PDS api      
        for i in range(self.retries):
            try:
                response = requests.post(self.pds_url + "/" + self.session_id, 
                    headers = headers)
                if(response.status_code == 200):
                    if 'count' in response.json():
                        if(response.json()['count'] < 1):
                            # this isn't a lack of results, it could be the end of the pages
                            return {}

                        self.count = response.json()['count']
                        self.total_count = response.json()['total_count']

                    break
                elif(response.status_code <= 400 and response.status_code < 500):
                    # we don't need to retry client errors
                    raise Exception(f"Error: failure with response from PDS: {response.status_code}:{response.text}")   
                else:
                    logger.warning(f"WARNING: PDS returned a non-200 response: {response.status_code}:{response.text} for query: {self.last_query}")
                    logger.warning(f"WARNING: retrying {i+1} of {self.retries}")      


            except Exception as e:
                logger.warning(f"WARNING: PDS returned an exception: {e} for query: {self.last_query}")
                logger.warning(f"WARNING: retrying {i+1} of {self.retries}")
              

        if 'session_id' in response.json():
            self.session_id = response.json()['session_id']

        return response.json()

    def start_pagination(self, query:str='', type:str=None, wait:bool=False, max_size:int=None):
        # Starts a pagination thread that will run through all results
        # adding them to either a 'queue' or a 'list'
        # max_size is the max we're allowing to be stored (cannot work with wait=True)

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
                # this sleep is necessary to not hit the 429 (rate limit)
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





