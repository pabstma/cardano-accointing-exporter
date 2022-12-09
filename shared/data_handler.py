import csv
import pandas as pd

from datetime import datetime
from exporters.accointing import csv_header


# Add row if it does not exist
def add_row(data, csv_data):
    if data not in csv_data:
        csv_data.append(data)


# Write csv data into file
def write_data(filename, csv_data):
    print('-- Sort calculated data')
    sorted_data = sorted(csv_data, key=lambda x: datetime.strptime(x[1], '%m/%d/%Y %H:%M:%S'))
    print('-- Aggregate UTXOs')
    aggregated_data = aggregate_utxos(sorted_data, csv_data)
    print('-- Write data on drive')
    with open(filename, mode='w') as transactions_file:
        transactions_writer = csv.writer(transactions_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        transactions_writer.writerow(csv_header)
        for d in aggregated_data:
            transactions_writer.writerow(d[:len(d) - 2])


# Aggregate the utxos of a transaction into one
def aggregate_utxos(data, csv_data):
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

        # aggregate each utxo into our aggregate variable
        for utxo in utxos:
            if tx_type == 'deposit' and utxo != d and tx_time == utxo[1] and utxo[9] not in seen_deposit:
                aggregate[2] += utxo[2]
            elif tx_type == 'withdraw' and utxo != d and tx_time == utxo[1] and utxo[9] not in seen_withdraw:
                aggregate[4] += utxo[4]

        # Mark the deposit/withdrawal as seen
        if tx_type == 'deposit':
            seen_deposit.append(tx_id)
        if tx_type == 'withdraw':
            seen_withdraw.append(tx_id)

        # if our aggregate is not already in our aggregated_utxos, add it
        if not list(filter(lambda x: x[9] == aggregate[9] and x[0] == aggregate[0] and x[1] == aggregate[1],
                           aggregated_utxos)):
            aggregated_utxos.append(aggregate)

    # Build transaction fees and deposits
    transactions = list(filter(lambda x: x[9] != '', aggregated_utxos))
    rewards = list(filter(lambda x: x[9] == '', data))
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
            final_tx = ['withdraw', date, '', '', round(result, 6), 'ADA', fee, fee_asset, classification, operation_id,
                        '', '', '']
            add_row(final_tx, csv_data)
            aggregated_data.append(final_tx)
        elif transaction[9] not in seen_transactions:
            seen_transactions.append(transaction[9])
            aggregated_data.append(tx_pair[0])
    return sorted((aggregated_data + rewards), key=lambda x: datetime.strptime(x[1], '%m/%d/%Y %H:%M:%S'))


def convert_csv_to_xlsx(csv_files):
    for csv_file in csv_files:
        out = csv_file.split('.')[0] + '.xlsx'
        df = pd.read_csv(csv_file)
        df.to_excel(out, index=False)
