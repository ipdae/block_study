from flask import Flask
from pytest import fixture

from coin.models import Blockchain
from coin.wsgi import app


@fixture
def fx_blockchain() -> Blockchain:
    return Blockchain()


@fixture
def fx_wsgi_app() -> Flask:
    return app
