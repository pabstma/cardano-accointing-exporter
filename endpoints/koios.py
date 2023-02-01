import json
from datetime import timedelta, timezone

from config import SHELLEY_START_EPOCH, SHELLEY_START_DATETIME, KOIOS_BASE_API
from shared import api_handler
from shared.representations import *


def get_reward_history_for_account(stake_addr: str, start_time: datetime, end_time: datetime) -> List[Reward]:
    reward_history = []
    rewards = []
    offset = 0
    new_results = True
    while new_results:
        body = {"_stake_addresses": [stake_addr]}
        reward_history_r = api_handler.post_request_api(KOIOS_BASE_API + 'account_rewards' + '?offset=' + str(offset), json.dumps(body))
        new_results = reward_history_r.json()
        reward_history.append(reward_history_r.json())
        offset += 1000

    reward_history = [item for sublist in reward_history for item in sublist]

    if len(reward_history) > 0:
        for reward in reward_history[0]['rewards']:
            epoch = reward['earned_epoch']
            datetime_delta = (epoch - SHELLEY_START_EPOCH) * 5
            reward_time = (SHELLEY_START_DATETIME + timedelta(days=datetime_delta) + timedelta(days=10)).replace(tzinfo=timezone.utc)
            reward_type = reward['type']
            pool_id = reward['pool_id']
            if start_time <= reward_time <= end_time:
                rewards.append(Reward(epoch, reward_time, reward['amount'], pool_id, reward_type))

    return rewards
