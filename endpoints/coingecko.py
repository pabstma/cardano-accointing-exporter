from datetime import datetime, timezone
from functools import lru_cache
from typing import List, Dict

import requests_cache

import config
from config import COINGECKO_BASE_API
from shared import api_handler


@lru_cache(maxsize=config.cache_limit)
def get_price_history_for_token(token: str, currency: str) -> Dict[datetime, float]:
    with requests_cache.disabled():
        price_history = api_handler.get_request_api(COINGECKO_BASE_API + 'coins/' + token + '/market_chart?vs_currency=' + currency + '&days=max', '{}').json()['prices']
    prices = [tuple(x) for x in price_history]
    result = {}
    for (key, value) in prices:
        # convert unix timestamp to date
        date = datetime.fromtimestamp(key / 1000.0).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        if date not in result:
            result[date] = value
    return result


def get_price_for_token_at_date(token: str, date: datetime, currency: str) -> float:
    return get_price_history_for_token(token, currency)[date.replace(hour=0, minute=0, second=0, microsecond=0)]


def get_supported_vs_currencies() -> List[str]:
    currencies = api_handler.get_request_api(COINGECKO_BASE_API + 'simple/supported_vs_currencies', '{}').json()
    return currencies
