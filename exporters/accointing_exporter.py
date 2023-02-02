from typing import List, Any

import config
from endpoints.blockfrost import get_withdrawal_for_transaction
from shared.representations import Wallet, Transaction

csv_header = ['transactionType', 'date', 'inBuyAmount', 'inBuyAsset', 'outSellAmount', 'outSellAsset', 'feeAmount (optional)',
              'feeAsset (optional)', 'classification (optional)', 'operationId (optional)', 'comments (optional)']
sorting_key = 1


def export_reward_history_for_wallet(wallet: Wallet, currency: str) -> List[Any]:
    rewards = []
    if len(wallet.rewards) > 0:
        for reward in wallet.rewards:
            amount = int(reward.amount) / 1000000
            classification = ''
            if reward.type == 'member':
                classification = 'staked'
            elif reward.type == 'leader':
                classification = 'master_node'
            elif reward.type == 'treasury' or reward.type == 'reserves':
                classification = 'bounty'
            rewards.append(['deposit', reward.reward_time, amount, 'ADA', '', '', '', '', classification, '', ''])

    return rewards


def export_transaction_history_for_transactions(transactions: List[Transaction], wallet: Wallet, currency: str) -> List[List[Any]]:
    tx_csv = []
    for tx in transactions:
        if tx.withdrawal_count > 0:
            withdrawal = get_withdrawal_for_transaction(tx.hash).json()
            withdrawal_address = withdrawal[0]['address']
            withdrawal_amount = int(withdrawal[0]['amount'])
            if withdrawal_address == wallet.stake_address:
                tx.output_amount = [('lovelace', tx.output_amount[0][1] - withdrawal_amount)]

        if tx.output_amount[0][1] < 0 and abs(tx.output_amount[0][1]) == tx.fees:
            # fees
            tx_csv.append(['withdraw',
                           tx.block_time,
                           '',
                           '',
                           tx.fees / 1000000,
                           'ADA',
                           '',
                           '',
                           'fee',
                           tx.hash,
                           ''])
        elif tx.output_amount[0][1] > 0:
            # deposit
            tx_csv.append(['deposit',
                           tx.block_time,
                           tx.output_amount[0][1] / 1000000 + tx.fees / 1000000,
                           'ADA',
                           '',
                           '',
                           tx.fees / 1000000,
                           'ADA',
                           '',
                           tx.hash,
                           ''])
        elif tx.output_amount[0][1] < 0:
            # withdrawal
            tx_csv.append(['withdraw',
                           tx.block_time,
                           '',
                           '',
                           abs(tx.output_amount[0][1]) / 1000000 - tx.fees / 1000000,
                           'ADA',
                           tx.fees / 1000000,
                           'ADA',
                           '',
                           tx.hash,
                           ''])
        else:
            print(f'The transaction "{tx.hash}" has a derived output amount of zero, thus not matching any accointing classification. Skipping..')

        if config.classify_internal_txs:
            internal = True
            wtx = wallet.transactions[tx.hash]
            wtx_utxos = wtx.inputs + wtx.outputs
            for wtx_utxo in wtx_utxos:
                if wtx_utxo.address not in config.addresses:
                    internal = False
                    break
            if internal:
                tx_csv[-1][0] = 'internal'

    return tx_csv


def sanity_check_controlled_amount(csv_data) -> float:
    derived_amount = 0.0
    for row in csv_data:
        if row[2] != '':
            derived_amount = derived_amount + float(row[2])
        if row[4] != '':
            derived_amount = derived_amount - float(row[4])
        if row[6] != '':
            derived_amount = derived_amount - float(row[6])

    return derived_amount


def sanity_check_amount_for_addresses(wallet: Wallet, csv_data) -> float:
    for address in wallet.addresses:
        derived_amount = 0.0
        tx_hashes = []
        for tx in address.transactions:
            tx_hashes.append(tx.hash)
        for row in csv_data:
            if row[9] in tx_hashes:
                if row[2] != '':
                    derived_amount = derived_amount + float(row[2])
                if row[4] != '':
                    derived_amount = derived_amount - float(row[4])
                if row[6] != '':
                    derived_amount = derived_amount - float(row[6])

    return derived_amount
