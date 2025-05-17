import glob
import time
from datetime import datetime
from typing import Set

# Configuration variables
PROJECT_ID = ''
BLOCKFROST_BASE_API = 'https://cardano-mainnet.blockfrost.io/api/v0/'
KOIOS_BASE_API = 'https://api.koios.rest/api/v1/'
COINGECKO_BASE_API = 'https://api.coingecko.com/api/v3/'
SHELLEY_START_EPOCH = 208
SHELLEY_START_DATETIME = datetime(2020, 7, 29, 21, 44, 51)
# Configure how long rewards and transactions should stay in cache (in seconds).
URLS_EXPIRE_AFTER = {KOIOS_BASE_API + 'account_rewards': 60 * 60 * 24 * 5,
                     BLOCKFROST_BASE_API + 'addresses/*/transactions': 60 * 60 * 24 * 1,
                     BLOCKFROST_BASE_API + 'accounts/*': 60 * 60 * 24 * 5,
                     COINGECKO_BASE_API + 'coins/*/market_chart?vs_currency=*&days=max': 60 * 60 * 24 * 1}

# Change this parameter to limit the cache size if you run out of memory (e.g. to '16000' entries)
cache_limit = None
# Change this parameter if you want to specify another subdirectory for your .wallet files
wallet_files = glob.glob('wallets/*.wallet')
# You should not need to change anything below this line
addresses = set()   # type: Set[str]
classify_internal_txs = False
api_counter = 0
ondisk_cache_counter = 0
start_time = time.time()
elapsed_time = time.time() - start_time
request_time = time.time()
