import glob
import math
import sys
import time
from os import remove

import argparse
import config
import endpoints.blockfrost as blockfrost
import endpoints.koios as koios
import exporters
import requests_cache
from config import URLS_EXPIRE_AFTER, LINE_CLEAR
from exporters.accointing import export_reward_history_for_wallet, export_transaction_history_for_transactions
from shared.data_handler import extract_addresses_from_file, add_row, calculate_derived_tx, write_data, convert_csv_to_xlsx
from shared.helper import clear
from shared.representations import Wallet


def main():
    config.init()

    parser = argparse.ArgumentParser(description='This program exports the transaction history of one or more wallets in an account-like ' +
                                                 'style using one of the available exporters.')
    parser.add_argument('--project-id-file', type=str, help='path to a file containing only your blockfrost.io project id ' +
                                                            '(has precedence over hard-coded project id in config.py)')
    parser.add_argument('--purge-cache', help='removes the current cache; forcing refresh of API data', action='store_true')
    args = parser.parse_args()

    # Handle api-key-file argument
    if args.project_id_file is not None:
        try:
            with open(args.project_id_file, 'r') as f:
                content = f.read()
                if content:
                    config.PROJECT_ID = content.splitlines()[0]
                else:
                    print('Given project-id-file is empty. Using project id from config.py if available.')
                print('Project id ' + args.project_id_file + ' read successfully ', end='')
                print(u'\u2713')
        except OSError as e:
            print(f'Unable to open {args.project_id_file}: {e}', file=sys.stderr)
            print('Using project id from config.py if available')

    if config.PROJECT_ID == '':
        print('No blockfrost project id was given but is required. Check -h or --help for information about the usage.')
        exit(1)

    blockfrost.init_header()

    # Handle purge-cache argument
    if args.purge_cache:
        print('Purge Cache ', end='')
        remove('http_cache.sqlite')
        print(u'\u2713')

    # Check backend health
    print('Check backend health ', end='')
    if not blockfrost.check_health():
        print('Backend reports unhealthy state. Check https://status.blockfrost.io/ and try again later.')
        exit(1)
    print(u'\u2713')

    # Check project id validity
    print('Check validity of Blockfrost project id ', end='')
    blockfrost.check_project_id()
    print(u'\u2713')

    requests_cache.install_cache(expire_after=None, urls_expire_after=URLS_EXPIRE_AFTER)
    requests_cache.remove_expired_responses()

    for wallet_file in config.wallet_files:

        current_wallet = Wallet('', 0, [], [], [], False)
        config.wallets.append(current_wallet)

        config.calculated_wallet_counter += 1
        config.tx_counter = 0
        config.reward_counter = 0

        print('Calculating wallet ' + str(config.calculated_wallet_counter) + ' of ' + str(config.wallet_counter))
        print('-- Reading wallet ' + wallet_file)
        csv_data = []
        stake_keys_calculated = set()
        current_wallet.stake_address = None
        filename = wallet_file.split('.')[0] + '.csv'

        current_wallet.addresses = extract_addresses_from_file(wallet_file)
        if len(current_wallet.addresses) == 1 and current_wallet.addresses[0].address.startswith('stake1u'):
            print('---- Stake key detected ' + current_wallet.addresses[0].address)
            current_wallet.stake_address = current_wallet.addresses[0].address

        # If there is no stake key given, check if we can find the stake key anyway
        if current_wallet.stake_address is None:
            current_wallet.stake_address = blockfrost.get_stake_addr_for_addr(current_wallet.addresses[0].address)

        if current_wallet.stake_address.startswith('stake1u'):
            print('---- Get addresses for ' + current_wallet.stake_address)
            current_wallet.addresses = blockfrost.get_addresses_for_account(current_wallet.stake_address)
            print('---- Get controlled amount for ' + current_wallet.stake_address)
            current_wallet.controlled_amount = blockfrost.get_controlled_amount_for_account(current_wallet.stake_address)
            print('---- Get status of stake key ' + current_wallet.stake_address)
            current_wallet.active = blockfrost.get_active_status_for_account(current_wallet.stake_address)

        config.address_counter += len(current_wallet.addresses)

        # Wallet Transaction History
        for address in current_wallet.addresses:
            config.tx_counter = 0
            config.calculated_address_counter += 1
            clear()
            config.elapsed_time = time.time() - config.start_time
            print()
            print('Calculating wallet ' + str(config.calculated_wallet_counter) + ' of ' + str(config.wallet_counter))
            print('Calculating address ' + str(config.calculated_address_counter) + ' of ' + str(config.address_counter))

            # Reward history
            print('-- Get reward history')
            if current_wallet.stake_address.startswith('stake1u'):
                if current_wallet.stake_address not in stake_keys_calculated:
                    print('---- for stake key ' + current_wallet.stake_address)
                    current_wallet.rewards = koios.get_reward_history_for_account(current_wallet.stake_address)
                    for row in export_reward_history_for_wallet(current_wallet):
                        add_row(row, csv_data)
                    stake_keys_calculated.add(current_wallet.stake_address)
                else:
                    print('---- skipping rewards already calculated for ' + current_wallet.stake_address)
            else:
                print('---- no stake key found for address: ' + address.address)

            # Get all transactions for a specific address
            print('-- Get all transactions for ' + address.address)
            transactions = blockfrost.get_transaction_history_for_addr(address.address)
            current_wallet.transactions.append(transactions)
            address.transactions = transactions
            print(LINE_CLEAR + '---- Received ' + str(config.tx_counter) + ' TXs - Elapsed Time: ' +
                  str(round(config.elapsed_time, 2)), end='\r')

        current_wallet.transactions = [item for sublist in current_wallet.transactions for item in sublist]
        derived_txs = calculate_derived_tx(current_wallet)

        # write txs to file
        for row in export_transaction_history_for_transactions(derived_txs, current_wallet):
            add_row(row, csv_data)

        # Sanity Checks
        print()
        if current_wallet.stake_address.startswith('stake1u'):
            print('-- Sanity check for controlled amount')
            derived_controlled_amount = exporters.accointing.sanity_check_controlled_amount(csv_data)
            if not math.isclose(derived_controlled_amount, current_wallet.controlled_amount / 1000000, abs_tol=0.00000001):
                print('---- Sanity check for controlled amount failed. Expected: ' + str(
                    current_wallet.controlled_amount / 1000000) + ' Was: ' + str(
                    round(derived_controlled_amount, 6)) + ' Diff: ' + str(
                    round(current_wallet.controlled_amount / 1000000 - derived_controlled_amount, 6)))
            else:
                print('---- Sanity check for controlled amount successful. Current ADA amount of wallet: ' + str(
                    abs(round(derived_controlled_amount, 6))))

        if config.address_counter >= 1 and not current_wallet.stake_address.startswith('stake1u'):
            print('-- Sanity check for controlled amount of address')
            amount = blockfrost.get_amount_for_address(address.address)
            derived_amount = exporters.accointing.sanity_check_amount_for_addresses(current_wallet, csv_data)
            if not math.isclose(derived_amount, amount / 1000000, abs_tol=0.00000001):
                print(
                    '---- Sanity check for address failed. Expected: ' + str(amount / 1000000) + ' Was: ' + str(
                        round(derived_amount, 6)) + ' Diff: '
                    + str(abs(round(amount / 1000000 - derived_amount, 6))))
            else:
                print('---- Sanity check for controlled amount successful. Current ADA amount of address: ' + str(
                    abs(round(derived_amount, 6))))

        write_data(filename, csv_data)

    convert_csv_to_xlsx(glob.glob('wallets/*.csv'))
    end_time = time.time()
    config.elapsed_time = end_time - config.start_time
    print('\nTransaction history created successfully in ' + str(round(config.elapsed_time, 4)) + 's using ' + str(config.cache_counter) +
          ' cached calls and ' + str(config.api_counter) + ' API calls for ' + str(len(config.wallet_files)) + ' wallet(s) with ' +
          str(config.address_counter) + ' address(es).')


if __name__ == "__main__":
    main()
