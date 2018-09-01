import dataclasses
import time
import typing
import unittest.mock
import urllib.parse

from pytest import mark
from requests_mock import Mocker
from typeguard import typechecked

from coin.models import Block, Blockchain, Transaction


def test_block_chain():
    blockchain = Blockchain()
    block = blockchain.chain[0]
    assert isinstance(block, Block)
    assert block.index == 1
    assert block.transactions == []
    assert block.proof == 100
    assert block.previous_hash == 1
    assert blockchain.current_transations == []
    assert blockchain.nodes == set()


@typechecked
@mark.parametrize('proof, previous_hash, expected', [
    (1, None, str),
    (1, 1, int),
    (1, '1', str),
])
def test_new_block(fx_blockchain: Blockchain,
                   proof: int,
                   previous_hash: typing.Union[str, int, None],
                   expected: typing.types):
    block = fx_blockchain.new_block(proof, previous_hash)
    assert isinstance(block.previous_hash, expected)


def test_new_transaction(fx_blockchain: Blockchain):
    block = fx_blockchain.last_block
    assert block.index == 1
    assert fx_blockchain.current_transations == []
    result = fx_blockchain.new_transaction('0', 'test', 1)
    assert result == 2
    transaction = fx_blockchain.current_transations[0]
    assert isinstance(transaction, Transaction)
    assert transaction.sender == '0'
    assert transaction.recipient == 'test'
    assert transaction.amount == 1


def test_hash(fx_blockchain: Blockchain):
    result = fx_blockchain.hash(fx_blockchain.last_block)
    assert isinstance(result, str)


def test_last_block(fx_blockchain: Blockchain):
    block = fx_blockchain.chain[0]
    assert fx_blockchain.last_block == block
    new_block = fx_blockchain.new_block(previous_hash=2, proof=10)
    assert fx_blockchain.last_block == new_block


def test_valid_proof(fx_blockchain: Blockchain):
    assert fx_blockchain.valid_proof(0, 0) in (True, False)


@typechecked
@mark.parametrize('address, expected', [
    ('http://www.google.com', 'www.google.com'),
    ('https://www.google.com', 'www.google.com'),
])
def test_register_node(fx_blockchain: Blockchain, address: str, expected: str):
    assert fx_blockchain.nodes == set()
    fx_blockchain.register_node(address)
    assert fx_blockchain.nodes == {expected}


def test_valid_chain(fx_blockchain: Blockchain):
    assert fx_blockchain.valid_chain(fx_blockchain.chain) is True


@mark.parametrize('previous_hash', [
    '',
    'test',
])
def test_valid_chain_invalid_hash(fx_blockchain: Blockchain,
                                  previous_hash: str):
    block = Block(2, time.time(), fx_blockchain.current_transations, 10,
                  previous_hash)
    chain = fx_blockchain.chain
    chain.append(block)
    assert not block.previous_hash == fx_blockchain.hash(chain[0])
    assert fx_blockchain.valid_chain(fx_blockchain.chain) is False


def test_valid_chain_invalid_proof(fx_blockchain: Blockchain):
    block = fx_blockchain.new_block(10)
    assert len(fx_blockchain.chain) == 2
    assert block.previous_hash == fx_blockchain.hash(fx_blockchain.chain[0])
    with unittest.mock.patch.object(Blockchain, 'valid_proof',
                                    return_value=False):
        assert fx_blockchain.valid_chain(fx_blockchain.chain) is False


def test_resolve_conflicts(fx_blockchain: Blockchain):
    url = 'http://www.google.com'
    fx_blockchain.register_node(url)
    with Mocker() as m:
        url = urllib.parse.urljoin(url, '/chain')
        m.get(url, status_code=200, json={
            'length': len(fx_blockchain.chain) + 1,
            'chain': [dataclasses.asdict(b) for b in fx_blockchain.chain],
        })
        assert fx_blockchain.resolve_conflicts() is True


@typechecked
@mark.parametrize('length, chain', [
    (0, [{}]),
    (2, [{}]),
])
def test_resolve_conflicts_false(fx_blockchain: Blockchain, length: int,
                                 chain: list):
    url = 'http://www.google.com'
    fx_blockchain.register_node(url)
    with Mocker() as m:
        url = urllib.parse.urljoin(url, '/chain')
        m.get(url, status_code=200, json={
            'length': length,
            'chain': chain
        })
        assert fx_blockchain.resolve_conflicts() is False
