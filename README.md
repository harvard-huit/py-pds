
## Person Data Service Python Library

This library is meant to serve as a convenience library to using the PDS. This came about from me rewriting the same code over and over. 

### Installation

#### Artifactory

This is hosted in artifactory.huit. You can directly install it with pip with:
```
pip install --index-url https://artifactory.huit.harvard.edu/artifactory/api/pypi/ats-python/simple pds
```

If you have the dependency in a requirements file, the `extra-index-url`` needs to be set up in the config. Note that you should set `extra-index-url` and NOT `index-url` as that will overwrite your index (probably pypi.org).
```
pip config set global.extra-index-url https://artifactory.huit.harvard.edu/artifactory/api/pypi/ats-python/simple
pip install -r requirements.txt
```

#### Directly from source

While it's not recommended, you can also pull directly from source with the following:

If you're a member of github.huit, this can be installed *locally*, directly from this repository with:
```
pip install git+https://github.huit.harvard.edu/HUIT/py-pds.git@v1.1.0
```

However, if this is being deployed, you can't do that. (A docker image building this will most likely not be authenticated to github.huit as you are locally.) This will eventually make it to artifactory, but right now, it is being mirrored on public github, so you can use this in your `requirements.txt`:
```
pds @ git+https://github.com/harvard-huit/py-pds@v1.1.0
```

### Usage

Create a People object using an apikey and what you want your batch size to be (if you're paginating). 

```py
import pds

pds_api = pds.People(apikey='12345', batch=50)
```

Default batch is 50 and this won't work without a valid apikey, so if you don't have one, head over here: https://portal.apis.huit.harvard.edu/docs/ats-person-v3/1/overview

Once that object is created, there are only a couple of methods for it. 

### Methods

 - [search](README.md#search): the core search method
 - [next](README.md#next): the manual method to make a call for next result in a pagination session
 - [start_pagination](README.md#Asynchronous+Pagination): create a pagination session to page through results
 - [wait_for_pagination](README.md#Asynchronous+Pagination): blocks processing until pagination is done. Synonymous to using `start_pagination` with the `wait` parameter
 - [next_page_results](README.md#Asynchronous+Pagination): gets next batch of results


#### search

This is the core function. It takes a dict `query` and an optional boolean `paginate`, 

```py
import pds

pds_api = pds.People(apikey-'12345', batch=50)
people = pds_api.search(query={
    "fields": [
        "univid"
    ],
    "conditions": {
        "names.name": "jazahn"
    }
})

total_results = people['total_results']
results = people['results']
```


#### make_people

This just converts some results into dotmaps, which can _sometimes_ make referencing values easier.  

```py
import pds

pds_api = pds.People(apikey-'12345', batch=50)
people = pds_api.search(query={
    "fields": [
        "univid"
    ],
    "conditions": {
        "names.name": "jazahn"
    }
})

total_results = people['total_results']
results = people['results']

dotmapped_people = pds_api.make_people(results)
print(dotmapped_people[0].univid)
```

#### next

Next is probably the reason you're using this library. This helps simplify pagination. Simply make a search call with the `paginate` boolean set to true and then you can call `next()` to get the next set. 

```py
import pds

pds_api = pds.People(apikey-'12345', batch=50)
response = pds_api.search(query={
    "fields": [
        "univid"
    ],
    "conditions": {
        "names.name": "jazahn"
    }
}, pagination=True)

total_results = response['total_results']
results = response['results']

while(True):
    response = pds_api.next()
    if not response:
        break

    results = response['results']
    # do something with results
```

### Pagination

The pagination process has a few ways it can be used. Synchronously, asynchronously and producing a queue of batches or a list. 

Using `next()` is good, but this pagination process was created with async operations in mind. For example, if you're processing 100k records, you'll be getting a max of 1000 records and if you're doing something with them that might take longer than 3 min, the PDS pagination process will time out before you get to call `next()` again, which would force you to start it over again. 

#### Synchronous Pagination

Please note that getting a lot of records and holding them before processing could have an effect on memory. If you have the memory to hold all the records you're getting, you can just do this:

```
import pds

people = pds.People(apikey=os.getenv('APIKEY'), batch_size=1000)

query = {
    "fields": ["univid"],
    "conditions": {
        "names.name": "john"
    }
}

people.start_pagination(query, type='list', wait=True)
people_list = people.results
```

That will give you the full list.

#### Asynchronous Pagination

```py
import pds

people = pds.People(apikey=os.getenv('APIKEY'), batch_size=1000)

query = {
    "fields": ["univid"],
    "conditions": {
        "names.name": "john"
    }
}


try:
    people.start_pagination(query)

    results = people.next_page_results()
    logger.info(f"doing something with this batch of {len(results)} results")
    if len(results) < 1 and not people.is_paginating:
        break
        
except Exception as e:
    logger.error(f"Something went wrong with the processing. {e}")
```