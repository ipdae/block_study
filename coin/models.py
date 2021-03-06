import dataclasses
import hashlib
import json
import time
import typing
import urllib.parse

from requests import get
from typeguard import typechecked

from .exc import InvalidBlockError, InvalidTransactionError


__all__ = 'Blockchain'


@dataclasses.dataclass
class Transaction:
    sender: str
    recipient: str
    amount: int
    timestamp: float


@dataclasses.dataclass
class Block:
    index: int
    timestamp: float
    transactions: typing.List[Transaction]
    proof: int
    previous_hash: typing.Union[int, str]

    def __post_init__(self):
        for i, t in enumerate(self.transactions):
            if not isinstance(t, Transaction):
                self.transactions[i] = Transaction(**t)


@dataclasses.dataclass
class Blockchain:

    chain: typing.List[Block] = dataclasses.field(default_factory=list)
    current_transactions: typing.List[Transaction] = dataclasses.field(
        default_factory=list)
    nodes: typing.AbstractSet = dataclasses.field(default_factory=set)

    def __post_init__(self):
        self.new_block(previous_hash=1, proof=100)

    @typechecked
    def new_block(
            self, proof: int,
            previous_hash: typing.Optional[typing.Union[str, int]]=None
    ) -> Block:
        block = Block(
            len(self.chain) + 1,
            time.time(),
            self.current_transactions,
            proof,
            previous_hash or self.hash(self.last_block)
        )
        if self.valid_block(block):
            self.current_transactions = []
            self.chain.append(block)
            return block
        raise InvalidBlockError

    @typechecked
    def new_transaction(self, sender: str, recipient: str, amount: int) -> int:
        transaction = Transaction(
            sender,
            recipient,
            amount,
            time.time()
        )
        if self.valid_transaction(transaction):
            self.current_transactions.append(transaction)
            return self.last_block.index + 1
        raise InvalidTransactionError

    @staticmethod
    @typechecked
    def hash(block: Block) -> str:
        block_string = json.dumps(
            dataclasses.asdict(block), sort_keys=True
        ).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    @typechecked
    def last_block(self) -> Block:
        return self.chain[-1]

    @typechecked
    def pow(self, last_proof: int) -> int:
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    @typechecked
    def valid_proof(last_proof: int, proof: int) -> bool:
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == '0000'

    @typechecked
    def register_node(self, address: str) -> None:
        parsed_url = urllib.parse.urlparse(address)
        self.nodes.add(parsed_url.netloc)

    @typechecked
    def valid_chain(self, chain: typing.List[Block]) -> bool:
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'last_block: {last_block}')
            print(f'block: {block}')
            print('\n----------\n')
            if block.previous_hash != self.hash(last_block):
                return False

            if not self.valid_proof(last_block.proof, block.proof):
                return False

            last_block = block
            current_index += 1

        return True

    @typechecked
    def valid_block(self, block: Block) -> bool:
        try:
            last_block = self.chain[-1]
        except IndexError:
            # genesis block
            return True
        if block.previous_hash != self.hash(last_block):
            return False
        if not self.valid_proof(last_block.proof, block.proof):
            return False
        return True

    @typechecked
    def valid_transaction(self, transaction: Transaction) -> bool:
        if len(self.current_transactions) == 0:
            return True
        latest = self.current_transactions[-1]
        if latest == transaction:
            return True
        elif latest.timestamp < transaction.timestamp:
            return True
        return False

    @typechecked
    def resolve_conflicts(self) -> bool:
        new_chain = None
        max_length = len(self.chain)

        for node in self.nodes:
            response = get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain_list = response.json()['chain']
                try:
                    chain = [Block(**chain) for chain in chain_list]
                except TypeError:
                    return False

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain
        if new_chain:
            self.chain = new_chain
            return True
        return False
