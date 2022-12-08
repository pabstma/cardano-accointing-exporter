import time
from datetime import datetime


# Configuration variables
PROJECT_ID = ''
BASE_API = 'https://cardano-mainnet.blockfrost.io/api/v0/'
SHELLEY_START_EPOCH = 208
SHELLEY_START_DATETIME = datetime(2020, 7, 29, 21, 44, 51)
CACHE_ALL = False


def init():
    # Global variables
    global api_counter
    global cache_counter
    global start_time
    global request_time
    global elapsed_time

    api_counter = 0
    cache_counter = 0
    start_time = time.time()
    request_time = time.time()
    elapsed_time = time.time() - start_time
