import glob
import time
from datetime import datetime

# Configuration variables
PROJECT_ID = ''
BLOCKFROST_BASE_API = 'https://cardano-mainnet.blockfrost.io/api/v0/'
KOIOS_BASE_API = 'https://api.koios.rest/api/v0/'
SHELLEY_START_EPOCH = 208
SHELLEY_START_DATETIME = datetime(2020, 7, 29, 21, 44, 51)
LINE_CLEAR = '\x1b[2K'


def init():
    # Global variables
    global api_counter
    global cache_counter
    global start_time
    global request_time
    global elapsed_time
    global calculated_wallet_counter
    global address_counter
    global calculated_address_counter
    global tx_counter
    global reward_counter
    global wallet_files
    global current_wallet
    global wallet_counter

    wallet_files = glob.glob('wallets/*.wallet')
    wallet_counter = len(wallet_files)
    api_counter = 0
    cache_counter = 0
    calculated_wallet_counter = 0
    address_counter = 0
    calculated_address_counter = 0
    tx_counter = 0
    reward_counter = 0
    start_time = time.time()
    request_time = time.time()
    elapsed_time = time.time() - start_time
