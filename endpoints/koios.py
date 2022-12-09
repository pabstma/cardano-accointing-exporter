import time
import requests as requests
import config

from time import sleep


# Function to GET request the api with simple builtin retry
def request_api(url):
    retries = 0
    response_code = None
    while response_code != 200 and retries < 20:
        if retries > 0:
            sleep(retries * 5)
            print('Response code was: ' + str(response_code) + ' -> Retrying ' + str(retries) + '...')
        response = requests.get(url)
        response_code = response.status_code
        check_cached(response)
        config.request_time = time.time()
        retries += 1
    check_content(response)
    return response

# Function to POST request the api with a specific body and simple builtin retry
def request_api(url, body):
    retries = 0
    response_code = None
    while response_code != 200 and retries < 20:
        if retries > 0:
            sleep(retries * 5)
            print('Response code was: ' + str(response_code) + ' -> Retrying ' + str(retries) + '...')
        response = requests.post(url, json=body)
        response_code = response.status_code
        check_cached(response)
        config.request_time = time.time()
        retries += 1
    check_content(response)
    return response


# Function to check if the response was cached; needed for limiting api requests
def check_cached(response):
    config.elapsed_time = time.time() - config.start_time
    elapsed_since_request = time.time() - config.request_time
    if not getattr(response, 'from_cache', False):
        config.api_counter += 1
        if config.elapsed_time > 5 and elapsed_since_request < 0.1:
            sleep(0.1 - elapsed_since_request)
    else:
        config.cache_counter += 1


# Check if the received response content type is json
def check_content(response):
    if 'json' not in response.headers.get('Content-Type'):
        print('The content type of the received data is not json but ' + response.headers)
        exit(1)
