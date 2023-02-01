# Function to request the api with simple builtin retry
import json
import time
from functools import lru_cache
from time import sleep

import requests as requests
from requests import Response

import config


@lru_cache(maxsize=config.cache_limit)
def get_request_api(url: str, headers: str) -> Response:
    retries = 0
    response_code = None
    while response_code != 200 and retries <= 20:
        if retries > 0:
            sleep(retries * 5)
            print('Response code was: ' + str(response_code) + ' -> Retrying ' + str(retries) + '...')
        response = requests.get(url, headers=json.loads(headers))
        response_code = response.status_code
        __check_cached(response)
        config.request_time = time.time()
        retries += 1
    if response_code != 200:
        print('Response code was: ' + str(response_code) + ' -> Exiting after 20 retries...')
        exit(1)
    __check_content(response)
    return response


@lru_cache(maxsize=config.cache_limit)
def post_request_api(url: str, body: str) -> Response:
    retries = 0
    response_code = None
    while response_code != 200 and retries < 20:
        if retries > 0:
            sleep(retries * 5)
            print('Response code was: ' + str(response_code) + ' -> Retrying ' + str(retries) + '...')
        response = requests.post(url, json=json.loads(body))
        response_code = response.status_code
        __check_cached(response)
        config.request_time = time.time()
        retries += 1
    if response_code != 200:
        print('Response code was: ' + str(response_code) + ' -> Exiting after 20 retries...')
        exit(1)
    __check_content(response)
    return response


def get_lru_cache_hit_counter() -> int:
    return get_request_api.cache_info().hits + post_request_api.cache_info().hits


# Function to check if the response was cached; needed for limiting api requests
def __check_cached(response: Response) -> None:
    config.elapsed_time = time.time() - config.start_time
    elapsed_since_request = time.time() - config.request_time
    if not getattr(response, 'from_cache', False):
        config.api_counter += 1
        if config.elapsed_time > 5 and elapsed_since_request < 0.1:
            sleep(0.1 - elapsed_since_request)
    else:
        config.ondisk_cache_counter += 1


# Check if the received response content type is json
def __check_content(response: Response) -> None:
    if response is not None:
        if 'json' not in response.headers.get('Content-Type'):
            print('The content type of the received data is not json but ' + response.headers)
            exit(1)
    else:
        print('No response was received -> Exiting...')
        exit(1)
