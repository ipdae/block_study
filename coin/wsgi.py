import dataclasses
import uuid

from flask import Flask, jsonify, request
from werkzeug.exceptions import BadRequest

from .models import Blockchain


__all__ = 'app'

app = Flask(__name__)
node_identifier = str(uuid.uuid4()).replace('-', '')
app.blockchain = blockchain = Blockchain()


@app.route('/mine')
def mine():
    last_block = blockchain.last_block
    last_proof = last_block.proof
    proof = blockchain.pow(last_proof)
    blockchain.new_transaction(
        sender='0',
        recipient=node_identifier,
        amount=1,
    )
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)
    response = {
        'message': 'New Block Forged',
        'index': block.index,
        'transactions': [dataclasses.asdict(t) for t in block.transactions],
        'proof': block.proof,
        'previous_hash': block.previous_hash,
    }
    return jsonify(response)


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    payload = request.get_json()
    required = ['sender', 'recipient', 'amount']
    if not all(payload.get(k) for k in required):
        raise BadRequest
    try:
        index = blockchain.new_transaction(
            payload['sender'], payload['recipient'], payload['amount']
        )
    except TypeError:
        raise BadRequest
    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/chain')
def full_chain():
    response = {
        'chain': [dataclasses.asdict(b) for b in blockchain.chain],
        'length': len(blockchain.chain),
    }
    return jsonify(response)


@app.route('/nodes/register', methods=['POST'])
def register_node():
    payload = request.get_json()
    try:
        nodes = payload['nodes']
    except KeyError:
        raise BadRequest

    for node in nodes:
        blockchain.register_node(node)
    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain is replaced',
            'new_chain': [dataclasses.asdict(b) for b in blockchain.chain],
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': [dataclasses.asdict(b) for b in blockchain.chain],
        }
    return jsonify(response)


@app.route('/')
def index():
    return 'ping'
