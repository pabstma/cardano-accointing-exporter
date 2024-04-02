import glob
import math
import time
from datetime import datetime, timezone
from os import remove
from typing import List

import argparse
import requests_cache

import config
import endpoints.blockfrost as blockfrost
import endpoints.koios as koios
import exporters.accointing_exporter
import exporters.blockpit_exporter
import exporters.generic_exporter
from config import URLS_EXPIRE_AFTER
from endpoints import coingecko
from shared import api_handler
from shared.data_handler import extract_addresses_from_file, add_row, calculate_derived_tx, write_data, convert_csv_to_xlsx, read_lines
from shared.representations import Wallet


def main():
    parser = argparse.ArgumentParser(description='This program exports the transaction history of one or more wallets in an account-like ' +
                                                 'style using one of the available exporters. Note: not all exporters support all features.')
    parser.add_argument('--project-id-file', type=str, default='project.id', help='path to a file containing only your blockfrost.io ' +
                        'project id (has precedence over hard-coded project id in config.py, default: project.id)')
    parser.add_argument('--exporter', type=str, default='accointing', help='the exporter to use (available: accointing, blockpit, generic, default: accointing)')
    parser.add_argument('--purge-cache', help='removes the current cache; forcing refresh of API data', action='store_true')
    parser.add_argument('--start-time', type=lambda s: datetime.strptime(s, '%Y-%m-%d').replace(tzinfo=timezone.utc),
                        default=datetime.fromtimestamp(0, timezone.utc),
                        help='the utc time (inclusive) the transaction history should start at (format: YYYY-mm-dd e.g. 2022-02-19)')
    parser.add_argument('--end-time', type=lambda s: datetime.strptime(s, '%Y-%m-%d')
                        .replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc),
                        default=datetime.fromtimestamp(config.start_time, timezone.utc),
                        help='the utc time (inclusive) the transaction history should end at (format: YYYY-mm-dd e.g. 2022-02-19)')
    parser.add_argument('--currency', type=str, default='usd', help='String of three letter currency code to use (default: usd)')
    parser.add_argument('--no-sanity-check', action='store_false',
                        help='Do not perform sanity checks of calculated amount against on chain data (sanity checks are always disabled ' +
                             'when using custom --start-time and --end-time values)')
    parser.add_argument('--classify-internal-txs', action='store_true',
                        help='Use the "internal" classification for transfers between your own ' +
                             'wallets. This assumes that all wallets in your wallets/ subdirectory belong together. Note: this is not ' +
                             'supported by accointing for a direct import but can be useful for tracking purposes.')
    parser.add_argument('--internals-file', type=str,
                        help='You can supply a file containing additional addresses that are used to determine internal transfers but are' +
                             ' not used for transaction history creation. One address or stake key per line.')
    args = parser.parse_args()

    # Handle project id file argument
    if args.project_id_file is not None:
        content = read_lines(args.project_id_file)
        if content:
            config.PROJECT_ID = content[0]
        else:
            print('Given project-id-file is empty. Using project id from config.py if available.')
        print(f'Project id file "{args.project_id_file}" read successfully', end='')
        print(u'\u2713')

    if config.PROJECT_ID == '':
        print('No blockfrost project id was given but is required. Check -h or --help for information about the usage.')
        exit(1)

    blockfrost.init_header()

    # Handle exporter argument
    if args.exporter == 'accointing':
        exporter = exporters.accointing_exporter
    if args.exporter == 'blockpit':
        exporter = exporters.blockpit_exporter
    elif args.exporter == 'generic':
        exporter = exporters.generic_exporter
    else:
        print('Given exporter is not supported. Check -h or --help for information about the usage.')
        exit(1)

    # Handle purge-cache argument
    if args.purge_cache:
        print('Purge Cache ', end='')
        remove('http_cache.sqlite')
        print(u'\u2713')

    # Handle classify-internal argument
    config.classify_internal_txs = args.classify_internal_txs

    # Handle internals-file argument
    if args.internals_file is not None:
        content = read_lines(args.internals_file)
        if content:
            for address in content:
                if address.startswith('stake1u'):
                    config.addresses.update([item.address for item in blockfrost.get_addresses_for_account(address)])
                else:
                    config.addresses.add(address)
        else:
            print('Given internals file is empty. No additional internals will be used.')
        print(f'Internals file "{args.internals_file}" read successfully ', end='')
        print(u'\u2713')
    internals_counter = len(config.addresses)

    # Handle currency argument
    if args.currency is not None:
        if not args.currency in coingecko.get_supported_vs_currencies():
            print(f'Given currency "{args.currency}" is not supported. ' +
                  'Check https://www.coingecko.com/api/documentations/v3#/simple/get_simple_supported_vs_currencies for a list of supported currencies.')
            exit(1)
    currency = args.currency

    # Handle sanity-check argument
    if args.start_time != datetime.fromtimestamp(0, timezone.utc) or args.end_time != datetime.fromtimestamp(config.start_time, timezone.utc):
        args.no_sanity_check = False

    # Check backend health
    print('Check backend health ', end='')
    if not blockfrost.check_health():
        print('Backend reports unhealthy state. Check https://status.blockfrost.io/ and try again later.')
        exit(1)
    print(u'\u2713')

    # Check project id validity
    print('Check validity of Blockfrost project id ', end='')
    blockfrost.check_project_id()
    print(u'\u2713', end='')

    requests_cache.install_cache(expire_after=None, urls_expire_after=URLS_EXPIRE_AFTER)
    requests_cache.remove_expired_responses()

    # Prepare some variables
    wallets = []  # type: List[Wallet]
    wallet_counter = len(config.wallet_files)
    tx_counter = 0
    # Calculate all stake keys and wallet addresses first
    for wallet_file in config.wallet_files:

        current_wallet = Wallet('', '', 0, [], {}, [], False)
        wallets.append(current_wallet)

        print()
        print(f'Collect basic information for {wallet_file}')
        print('-- Reading wallet')
        current_wallet.stake_address = None
        current_wallet.name = wallet_file.split('.')[0]

        current_wallet.addresses = extract_addresses_from_file(wallet_file)
        if len(current_wallet.addresses) == 1 and current_wallet.addresses[0].address.startswith('stake1u'):
            print(f'---- Stake key detected {current_wallet.addresses[0].address}')
            current_wallet.stake_address = current_wallet.addresses[0].address

        # If there is no stake key given, check if we can find the stake key anyway
        if current_wallet.stake_address is None:
            current_wallet.stake_address = blockfrost.get_stake_addr_for_addr(current_wallet.addresses[0].address)

        if current_wallet.stake_address.startswith('stake1u'):
            print(f'---- Get addresses for {current_wallet.stake_address}')
            current_wallet.addresses = blockfrost.get_addresses_for_account(current_wallet.stake_address)
            print(f'---- Get controlled amount for {current_wallet.stake_address}')
            current_wallet.controlled_amount = blockfrost.get_controlled_amount_for_account(current_wallet.stake_address)
            print(f'---- Get status of stake key {current_wallet.stake_address}')
            current_wallet.active = blockfrost.get_active_status_for_account(current_wallet.stake_address)

        for addr in current_wallet.addresses:
            config.addresses.add(addr.address)

    calculated_wallet_counter = 0
    for current_wallet in wallets:
        calculated_wallet_counter += 1
        address_counter = 0
        calculated_address_counter = 0
        address_counter += len(current_wallet.addresses)
        csv_data = []
        stake_keys_calculated = set()

        print('\n')
        print(f'Calculating wallet {calculated_wallet_counter} of {wallet_counter}')

        # Wallet Transaction History
        for address in current_wallet.addresses:
            addr_tx_counter = 0
            calculated_address_counter += 1
            config.elapsed_time = time.time() - config.start_time
            print(f'Calculating address {calculated_address_counter} of {address_counter}')

            # Reward history
            if current_wallet.stake_address.startswith('stake1u'):
                if current_wallet.stake_address not in stake_keys_calculated:
                    print('-- Get reward history')
                    print(f'---- for stake key {current_wallet.stake_address}')
                    current_wallet.rewards = koios.get_reward_history_for_account(current_wallet.stake_address, args.start_time, args.end_time)
                    reward_history = exporter.export_reward_history_for_wallet(current_wallet, currency)
                    for row in reward_history:
                        add_row(row, csv_data)
                    stake_keys_calculated.add(current_wallet.stake_address)
            else:
                print(f'---- no stake key found for address: {address.address}')

            # Get all transactions for a specific address
            print(f'-- Get all transactions for {address.address}')
            transactions = blockfrost.get_transaction_history_for_addr(address.address, args.start_time, args.end_time)
            addr_tx_counter += len(transactions)
            tx_counter += addr_tx_counter
            for tx in transactions:
                current_wallet.transactions[tx.hash] = tx
            address.transactions = transactions
            print(f'---- Received {addr_tx_counter} TXs - Elapsed Time: {round(config.elapsed_time, 2)}')

        derived_txs = calculate_derived_tx(current_wallet)

        # write txs to file
        print('---- Deriving transactions')
        for row in exporter.export_transaction_history_for_transactions(derived_txs, current_wallet, currency):
            add_row(row, csv_data)

        # Sanity Checks
        if args.no_sanity_check:
            if current_wallet.stake_address.startswith('stake1u'):
                print('-- Sanity check for controlled amount')
                derived_controlled_amount = exporter.sanity_check_controlled_amount(csv_data)
                if not math.isclose(derived_controlled_amount, current_wallet.controlled_amount / 1000000, abs_tol=0.00000001):
                    print(f'---- Sanity check for controlled amount failed. Expected: {current_wallet.controlled_amount / 1000000} ' +
                          f'Was: {round(derived_controlled_amount, 6)} Diff: {round(current_wallet.controlled_amount / 1000000 - derived_controlled_amount, 6)}')
                else:
                    print(f'---- Sanity check for controlled amount successful. Current ADA amount of wallet: {abs(round(derived_controlled_amount, 6))}')

            if address_counter >= 1 and not current_wallet.stake_address.startswith('stake1u'):
                print('-- Sanity check for controlled amount of address')
                amount = blockfrost.get_amount_for_address(address.address)
                derived_amount = exporter.sanity_check_amount_for_addresses(current_wallet, csv_data)
                if not math.isclose(derived_amount, amount / 1000000, abs_tol=0.00000001):
                    print(f'---- Sanity check for address failed. Expected: {amount / 1000000} Was: {round(derived_amount, 6)} ' +
                          f'Diff: {abs(round(amount / 1000000 - derived_amount, 6))}')
                else:
                    print(f'---- Sanity check for controlled amount successful. Current ADA amount of address: {abs(round(derived_amount, 6))}')

        write_data(current_wallet.name + '.csv', exporter.csv_header, csv_data, exporter.sorting_key)

    print('\nConvert CSV to XLSX ', end='')
    print(u'\u2713')
    convert_csv_to_xlsx(glob.glob('wallets/*.csv'))
    end_time = time.time()
    config.elapsed_time = end_time - config.start_time
    print(f'Transaction history created successfully in {round(config.elapsed_time, 4)}s using {api_handler.get_lru_cache_hit_counter()} ' +
          f'in memory cached calls, {config.ondisk_cache_counter} on disk cached calls and {config.api_counter} API calls for ' +
          f'{len(config.wallet_files)} wallet(s) with {len(config.addresses) - internals_counter} address(es) with {tx_counter} transactions.')


if __name__ == "__main__":
    main()
