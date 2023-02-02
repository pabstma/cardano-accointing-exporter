import json
import time
from datetime import timezone, datetime
from typing import List, Tuple

from requests import Response

import config
from config import BLOCKFROST_BASE_API
from shared import api_handler
from shared.representations import Address, Transaction, Input, Output

headers = ''


# HTTP header
def init_header() -> None:
    global headers
    headers = json.dumps({'project_id': config.PROJECT_ID})


# Check backend health
def check_health() -> bool:
    health = api_handler.get_request_api(BLOCKFROST_BASE_API + 'health', headers).json()['is_healthy']
    return health


# Check project id
def check_project_id() -> bool:
    api_handler.get_request_api(BLOCKFROST_BASE_API, headers)
    return True


def get_addresses_for_account(stake_addr: str) -> List[Address]:
    # Get all addresses for the given stake key
    page = 1
    addresses_r = Response
    addresses = []
    while addresses_r:
        addresses_r = api_handler.get_request_api(BLOCKFROST_BASE_API + 'accounts/' + stake_addr + '/addresses' + '?page=' + str(page), headers).json()
        page += 1
        for address in addresses_r:
            addresses.append(Address(address['address'], [], {}))

    return addresses


def get_controlled_amount_for_account(stake_addr: str) -> int:
    return int(api_handler.get_request_api(BLOCKFROST_BASE_API + 'accounts/' + stake_addr, headers).json()['controlled_amount'])


def get_amount_for_address(addr: str) -> int:
    return int(api_handler.get_request_api(BLOCKFROST_BASE_API + 'addresses/' + addr, headers).json()['amount'][0]['quantity'])


def get_active_status_for_account(stake_addr: str) -> bool:
    return bool(api_handler.get_request_api(BLOCKFROST_BASE_API + 'accounts/' + stake_addr, headers).json()['active'])


def get_stake_addr_for_addr(addr: str) -> str:
    return str(api_handler.get_request_api(BLOCKFROST_BASE_API + 'addresses/' + addr, headers).json()['stake_address'])


def get_transaction_history_for_addr(addr: str, start_time: datetime, end_time: datetime) -> List[Transaction]:
    txs_history = []
    txs = []
    page = 1
    addr_txs_r = True
    print('---- Request all transaction hashes')
    while addr_txs_r:
        addr_txs_r = api_handler.get_request_api(BLOCKFROST_BASE_API + 'addresses/' + addr + '/transactions' + '?page=' + str(page), headers).json()
        page += 1
        config.elapsed_time = time.time() - config.start_time
        if len(addr_txs_r) > 0:

            if start_time <= datetime.fromtimestamp(addr_txs_r[-1]['block_time'], timezone.utc):
                if datetime.fromtimestamp(addr_txs_r[0]['block_time'], timezone.utc) <= end_time:
                    txs_history.append(addr_txs_r)
                else:
                    break

    txs_history = [item for sublist in txs_history for item in sublist]

    print('---- Request detailed information for transactions')
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


def get_withdrawal_for_transaction(tx_hash: str) -> Response:
    return api_handler.get_request_api(BLOCKFROST_BASE_API + 'txs/' + tx_hash + '/withdrawals', headers)


def __get_output_amount_for_transaction(tx_hash: str) -> List[Tuple[str, int]]:
    output_amount = api_handler.get_request_api(BLOCKFROST_BASE_API + 'txs/' + tx_hash, headers).json()['output_amount']
    output_amounts = []
    for o in output_amount:
        output_amounts.append((o['unit'], int(o['quantity'])))

    return output_amounts


def __get_detailed_tx_information(tx_hash: str):
    return api_handler.get_request_api(BLOCKFROST_BASE_API + 'txs/' + tx_hash, headers).json()


def __get_inputs_for_transaction(tx_hash: str) -> List[Input]:
    tx_utxos_r = api_handler.get_request_api(BLOCKFROST_BASE_API + 'txs/' + tx_hash + '/utxos', headers).json()
    tx_utxos = []
    for tx_input in tx_utxos_r['inputs']:
        tx_utxos.append(Input(tx_input['address'], [(tx_input['amount'][0]['unit'], int(tx_input['amount'][0]['quantity']))], tx_hash,
                              tx_input['output_index'], tx_input['collateral']))

    return tx_utxos


def __get_outputs_for_transaction(tx_hash: str) -> List[Output]:
    tx_utxos_r = api_handler.get_request_api(BLOCKFROST_BASE_API + 'txs/' + tx_hash + '/utxos', headers).json()
    tx_utxos = []
    for tx_output in tx_utxos_r['outputs']:
        tx_utxos.append(Output(tx_output['address'], [(tx_output['amount'][0]['unit'], int(tx_output['amount'][0]['quantity']))], tx_hash,
                               tx_output['output_index'], tx_output['collateral']))

    return tx_utxos
