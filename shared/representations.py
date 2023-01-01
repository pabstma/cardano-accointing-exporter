from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple


@dataclass
class Input:
    address: str
    amount: List[Tuple[str, int]]
    tx_hash: str
    output_index: int
    collateral: bool


@dataclass
class Output:
    address: str
    amount: List[Tuple[str, int]]
    tx_hash: str
    output_index: int
    collateral: bool


@dataclass
class Transaction:
    hash: str
    block_time: datetime
    output_amount: List[Tuple[str, int]]
    fees: int
    utxo_in_count: int
    utxo_out_count: int
    utxo_count: int
    withdrawal_count: int
    mir_cert_count: int
    delegation_count: int
    stake_cert_count: int
    pool_update_count: int
    pool_retire_count: int
    inputs: List[Input]
    outputs: List[Output]

    def __post_init__(self) -> None:
        self.utxo_in_count = len(self.inputs)
        self.utxo_out_count = len(self.outputs)


@dataclass
class Reward:
    epoch: int
    reward_time: datetime
    amount: int
    pool_id: str
    type: str


@dataclass
class Address:
    address: str
    amount: List[Tuple[str, int]]
    transactions: List[Transaction]


@dataclass
class Wallet:
    stake_address: str
    controlled_amount: int
    addresses: List[Address]
    transactions: List[Transaction]
    rewards: List[Reward]
    active: bool
