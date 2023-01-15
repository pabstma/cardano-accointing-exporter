import time
from datetime import timezone
from time import sleep

import requests as requests
from requests import Response

import config
from config import BLOCKFROST_BASE_API
from shared.representations import *

headers = None


# HTTP header
def init_header() -> None:
    global headers
    headers = {
        'project_id': config.PROJECT_ID
    }


# Check backend health
def check_health() -> bool:
    health = __request_api(BLOCKFROST_BASE_API + 'health').json()['is_healthy']
    return health


# Check project id
def check_project_id() -> bool:
    __request_api(BLOCKFROST_BASE_API)
    return True


def get_addresses_for_account(stake_addr: str) -> List[Address]:
    # Get all addresses for the given stake key
    page = 1
    addresses_r = True
    addresses = []
    while addresses_r:
        addresses_r = __request_api(BLOCKFROST_BASE_API + 'accounts/' + stake_addr + '/addresses' + '?page=' + str(page)).json()
        page += 1
        for address in addresses_r:
            addresses.append(Address(address['address'], [], []))
    return addresses


def get_controlled_amount_for_account(stake_addr: str) -> int:
    return int(__request_api(BLOCKFROST_BASE_API + 'accounts/' + stake_addr).json()['controlled_amount'])


def get_amount_for_address(addr: str) -> int:
    return int(__request_api(BLOCKFROST_BASE_API + 'addresses/' + addr).json()['amount'][0]['quantity'])


def get_active_status_for_account(stake_addr: str) -> bool:
    return bool(__request_api(BLOCKFROST_BASE_API + 'accounts/' + stake_addr).json()['active'])


def get_stake_addr_for_addr(addr: str) -> str:
    return str(__request_api(BLOCKFROST_BASE_API + 'addresses/' + addr).json()['stake_address'])


def get_transaction_history_for_addr(addr: str, start_time: datetime, end_time: datetime) -> List[Transaction]:
    txs_history = []
    txs = []
    page = 1
    addr_txs_r = True
    while addr_txs_r:
        addr_txs_r = __request_api(BLOCKFROST_BASE_API + 'addresses/' + addr + '/transactions' + '?page=' + str(page)).json()
        page += 1
        config.elapsed_time = time.time() - config.start_time
        if len(addr_txs_r) > 0:
            config.tx_counter += len(addr_txs_r)
            if start_time <= datetime.fromtimestamp(addr_txs_r[-1]['block_time'], timezone.utc):
                if datetime.fromtimestamp(addr_txs_r[0]['block_time'], timezone.utc) <= end_time:
                    txs_history.append(addr_txs_r)
                else:
                    break

    txs_history = [item for sublist in txs_history for item in sublist]

    if len(txs_history) > 0:
        for tx in txs_history:
            if start_time <= datetime.fromtimestamp(tx['block_time'], timezone.utc) <= end_time:
                tx_details = __get_detailed_tx_information(tx['tx_hash'])
                txs.append(Transaction(tx['tx_hash'],
                                       datetime.fromtimestamp(tx['block_time'], timezone.utc),
                                       __get_output_amount_for_transaction(tx['tx_hash']),
                                       int(tx_details['fees']),
                                       0,
                                       0,
                                       int(tx_details['utxo_count']),
                                       int(tx_details['withdrawal_count']),
                                       int(tx_details['mir_cert_count']),
                                       int(tx_details['delegation_count']),
                                       int(tx_details['stake_cert_count']),
                                       int(tx_details['pool_update_count']),
                                       int(tx_details['pool_retire_count']),
                                       __get_inputs_for_transaction(tx['tx_hash']),
                                       __get_outputs_for_transaction(tx['tx_hash'])))

    return txs


# Function to request the api with simple builtin retry
def __request_api(url: str) -> Response:
    retries = 0
    response_code = None
    while response_code != 200 and retries <= 20:
        if retries > 0:
            sleep(retries * 5)
            print('Response code was: ' + str(response_code) + ' -> Retrying ' + str(retries) + '...')
        response = requests.get(url, headers=headers)
        response_code = response.status_code
        __check_cached(response)
        config.request_time = time.time()
        retries += 1
    if response_code != 200:
        print('Response code was: ' + str(response_code) + ' -> Exiting after 20 retries...')
        exit(1)
        __check_content(response)

    return response


# Function to check if the response was cached; needed for limiting api requests
def __check_cached(response: Response) -> None:
    config.elapsed_time = time.time() - config.start_time
    elapsed_since_request = time.time() - config.request_time
    if not getattr(response, 'from_cache', False):
        config.api_counter += 1
        if config.elapsed_time > 5 and elapsed_since_request < 0.1 and (config.api_counter % 1100) > 600:
            sleep(0.1 - elapsed_since_request)
    else:
        config.cache_counter += 1


# Check if the received response content type is json
def __check_content(response: Response) -> None:
    if response is not None:
        if 'json' not in response.headers.get('Content-Type'):
            print('The content type of the received data is not json but ' + response.headers)
            exit(1)
    else:
        print('No response was received -> Exiting...')
        exit(1)


def get_withdrawal_for_transaction(tx_hash: str) -> Response:
    return __request_api(BLOCKFROST_BASE_API + 'txs/' + tx_hash + '/withdrawals')


def __get_output_amount_for_transaction(tx_hash: str) -> List[Tuple[str, int]]:
    output_amount = __request_api(BLOCKFROST_BASE_API + 'txs/' + tx_hash).json()['output_amount']
    output_amounts = []
    for o in output_amount:
        output_amounts.append((o['unit'], int(o['quantity'])))
    return output_amounts


def __get_detailed_tx_information(tx_hash: str):
    return __request_api(BLOCKFROST_BASE_API + 'txs/' + tx_hash).json()


def __get_inputs_for_transaction(tx_hash: str) -> List[Input]:
    tx_utxos_r = __request_api(BLOCKFROST_BASE_API + 'txs/' + tx_hash + '/utxos').json()
    tx_utxos = []

    for tx_input in tx_utxos_r['inputs']:
        tx_utxos.append(Input(tx_input['address'], [(tx_input['amount'][0]['unit'], int(tx_input['amount'][0]['quantity']))], tx_hash,
                              tx_input['output_index'], tx_input['collateral']))

    return tx_utxos


def __get_outputs_for_transaction(tx_hash: str) -> List[Output]:
    tx_utxos_r = __request_api(BLOCKFROST_BASE_API + 'txs/' + tx_hash + '/utxos').json()
    tx_utxos = []

    for tx_output in tx_utxos_r['outputs']:
        tx_utxos.append(Output(tx_output['address'], [(tx_output['amount'][0]['unit'], int(tx_output['amount'][0]['quantity']))], tx_hash,
                               tx_output['output_index'], tx_output['collateral']))

    return tx_utxos
