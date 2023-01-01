import csv
from typing import Any

import pandas as pd

from exporters.accointing import csv_header
from shared.representations import *


# Extract addresses from a given file and add the addresses to the given wallet
def extract_addresses_from_file(wallet_file: str) -> List[Address]:
    file = open(wallet_file, 'r')
    wallets = file.readlines()
    wallet_list = []
    for i in range(0, len(wallets)):
        wallets[i] = wallets[i].strip()
        wallet_list.append(Address(wallets[i], [], []))
    return wallet_list


# Add row if it does not exist
def add_row(data, csv_data: Any) -> None:
    if data not in csv_data:
        csv_data.append(data)


# Write csv data into file
def write_data(filename: str, csv_data: Any) -> None:
    print('-- Sort calculated data')
    sorted_data = sorted(csv_data, key=lambda x: x[1])
    print('-- Write data on drive')
    with open(filename, mode='w') as transactions_file:
        transactions_writer = csv.writer(transactions_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        transactions_writer.writerow(csv_header)
        for d in sorted_data:
            transactions_writer.writerow(d)


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

    for tx in wallet.transactions:
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
