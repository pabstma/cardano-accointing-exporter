import csv
import glob
import time
from datetime import datetime, timedelta
from os import system, name
from time import sleep

import pandas as pd
import requests
import requests_cache

# Variables
api_key = ''
base_api = 'https://cardano-mainnet.blockfrost.io/api/v0/'
api_counter = 0
cache_counter = 0
shelley_start_epoch = 208
shelley_start_datetime = datetime(2020, 7, 29, 21, 44, 51)
wallet_files = glob.glob('wallets/*.wallet')
wallet_counter = len(wallet_files)
calculated_wallet_counter = 0
address_counter = 0
calculated_address_counter = 0
start_time = time.time()
request_time = time.time()
stake_key = None
cache_all = False

# HTTP header
headers = {
    'project_id': api_key
}

# CSV data
csv_header = ['transactionType', 'date', 'inBuyAmount', 'inBuyAsset', 'outSellAmount', 'outSellAsset',
              'feeAmount (optional)', 'feeAsset (optional)', 'classification (optional)', 'operationId (optional)','comments (optional)']


# Function to clear the terminal output
def clear():
    # for windows
    if name == 'nt':
        _ = system('cls')
    # for mac and linux(here, os.name is 'posix')
    else:
        _ = system('clear')


# Function to request the api with simple builtin retry
def request_api(url):
    global request_time
    retries = 0
    response_code = None
    while response_code != 200 and retries < 20:
        if retries > 0:
            sleep(retries * 5)
            print('Response code was: ' + str(response_code) + ' -> Retrying ' + str(retries) + '...')
        response = requests.get(url, headers=headers)
        response_code = response.status_code
        check_cached(response)
        request_time = time.time()
        retries += 1
    check_content(response)
    return response


# Function to check if the response was cached; needed for limiting api requests
def check_cached(response):
    global cache_counter
    global api_counter
    global request_time
    elapsed_time = time.time() - start_time
    elapsed_since_request = time.time() - request_time
    if not getattr(response, 'from_cache', False):
        api_counter += 1
        if elapsed_time > 5 and elapsed_since_request < 0.1:
            sleep(0.1 - elapsed_since_request)
    else:
        cache_counter += 1


# Check if the received response content type is json
def check_content(response):
    if 'json' not in response.headers.get('Content-Type'):
        print('The content type of the received data is not json but ' + response.headers)
        exit(1)


# Add row to array if it not exists
def add_row(data):
    if data not in csv_data:
        csv_data.append(data)


# Aggregate the utxos of a transaction into one
def aggregate_utxos(data):
    aggregated_utxos = []
    aggregated_data = []
    seen_deposit = []
    seen_withdraw = []

    for d in data:
        tx_type = d[0]
        tx_time = d[1]
        tx_id = d[9]
        utxos = list(filter(lambda x: x[9] == tx_id and x[0] == tx_type, data))
        aggregate = d

        for utxo in utxos:
            if tx_type == 'deposit' and utxo != d and tx_time == utxo[1] and utxo[9] not in seen_deposit:
                aggregate[2] += utxo[2]
            elif tx_type == 'withdraw' and utxo != d and tx_time == utxo[1] and utxo[9] not in seen_withdraw:
                aggregate[4] += utxo[4]

        if tx_type == 'deposit':
            seen_deposit.append(tx_id)
        if tx_type == 'withdraw':
            seen_withdraw.append(tx_id)

        if not list(filter(lambda x: x[9] == aggregate[9] and x[0] == aggregate[0] and x[1] == aggregate[1],
                           aggregated_utxos)):
            aggregated_utxos.append(aggregate)

    # Build transaction fees and deposits
    transactions = list(filter(lambda x: x[9] != '', aggregated_utxos))
    rewards = list(filter(lambda x: x[9] == '', aggregated_utxos))
    seen_transactions = []
    for transaction in transactions:
        tx_pair = list(filter(lambda x: x[9] == transaction[9], transactions))
        tx_pair = sorted(tx_pair, key=lambda x: x[0], reverse=True)

        result = None
        if transaction[9] not in seen_transactions and len(tx_pair) > 1:
            result = tx_pair[0][4] - tx_pair[1][2] - transaction[6]

        if result is not None:
            date = transaction[1]
            seen_transactions.append(transaction[9])
            fee = transaction[6]
            fee_asset = transaction[7]
            classification = ''
            operation_id = transaction[9]
            if result < 0.000001:
                result = fee
                fee = ''
                fee_asset = ''
                classification = 'fee'
            final_tx = ['withdraw', date, '', '', round(result, 5), 'ADA', fee, fee_asset, classification, operation_id]
            add_row(final_tx)
            aggregated_data.append(final_tx)
        elif transaction[9] not in seen_transactions:
            seen_transactions.append(transaction[9])
            aggregated_data.append(tx_pair[0])

    return sorted(aggregated_data + rewards, key=lambda x: datetime.strptime(x[1], '%m/%d/%Y %H:%M:%S'))


