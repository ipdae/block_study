from pytest import fixture

from coin.models import Blockchain


@fixture
def fx_blockchain() -> Blockchain:
    return Blockchain()
