from typing import List, Any

import config
from endpoints import coingecko
from endpoints.blockfrost import get_withdrawal_for_transaction
from shared.representations import Transaction, Wallet

csv_header = ['date', 'tx_id', 'inBuyAmount', 'inBuyAsset', 'inBuyFiatAmount', 'inBuyFiatAsset', 'outSellAmount', 'outSellAsset',
              'outSellFiatAmount', 'outSellFiatAsset', 'feeAmount', 'feeAsset', 'feeFiatAmount', 'feeFiatAsset', 'classification',
              'price', 'priceAsset', 'comments']
sorting_key = 0


def export_reward_history_for_wallet(wallet: Wallet, currency: str) -> List[Any]:
    rewards = []
    if len(wallet.rewards) > 0:
        for reward in wallet.rewards:
            amount = int(reward.amount) / 1000000
            price = round(coingecko.get_price_for_token_at_date('cardano', reward.reward_time, currency=currency), 2)
            classification = ''
            if reward.type == 'member':
                classification = 'staked'
            elif reward.type == 'leader':
                classification = 'master_node'
            elif reward.type == 'treasury' or reward.type == 'reserves':
                classification = 'bounty'
            rewards.append([reward.reward_time, '', amount, 'ADA', round(price * amount, 2), currency, '', '', '', '', '', '', '', '',
                            classification, price, currency, ''])
    return rewards


def export_transaction_history_for_transactions(transactions: List[Transaction], wallet: Wallet, currency: str) -> List[List[Any]]:
    tx_csv = []
    for tx in transactions:
        price = round(coingecko.get_price_for_token_at_date('cardano', tx.block_time, currency=currency), 2)

        if tx.withdrawal_count > 0:
            withdrawal = get_withdrawal_for_transaction(tx.hash).json()
            withdrawal_address = withdrawal[0]['address']
            withdrawal_amount = int(withdrawal[0]['amount'])
            if withdrawal_address == wallet.stake_address:
                tx.output_amount = [('lovelace', tx.output_amount[0][1] - withdrawal_amount)]

        if tx.output_amount[0][1] < 0 and abs(tx.output_amount[0][1]) == tx.fees:
            # fees
            amount = tx.fees / 1000000
            tx_csv.append([tx.block_time, tx.hash,
                           '', '', '', '',
                           amount, 'ADA', round(amount * price, 2), currency,
                           '', '', '', '',
                           'fee', price, currency, ''])

        elif tx.output_amount[0][1] > 0:
            # deposit
            amount = tx.output_amount[0][1] / 1000000 + tx.fees / 1000000
            fee_amount = tx.fees / 1000000
            tx_csv.append([tx.block_time, tx.hash,
                           amount, 'ADA', round(amount * price, 2), currency,
                           '', '', '', '',
                           fee_amount, 'ADA', fee_amount * price, currency,
                           'deposit', price, currency,  ''])

        elif tx.output_amount[0][1] < 0:
            # withdrawal
            amount = abs(tx.output_amount[0][1]) / 1000000 - tx.fees / 1000000
            fee_amount = tx.fees / 1000000
            tx_csv.append([tx.block_time, tx.hash,
                           '', '', '', '',
                           amount, 'ADA', round(amount * price, 2), currency,
                           fee_amount, 'ADA', fee_amount * price, currency,
                           'withdraw', price, currency,  ''])

        else:
            out_amount = abs(tx.output_amount[0][1]) / 1000000 - tx.fees / 1000000
            in_amount = tx.output_amount[0][1] / 1000000 + tx.fees / 1000000
            fee_amount = tx.fees / 1000000
            tx_csv.append([tx.block_time, tx.hash,
                           in_amount, 'ADA', round(in_amount * price, 2), currency,
                           out_amount, 'ADA', round(out_amount * price, 2), currency,
                           fee_amount, 'ADA', round(fee_amount * price, 2), currency,
                           'smart contract', price, currency,  ''])

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
        if row[6] != '':
            derived_amount = derived_amount - float(row[6])
        if row[10] != '':
            derived_amount = derived_amount - float(row[10])

    return derived_amount


def sanity_check_amount_for_addresses(wallet: Wallet, csv_data) -> float:
    for address in wallet.addresses:
        derived_amount = 0.0
        tx_hashes = []
        for tx in address.transactions:
            tx_hashes.append(tx.hash)

        for row in csv_data:
            if row[1] in tx_hashes:
                if row[2] != '':
                    derived_amount = derived_amount + float(row[2])
                if row[6] != '':
                    derived_amount = derived_amount - float(row[6])
                if row[10] != '':
                    derived_amount = derived_amount - float(row[10])

    return derived_amount
