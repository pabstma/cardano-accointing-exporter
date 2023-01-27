from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple, Dict


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

    def __hash__(self):
        return hash(self.hash)

    def __eq__(self, other):
        if isinstance(other, Transaction):
            return self.hash == other.hash
        elif isinstance(other, str):
            return self.hash == other


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
    transactions: Dict[str, Transaction]

    def __hash__(self):
        return hash(self.address)

    def __eq__(self, other):
        if isinstance(other, Address):
            return self.address == other.address
        elif isinstance(other, str):
            return self.address == other


@dataclass
class Wallet:
    name: str
    stake_address: str
    controlled_amount: int
    addresses: List[Address]
    transactions: Dict[str, Transaction]
    rewards: List[Reward]
    active: bool
