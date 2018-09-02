import json
import typing
import unittest.mock

from flask import Flask
from pytest import mark
from typeguard import typechecked

from coin.models import Block, Blockchain, Transaction


def test_index(fx_wsgi_app: Flask):
    with fx_wsgi_app.test_client() as client:
        res = client.get('/')
        assert res.status_code == 200
        assert res.get_data(as_text=True) == 'ping'


def test_mine(fx_wsgi_app: Flask):
    with fx_wsgi_app.test_client() as client:
        blockchain = fx_wsgi_app.blockchain
        block = blockchain.last_block
        res = client.get('/mine')
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert data['message'] == 'New Block Forged'
        assert data['index'] == 2
        assert blockchain.last_block.transactions == [
            Transaction(**t) for t in data['transactions']
        ]
        assert data['proof'] == blockchain.pow(block.proof)
        assert data['previous_hash'] == blockchain.hash(block)
        assert len(blockchain.chain) == 2


def test_new_transaction(fx_wsgi_app: Flask):
    with fx_wsgi_app.test_client() as client:
        blockchain = fx_wsgi_app.blockchain
        assert blockchain.current_transactions == []
        res = client.post(
            '/transactions/new',
            data=json.dumps({
                'sender': 'sender',
                'recipient': 'recipient',
                'amount': 1000,
            }),
            content_type='application/json',
        )
        assert res.status_code == 201
        assert len(blockchain.current_transactions) == 1
        transaction = blockchain.current_transactions[-1]
        assert transaction.sender == 'sender'
        assert transaction.recipient == 'recipient'
        assert transaction.amount == 1000


@typechecked
@mark.parametrize('sender, recipient, amount', [
    (None, None, None),
    (None, 'recipient', None),
    (None, 'recipient', 0),
    (None, 'recipient', 1),
    (None, None, 1),
    (None, None, 0),
    ('sender', None, None),
    ('sender', 'recipient', None),
    ('sender', None, 1),
    ('sender', None, 0),
    ('sender', '', 1),
    ('sender', 'recipient', 0),
    ('', '', 1),
    ('', 'recipient', 1),
    ('', 'recipient', 0),
])
def test_new_transaction_bad_request(
        fx_wsgi_app: Flask,
        sender: typing.Union[str, None],
        recipient: typing.Union[str, None],
        amount: typing.Union[int, None]
):
    with fx_wsgi_app.test_client() as client:
        res = client.post(
            '/transactions/new',
            data=json.dumps({
                'sender': sender,
                'recipient': recipient,
                'amount': amount,
            }),
            content_type='application/json',
        )
        assert res.status_code == 400


def test_full_chain(fx_wsgi_app: Flask):
    with fx_wsgi_app.test_client() as client:
        blockchain = fx_wsgi_app.blockchain
        res = client.get('/chain')
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert [Block(**b) for b in data['chain']] == blockchain.chain
        assert data['length'] == len(blockchain.chain)


def test_register_node(fx_wsgi_app: Flask):
    with fx_wsgi_app.test_client() as client:
        blockchain = fx_wsgi_app.blockchain
        assert blockchain.nodes == set()
        nodes = ['http://www.google.co.kr']
        res = client.post(
            '/nodes/register',
            data=json.dumps({
                'nodes': nodes
            }),
            content_type='application/json',
        )
        assert res.status_code == 201
        assert blockchain.nodes == {'www.google.co.kr'}


def test_register_node_bad_request(fx_wsgi_app: Flask):
    with fx_wsgi_app.test_client() as client:
        res = client.post(
            '/nodes/register',
            data=json.dumps({
                'invalid': 'test',
            }),
            content_type='application/json',
        )
        assert res.status_code == 400


@typechecked
@mark.parametrize('replaced, message, key', [
    (True, 'Our chain is replaced', 'new_chain'),
    (False, 'Our chain is authoritative', 'chain')
])
def test_consensus_replaced(fx_wsgi_app: Flask, replaced: bool, message: str,
                            key: str):
    m = unittest.mock.patch.object(Blockchain, 'resolve_conflicts',
                                   return_value=replaced)
    client = fx_wsgi_app.test_client()
    blockchain = fx_wsgi_app.blockchain
    with m, client:
        res = client.get('/nodes/resolve')
        assert res.status_code == 200
        data = json.loads(res.get_data(as_text=True))
        assert data['message'] == message
        assert [Block(**b) for b in data[key]] == blockchain.chain
