from algoliasearch.search_client import SearchClient
from pathlib import Path
from pyfzf.pyfzf import FzfPrompt
from rich import print

import argparse
import json
import pandas as pd
import plumbum
import requests

fzf = FzfPrompt()

FZF_FILE_OPTS = "--cycle" 

algolia_app_id = 'LUA9B20G37'
algolia_api_key = 'dcc55281ffd7ba6f24c3a9b18288499b'

def get_domains_subdomains():
    ## Populate {domains:[subdomains]} dict
    url = 'https://www.coursera.org/graphqlBatch?opname=DomainGetAllQuery'
     
    headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:106.0) Gecko/20100101 Firefox/106.0' ,
            'Accept': '*/*' ,
            'Accept-Language': 'en'  ,
            'Referer': 'https://www.coursera.org/certificates/data-science' ,
            'content-type': 'application/json' ,
            'R2-APP-VERSION': '09791a29eabe8ca5ee453cb69c38c7605ab61be2' ,
            'X-Coursera-Application': 'premium-hub' ,
            'X-Coursera-Version': '09791a29eabe8ca5ee453cb69c38c7605ab61be2' ,
            'X-CSRF3-Token': '1668797255.HUO6HlUughhiQULz' ,
            'OPERATION-NAME': 'DomainGetAllQuery' ,
            'Origin': 'https://www.coursera.org' ,
            'DNT': '1' ,
            'Connection': 'keep-alive' ,
            'Sec-Fetch-Dest': 'empty' ,
            'Sec-Fetch-Mode': 'cors' ,
            'Sec-Fetch-Site': 'same-origin' ,
            'TE': 'trailers' ,
            }

    data = json.loads('[{"operationName":"DomainGetAllQuery","variables":{},"query":"query DomainGetAllQuery { DomainsV1Resource { domains: getAll { elements { id topic slug name description backgroundImageUrl subdomains { elements { id slug topic name domainId description __typename } __typename } __typename } __typename } __typename }}"}]')

    response = requests.post(url, headers=headers, data = json.dumps(data))
    data = response.json()[0]["data"]["DomainsV1Resource"]["domains"]["elements"]
    domains_subdomains = {d["topic"]: [ x["topic"] for x in d["subdomains"]["elements"] ] for d in data }

    return domains_subdomains

def main(): 

    ap = argparse.ArgumentParser()
    ap.add_argument('-c', '--cache-dir', default=f"~/.cache/{__name__}")
    args = ap.parse_args()

    ## For eventual use
    entityTypeDescriptions = [
            'Courses',
            'Guided Projects',
            'Specializations',
            'Projects',
            'Professional Certificates',
            'Degrees',
            'MasterTrack® Certificates',
            'University Certificates',
            'Graduate Certificates',
            'Postgraduate Diploma'
            ]

    entityTypeDescription = 'Courses'

    domains_subdomains = get_domains_subdomains()

    try:
        topic = fzf.prompt(domains_subdomains, FZF_FILE_OPTS)[0]
    except plumbum.commands.processes.ProcessExecutionError: #type:ignore
        return

    # NOTE: We are restricted by the number of returned entities (1000).
    # Limiting results by entityTypeDescription helps here, apart from being what was requested.
    filter = f"topic: '{topic}' AND entityTypeDescription: '{entityTypeDescription}'"

    cache_dir = Path(args.cache_dir)
    cache_file = cache_dir / f'{entityTypeDescription} - {topic}.json'

    if Path(cache_file).is_file(): 
        print(f"Loading data from cache file: {cache_file}")
        df = pd.read_json(cache_file, orient='records')
    else: 
        print(f"No cache_file found. Fetching data from API")

        client = SearchClient.create(algolia_app_id, algolia_api_key)
        index = client.init_index("test_products") # All products ever
        # index = client.init_index("prod_all_launched_products_term_optimization")

        # NOTE: Potential to paginate, but using filters limits total results to 1000
        res = index.search('', {
            'hitsPerPage': 1000,
            'page': 0,
            'filters': filter 
            })

        if len(res['hits']) == 1000: 
            print("Results overflowing! More actual results than fetchable!")

        with open(cache_file, 'w') as outfile:
            json.dump(res['hits'], outfile)

        df = pd.DataFrame.from_dict(res['hits'])

    # Extract description as a df column
    df2 = df['_snippetResult'].apply(pd.Series)['description'].apply(pd.Series)
    df = df.join(pd.DataFrame(df2))
    df.rename(columns = {'value': 'description'}, inplace=True)

    output_columns = ['name', 'partners', 'enrollments', 'numProductRatings', 'description']
    df[output_columns].to_csv(cache_file.with_suffix('.csv'), index=False)

    # TODO: UTF-8 Charset?

if __name__ == "__main__":
    main()
