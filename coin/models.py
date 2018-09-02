import dataclasses
import hashlib
import json
import time
import typing
import urllib.parse

from requests import get
from typeguard import typechecked


__all__ = 'Blockchain'


@dataclasses.dataclass
class Transaction:
    sender: str
    recipient: str
    amount: int


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


class Blockchain:

    def __init__(self):
        self.chain = []
        self.current_transations = []
        self.nodes = set()

        self.new_block(previous_hash=1, proof=100)

    @typechecked
    def new_block(
            self, proof: int,
            previous_hash: typing.Optional[typing.Union[str, int]]=None
    ) -> Block:
        block = Block(
            len(self.chain) + 1,
            time.time(),
            self.current_transations,
            proof,
            previous_hash or self.hash(self.last_block)
        )
        self.current_transations = []
        self.chain.append(block)
        return block

    @typechecked
    def new_transaction(self, sender: str, recipient: str, amount: int) -> int:
        transaction = Transaction(
            sender,
            recipient,
            amount
        )
        self.current_transations.append(transaction)
        return self.last_block.index + 1

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
