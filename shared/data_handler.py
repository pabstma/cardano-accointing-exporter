import csv
import sys
from typing import Any, List

import pandas as pd

from shared.representations import Address, Transaction, Wallet


def read_lines(path: str) -> List[str]:
    lines = []
    if path is not None:
        try:
            with open(path, 'r') as f:
                content = f.read()
                if content:
                    lines = [line.strip() for line in content.splitlines()]
        except OSError as e:
            print(f'Unable to read {path}: {e}', file=sys.stderr)
            print('Please make sure you can access the specified file: ' + path)
            exit(1)

    return lines


# Extract addresses from a given file and add the addresses to the given wallet
def extract_addresses_from_file(wallet_file: str) -> List[Address]:
    wallet_list = []
    try:
        with open(wallet_file, 'r') as f:
            wallets = f.readlines()
        for i in range(0, len(wallets)):
            wallets[i] = wallets[i].strip()
            wallet_list.append(Address(wallets[i], [], {}))
    except OSError as e:
        print(f"Unable to read {wallet_file}: {e}", file=sys.stderr)
        exit(1)

    return wallet_list


# Add row if it does not exist
def add_row(data, csv_data: Any) -> None:
    if data not in csv_data:
        csv_data.append(data)


# Write csv data into file
def write_data(filename: str, csv_header: str, csv_data: Any, sorting_key: int) -> None:
    print('-- Sort calculated data')
    sorted_data = sorted(csv_data, key=lambda x: x[sorting_key])
    print('-- Write data on drive')
    try:
        with open(filename, mode='w') as transactions_file:
            transactions_writer = csv.writer(transactions_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            transactions_writer.writerow(csv_header)
            for d in sorted_data:
                transactions_writer.writerow(d)
    except OSError as e:
        print(f"Unable to open or write to {filename}: {e}", file=sys.stderr)
        exit(1)


def convert_csv_to_xlsx(csv_files: List[str]) -> None:
    for csv_file in csv_files:
        out = csv_file.split('.')[0] + '.xlsx'
        df = pd.read_csv(csv_file)
        df.to_excel(out, index=False)


# Calculate real value of a transaction depending on the wallet
def calculate_derived_tx(wallet: Wallet) -> List[Transaction]:
    derived_txs = []
    list_of_addresses = []
    for addr in wallet.addresses:
        list_of_addresses.append(addr.address)

    for tx_hash, tx in wallet.transactions.items():
        inputs = []
        outputs = []
        sum_of_inputs = 0
        sum_of_outputs = 0

        for tx_input in tx.inputs:
            if tx_input.address in list_of_addresses and tx_input.collateral is False:
                inputs.append(tx_input)
                sum_of_inputs = sum_of_inputs + tx_input.amount[0][1]

        for tx_output in tx.outputs:
            if tx_output.address in list_of_addresses:
                outputs.append(tx_output)
                sum_of_outputs = sum_of_outputs + tx_output.amount[0][1]

        derived_tx = Transaction(tx.hash,
                                 tx.block_time,
                                 [('lovelace', int(sum_of_outputs - sum_of_inputs))],
                                 0,
                                 len(inputs),
                                 len(outputs),
                                 len(inputs) + len(outputs),
                                 tx.withdrawal_count,
                                 tx.mir_cert_count,
                                 tx.delegation_count,
                                 tx.stake_cert_count,
                                 tx.pool_update_count,
                                 tx.pool_retire_count,
                                 inputs,
                                 outputs)

        if derived_tx.utxo_in_count + derived_tx.utxo_out_count == tx.utxo_count or derived_tx.utxo_in_count == tx.utxo_in_count:
            derived_tx.fees = tx.fees

        derived_txs.append(derived_tx)

    return derived_txs
