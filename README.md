## MOVED

Due to the weird permissions we have on Github Enterprise, this has been moved to the harvard-huit org on github.com.

https://github.com/harvard-huit/py-pds


## Person Data Service Python Library

This library is meant to serve as a convenience library to using the PDS. This came about from me rewriting the same code over and over. 

### Installation

Currently this can be installed directly from this repository with:

```
pip install git+https://github.huit.harvard.edu/HUIT/py-pds.git@v1.0.2
```

### Usage

Create a People object using an apikey and what you want your batch size to be (if you're paginating). 

```py
import pds

pds_api = pds.People(apikey='12345', batch=50)
```

Default batch is 50 and this won't work without a valid apikey, so if you don't have one, head over here: https://portal.apis.huit.harvard.edu/docs/ats-person-v3/1/overview

Once that object is created, there are only a couple of methods for it. 

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
