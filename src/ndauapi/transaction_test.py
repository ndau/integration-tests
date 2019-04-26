import base64
import hashlib
import json
import pytest
import requests
from tempfile import NamedTemporaryFile
from urllib.parse import quote as urlquote
from src.util.random_string import random_string

# requests codes aren't technically members of their containing objects
# pylint: disable=no-member


@pytest.fixture(scope="session")
def claim_json(ndau):
    name = random_string("json-acct")
    ndau(f"account new {name}")
    # JSG must rfe before claim to pay for tx fees
    ndau(f"rfe 10 {name}")
    return json.loads(ndau(f"-j account claim {name}"))


@pytest.fixture(scope="session")
def claim_file(claim_json):
    with NamedTemporaryFile(mode="w+t") as tf:
        json.dump(claim_json, tf)
        tf.flush()
        yield tf.name


@pytest.fixture(scope="session")
def claim_signable_bytes(ndau, claim_file):
    signable_bytes_b64 = ndau(f"signable-bytes --strip claim {claim_file}")
    return base64.b64decode(signable_bytes_b64, validate=True)


@pytest.fixture(scope="session")
def claim_txhash(claim_signable_bytes):
    """
    Compute the tx hash of the claim tx.

    Defined in
    https://github.com/oneiro-ndev/metanode/
            blob/0f1c08ce1863f6950738932dc30ddaf8d8e66809/
            pkg/meta/transaction/transactable.go#L163-L166
    """
    return (
        base64.b64encode(hashlib.md5(claim_signable_bytes).digest())
        .decode("utf-8")
        .strip("=")
    )


@pytest.fixture(scope="session")
def claim(ndau, claim_file):
    return ndau(f"-v send claim {claim_file}")


@pytest.mark.api
@pytest.mark.parametrize(
    "send_hash,want_status,want_body",
    [
        (None, requests.codes.bad, "txhash parameter required"),
        (False, requests.codes.ok, "null"),
        # just ensure we got a real-looking tx back
        (True, requests.codes.ok, '{"Tx":{"Nonce":'),
    ],
)
def test_tx_hash(ndauapi, claim, claim_txhash, send_hash, want_status, want_body):
    if send_hash is None:
        hash = ""
    elif send_hash:
        hash = claim_txhash
    else:
        hash = "invalid hash"

    resp = requests.get(f"{ndauapi}/transaction/{urlquote(hash, safe='')}")
    assert resp.status_code == want_status
    assert want_body in resp.text