# Write csv data into file
def write_data():
    print('-- Sort calculated data')
    sorted_data = sorted(csv_data, key=lambda x: datetime.strptime(x[1], '%m/%d/%Y %H:%M:%S'))
    print('-- Aggregate UTXOs')
    aggregated_data = aggregate_utxos(sorted_data)
    print('-- Write data on drive')
    with open(filename, mode='w') as transactions_file:
        transactions_writer = csv.writer(transactions_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        transactions_writer.writerow(csv_header)
        for d in aggregated_data:
            transactions_writer.writerow(d)


def convert_csv_to_xlsx():
    csv_files = glob.glob('wallets/*.csv')
    for csv_file in csv_files:
        out = csv_file.split('.')[0] + '.xlsx'
        df = pd.read_csv(csv_file)
        df.to_excel(out, index=False)


# Start of the script itself
requests_cache.install_cache(expire_after=None)

for wallet in wallet_files:

    calculated_wallet_counter += 1
    print('Calculating wallet ' + str(calculated_wallet_counter) + ' of ' + str(wallet_counter))
    print('-- Reading wallet ' + wallet)
    csv_data = []
    stake_keys_calculated = set()
    stake_key = None
    filename = wallet.split('.')[0] + '.csv'
    wallet_file = open(wallet, 'r')
    addresses = wallet_file.readlines()
    for i in range(0, len(addresses)):
        addresses[i] = addresses[i].strip()

    if len(addresses) == 1 and addresses[0].startswith('stake1u'):
        print('---- Stake key detected ' + addresses[0])
        print('------ Get addresses for ' + addresses[0])
        page = 1
        new_results = True
        stake_key = addresses[0]
        addresses = []
        while new_results:
            addresses_r = request_api(base_api + 'accounts/' + stake_key + '/addresses' + '?page=' + str(page))
            new_results = addresses_r.json()
            page += 1
            for address in addresses_r.json():
                addresses.append(address['address'])
                print('-------- Address found ' + address['address'])

    address_counter += len(addresses)
    # Wallet Transaction History
    for address in addresses:
        global elapsed_time

        calculated_address_counter += 1
        clear()
        elapsed_time = time.time() - start_time
        print('Calculating wallet ' + str(calculated_wallet_counter) + ' of ' + str(wallet_counter) + ' - Elapsed Time: ' + str(round(elapsed_time, 2)))
        print('Calculating address ' + str(calculated_address_counter) + ' of ' + str(address_counter))

        # Address request
        addr_r = request_api(base_api + 'addresses/' + address)
        if stake_key is None:
            stake_key = addr_r.json()['stake_address']

        # Reward History
        print('-- Get reward history')
        reward_history_r = None
        reward_history = []
        if stake_key is not None:
            if stake_key not in stake_keys_calculated:
                print('---- for stake key ' + stake_key)
                with requests_cache.disabled():
                    page = 1
                    new_results = True
                    while new_results:
                        reward_history_r = request_api(base_api + 'accounts/' + stake_key + '/rewards' + '?page=' + str(page))
                        new_results = reward_history_r.json()
                        reward_history.append(reward_history_r.json())
                        page += 1

                reward_history = [item for sublist in reward_history for item in sublist]

                for reward in reward_history:
                    datetime_delta = (reward['epoch'] - shelley_start_epoch) * 5
                    reward_time = shelley_start_datetime + timedelta(days=datetime_delta) + timedelta(days=10)
                    amount = int(reward['amount']) / 1000000
                    deposit = ['deposit', reward_time.strftime('%m/%d/%Y %H:%M:%S'), amount, 'ADA', '', '', '', '',
                               'staked', '']
                    add_row(deposit)
            else:
                print('---- skipping rewards already calculated for ' + stake_key)
        else:
            print('---- no stake key found for address: ' + address)
        stake_keys_calculated.add(stake_key)

        # Get all transactions for a specific address
        print('-- Get all transactions for ' + address)
        addr_txs = []
        with requests_cache.disabled():
            page = 1
            new_results = True
            while new_results:
                addr_txs_r = request_api(base_api + 'addresses/' + address + '/txs' + '?page=' + str(page))
                new_results = addr_txs_r.json()
                addr_txs.append(addr_txs_r.json())
                page += 1

        addr_txs = [item for sublist in addr_txs for item in sublist]

        # Get detailed transaction information
        print('-- Get detailed transaction information')
        txs_details = []
        for tx in addr_txs:
            print('---- for transaction ' + tx)
            tx_details_r = request_api(base_api + 'txs/' + tx)
            txs_details.append([tx, tx_details_r.json()])

        # Get blocks for transactions
        print('-- Get blocks for transactions')
        blocks_for_txs = []
        for tx in txs_details:
            print('---- for transaction ' + tx[0])
            blocks_for_txs.append(tx[1]['block'])

        # Get block details
        print("-- Get details")
        block_details = []
        for block in blocks_for_txs:
            print('---- for block ' + block)
            block_details_r = request_api(base_api + 'blocks/' + block)
            block_details.append(block_details_r.json())

        # Get time for blocks
        print('-- Get time for blocks')
        block_times = []
        for block in block_details:
            print('---- for block ' + block['hash'])
            block_time = block['time']
            block_times.append(block_time)

        # Combine tx with time
        print('-- Combine tx with time')
        tx_with_time = []
        i = 0
        for tx in txs_details:
            print('---- for transaction ' + tx[0])
            tx_with_time.append([tx[0], tx[1], block_times[i]])
            i += 1

        # Get UTXOs for all transactions
        print('-- Get transaction UTXOs')
        txs_utxos = []

        for tx in tx_with_time:
            print('---- for transaction ' + tx[0])
            tx_utxo_r = request_api(base_api + 'txs/' + tx[0] + '/utxos')
            txs_utxos.append([tx_utxo_r.json(), tx])

        # Filter inputs and outputs
        print('-- Filter inputs and outputs')
        inputs = []
        outputs = []
        reward_withdrawals = []

        for tx in txs_utxos:
            ins = tx[0]['inputs']
            outs = tx[0]['outputs']

            if int(tx[1][1]['withdrawal_count']) > 0:
                tx_withdrawal_r = request_api(base_api + 'txs/' + tx[1][0] + '/withdrawals')
                if stake_key == tx_withdrawal_r.json()[0]['address'] \
                        and [tx, tx_withdrawal_r.json()] not in reward_withdrawals:
                    reward_withdrawals.append([tx[0], tx[1], tx_withdrawal_r.json()])

            for i in ins:
                if i['address'] in addresses:
                    inputs.append([i, tx[1]])

            for o in outs:
                if o['address'] in addresses:
                    outputs.append([o, tx[1]])

        # Collect inputs
        print('-- Calculate withdrawals')
        for addr in addresses:
            for i in inputs:
                if addr in i[0]['address']:
                    tx_time = datetime.utcfromtimestamp(i[1][2]).strftime('%m/%d/%Y %H:%M:%S')
                    amount = i[0]['amount']
                    quantity = int(amount[0]['quantity']) / 1000000
                    fee = int(i[1][1]['fees']) / 1000000
                    tx_hash = i[1][0]
                    withdraw = ['withdraw', tx_time, '', '', quantity, 'ADA', fee, 'ADA', '', tx_hash]
                    add_row(withdraw)

        # Collect outputs
        print('-- Calculate deposits')
        for addr in addresses:
            for o in outputs:
                if addr in o[0]['address']:
                    tx_time = datetime.utcfromtimestamp(o[1][2]).strftime('%m/%d/%Y %H:%M:%S')
                    amount = o[0]['amount']
                    quantity = int(amount[0]['quantity']) / 1000000
                    tx_hash = o[1][0]
                    deposit = ['deposit', tx_time, quantity, 'ADA', '', '', '', '', '', tx_hash]
                    add_row(deposit)

        # Collect reward withdrawals
        print('-- Calculate reward withdrawals')
        for reward_withdrawal in reward_withdrawals:
            tx_time = datetime.utcfromtimestamp(reward_withdrawal[1][2]).strftime('%m/%d/%Y %H:%M:%S')
            amount = reward_withdrawal[2][0]['amount']
            tx_hash = reward_withdrawal[1][0]
            withdraw = ['withdraw', tx_time, '', '', int(amount) / 1000000, 'ADA', '', '', '', tx_hash]
            add_row(withdraw)

    write_data()

convert_csv_to_xlsx()
end_time = time.time()
elapsed_time = end_time - start_time
print('\nTransaction history created successfully in ' + str(round(elapsed_time, 4)) + 's using ' + str(cache_counter) +
      ' cached calls and ' + str(api_counter) + ' API calls for ' + str(len(wallet_files)) + ' wallet/s with ' +
      str(address_counter) + ' address/es.')
