import glob
import time as time
from datetime import timedelta, datetime
import requests_cache
import endpoints.blockfrost as blockfrost
import endpoints.koios as koios
import config

from shared import data_handler
from config import BLOCKFROST_BASE_API, SHELLEY_START_EPOCH, SHELLEY_START_DATETIME, KOIOS_BASE_API, LINE_CLEAR
from shared.helper import *


# Start of the script itself
config.init()
requests_cache.install_cache(expire_after=None)

for wallet in config.wallet_files:

    config.calculated_wallet_counter += 1
    config.tx_counter = 0
    config.reward_counter = 0

    print('Calculating wallet ' + str(config.calculated_wallet_counter) + ' of ' + str(config.wallet_counter))
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
            addresses_r = blockfrost.request_api(BLOCKFROST_BASE_API + 'accounts/' + stake_key + '/addresses' + '?page=' + str(page))
            new_results = addresses_r.json()
            page += 1
            for address in addresses_r.json():
                addresses.append(address['address'])
                print('-------- Address found ' + address['address'], end='\r')

    config.address_counter += len(addresses)
    # Wallet Transaction History
    for address in addresses:

        config.tx_counter = 0
        config.calculated_address_counter += 1
        clear()
        config.elapsed_time = time.time() - config.start_time
        print()
        print('Calculating wallet ' + str(config.calculated_wallet_counter) + ' of ' + str(config.wallet_counter))
        print('Calculating address ' + str(config.calculated_address_counter) + ' of ' + str(config.address_counter))

        # Address request
        addr_r = blockfrost.request_api(BLOCKFROST_BASE_API + 'addresses/' + address)
        if stake_key is None:
            stake_key = addr_r.json()['stake_address']

        # Reward history
        print('-- Get reward history')
        reward_history_r = None
        reward_history = []
        if stake_key is not None:
            if stake_key not in stake_keys_calculated:
                print('---- for stake key ' + stake_key)
                with requests_cache.disabled():
                    offset = 0
                    new_results = True
                    while new_results:
                        body = {"_stake_addresses": [stake_key]}
                        reward_history_r = koios.request_api(KOIOS_BASE_API + 'account_rewards' + '?offset=' + str(offset), body)
                        new_results = reward_history_r.json()
                        reward_history.append(reward_history_r.json())
                        offset += 1000

                reward_history = [item for sublist in reward_history for item in sublist]

                for reward in reward_history[0]['rewards']:
                    config.reward_counter += 1
                    datetime_delta = (reward['earned_epoch'] - SHELLEY_START_EPOCH) * 5
                    reward_time = SHELLEY_START_DATETIME + timedelta(days=datetime_delta) + timedelta(days=10)
                    amount = int(reward['amount']) / 1000000
                    reward_type = reward['type']
                    classification = ""
                    if reward_type == 'member':
                        classification = 'staked'
                    elif reward_type == 'leader':
                        classification = 'master_node'
                    elif reward_type == 'treasury' or reward_type == 'reserves':
                        classification = 'bounty'
                    deposit = ['deposit', reward_time.strftime('%m/%d/%Y %H:%M:%S'), amount, 'ADA', '', '', '', '',
                               classification, '', '', '', config.reward_counter]
                    data_handler.add_row(deposit, csv_data)
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
                addr_txs_r = blockfrost.request_api(BLOCKFROST_BASE_API + 'addresses/' + address + '/transactions' + '?page=' + str(page))
                new_results = addr_txs_r.json()
                addr_txs.append(addr_txs_r.json())
                config.tx_counter += len(new_results)
                page += 1
                config.elapsed_time = time.time() - config.start_time
                print(LINE_CLEAR + '---- Received ' + str(config.tx_counter) + ' TXs - Elapsed Time: ' + str(round(config.elapsed_time, 2)), end='\r')

        addr_txs = [item for sublist in addr_txs for item in sublist]

        # Get detailed transaction information
        print('\n-- Get detailed transaction information')
        txs_details = []
        c = 1
        for tx in addr_txs:
            config.elapsed_time = time.time() - config.start_time
            print(LINE_CLEAR + '---- for transaction ' + tx['tx_hash'] + ' - Computed TXs: ' + str(c) + '/' + str(config.tx_counter) + ' - Elapsed Time: ' + str(round(config.elapsed_time, 2)), end='\r')
            tx_details_r = blockfrost.request_api(BLOCKFROST_BASE_API + 'txs/' + tx['tx_hash'])
            txs_details.append(tx_details_r.json())
            c += 1

        # Get UTXOs for all transactions
        print('\n-- Get transaction UTXOs')
        txs_utxos = []
        c = 1
        for tx in txs_details:
            config.elapsed_time = time.time() - config.start_time
            print(LINE_CLEAR + '---- for transaction ' + tx['hash'] + ' - Computed TXs: ' + str(c) + '/' + str(config.tx_counter) + ' - Elapsed Time: ' + str(round(config.elapsed_time, 2)), end='\r')
            tx_utxo_r = blockfrost.request_api(BLOCKFROST_BASE_API + 'txs/' + tx['hash'] + '/utxos')
            txs_utxos.append([tx_utxo_r.json(), tx])
            c += 1

        # Filter inputs and outputs
        print('\n-- Filter inputs and outputs')
        inputs = []
        outputs = []
        reward_withdrawals = []

        for tx in txs_utxos:
            ins = tx[0]['inputs']
            outs = tx[0]['outputs']
            if int(tx[1]['withdrawal_count']) > 0:
                tx_withdrawal_r = blockfrost.request_api(BLOCKFROST_BASE_API + 'txs/' + tx[0]['hash'] + '/withdrawals')
                if stake_key == tx_withdrawal_r.json()[0]['address'] \
                        and [tx, tx_withdrawal_r.json()] not in reward_withdrawals:
                    reward_withdrawals.append([tx_withdrawal_r.json(), tx[1]])

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
                    tx_time = datetime.utcfromtimestamp(i[1]['block_time']).strftime('%m/%d/%Y %H:%M:%S')
                    amount = i[0]['amount']
                    quantity = int(amount[0]['quantity']) / 1000000
                    fee = int(i[1]['fees']) / 1000000
                    tx_hash = i[1]['hash']
                    address = i[0]['address']
                    output_index = i[0]['output_index']
                    withdraw = ['withdraw', tx_time, '', '', quantity, 'ADA', fee, 'ADA', '', tx_hash, '', address, output_index]
                    data_handler.add_row(withdraw, csv_data)

        # Collect outputs
        print('-- Calculate deposits')
        for addr in addresses:
            for o in outputs:
                if addr in o[0]['address']:
                    tx_time = datetime.utcfromtimestamp(o[1]['block_time']).strftime('%m/%d/%Y %H:%M:%S')
                    amount = o[0]['amount']
                    quantity = int(amount[0]['quantity']) / 1000000
                    tx_hash = o[1]['hash']
                    address = o[0]['address']
                    output_index = o[0]['output_index']
                    deposit = ['deposit', tx_time, quantity, 'ADA', '', '', '', '', '', tx_hash, '', address, output_index]
                    data_handler.add_row(deposit, csv_data)

        # Collect reward withdrawals
        print('-- Calculate reward withdrawals')
        for reward_withdrawal in reward_withdrawals:
            tx_time = datetime.utcfromtimestamp(reward_withdrawal[1]['block_time']).strftime('%m/%d/%Y %H:%M:%S')
            amount = reward_withdrawal[0][0]['amount']
            tx_hash = reward_withdrawal[1]['hash']
            withdraw = ['withdraw', tx_time, '', '', int(amount) / 1000000, 'ADA', '', '', '', tx_hash, '', '', '']
            data_handler.add_row(withdraw, csv_data)

    data_handler.write_data(filename, csv_data)

data_handler.convert_csv_to_xlsx(glob.glob('wallets/*.csv'))
end_time = time.time()
config.elapsed_time = end_time - config.start_time
print('\nTransaction history created successfully in ' + str(round(config.elapsed_time, 4)) + 's using ' + str(config.cache_counter) +
      ' cached calls and ' + str(config.api_counter) + ' API calls for ' + str(len(config.wallet_files)) + ' wallet(s) with ' +
      str(config.address_counter) + ' address(/)es).')
