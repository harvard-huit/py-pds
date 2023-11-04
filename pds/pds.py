import requests
import json
import logging
from dotmap import DotMap

logger = logging.getLogger(__name__)

class People:
    def __init__(self, apikey, batch_size=50, retries=3, environment='prod'):
        if apikey == None:
            raise Exception("Error: apikey required")

        self.apikey = apikey
        self.last_query = None
        self.response = {}
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

    def __str__(self):
        return str(self.response)
    def __repr__(self):
        return str(self.response)

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


    def search(self, query='', paginate=False) -> dict:
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

        payload = query

        #calling PDS api
        for i in range(self.retries):
            try:
                response = requests.post(self.pds_url, 
                    headers = headers,
                    params = params,
                    data =  json.dumps(payload))
                if(response.status_code == 200):
                    break
                elif(response.status_code <= 400 and response.status_code < 500):
                    # we don't need to retry client errors
                    raise Exception(f"Error: failure with response from PDS: {response.status_code}:{response.text}")   
                else:
                    logger.warning(f"WARNING: PDS returned a non-200 response: {response.status_code}:{response.text} for query: {query}")
                    logger.warning(f"WARNING: retrying {i+1} of {self.retries}")         

                if 'count' in response.json():
                    if(response.json()['count'] < 1):
                        logger.warning(f"PDS returned no results for: {query}")

                    self.count = response.json()['count']
                    self.total_count = response.json()['total_count']


            except Exception as e:
                logger.warning(f"WARNING: PDS returned an exception: {e} for query: {query}")
                logger.warning(f"WARNING: retrying {i+1} of {self.retries}")


        if 'session_id' in response.json():
            self.session_id = response.json()['session_id']
        
        self.last_query = query
        self.response = response.json()
        return self.response

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
                    break
                elif(response.status_code <= 400 and response.status_code < 500):
                    # we don't need to retry client errors
                    raise Exception(f"Error: failure with response from PDS: {response.status_code}:{response.text}")   
                else:
                    logger.warning(f"WARNING: PDS returned a non-200 response: {response.status_code}:{response.text} for query: {self.last_query}")
                    logger.warning(f"WARNING: retrying {i+1} of {self.retries}")      

                if 'count' in response.json():
                    if(response.json()['count'] < 1):
                        # this isn't a lack of results, it could be the end of the pages
                        return {}

                    self.count = response.json()['count']
                    self.total_count = response.json()['total_count']


            except Exception as e:
                logger.warning(f"WARNING: PDS returned an exception: {e} for query: {self.last_query}")
                logger.warning(f"WARNING: retrying {i+1} of {self.retries}")
              

        if 'session_id' in response.json():
            self.session_id = response.json()['session_id']

        self.response = response.json()
        return self.response
