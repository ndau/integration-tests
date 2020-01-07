import base64
import hashlib
import json
import time
from tempfile import NamedTemporaryFile

import pytest
import requests

from src.util.random_string import random_string

# requests codes aren't technically members of their containing objects
# pylint: disable=no-member


@pytest.fixture(scope="session")
def set_validation_json(ndau):
    name = random_string("json-acct")
    ndau(f"account new {name}")
    # JSG must rfe before set_validation to pay for tx fees
    ndau(f"rfe 10 {name}")
    return json.loads(ndau(f"-j account set-validation {name}"))


@pytest.fixture(scope="session")
def set_validation_file(set_validation_json):
    with NamedTemporaryFile(mode="w+t") as tf:
        json.dump(set_validation_json, tf)
        tf.flush()
        yield tf.name


@pytest.fixture(scope="session")
def set_validation_signable_bytes(ndau, set_validation_file):
    signable_bytes_b64 = ndau(
        f"signable-bytes --strip set-validation {set_validation_file}"
    )
    return base64.b64decode(signable_bytes_b64, validate=True)


@pytest.fixture(scope="session")
def set_validation_txhash(set_validation_signable_bytes):
    """
    Compute the tx hash of the set_validation tx.

    Defined in
    https://github.com/oneiro-ndev/metanode/
            blob/0f1c08ce1863f6950738932dc30ddaf8d8e66809/
            pkg/meta/transaction/transactable.go#L163-L166
    """
    return (
        base64.urlsafe_b64encode(hashlib.md5(set_validation_signable_bytes).digest())
        .decode("utf-8")
        .strip("=")  # tx hashes do not include base64 padding characters
    )


@pytest.fixture(scope="session")
def set_validation(ndau, set_validation_file):
    return ndau(f"-v send set-validation {set_validation_file}")


@pytest.mark.api
@pytest.mark.parametrize(
    "txhash,want_status,want_body",
    [
        ("", requests.codes.bad, "txhash parameter required"),
        ("invalid-hash", requests.codes.ok, "null"),
        # just ensure we got a real-looking tx back
        (None, requests.codes.ok, '"BlockHeight":'),
    ],
)
def test_tx_hash(
    ndauapi, set_validation, set_validation_txhash, txhash, want_status, want_body
):
    if txhash is None:
        txhash = set_validation_txhash

    resp = requests.get(f"{ndauapi}/transaction/detail/{txhash}")
    print(resp.text)
    assert resp.status_code == want_status
    assert want_body in resp.text


@pytest.mark.api
@pytest.mark.parametrize(
    "txhash,want_status,want_body",
    [
        ("", requests.codes.bad, "txhash parameter required"),
        # Successful response, but no transactions in the list.
        ("invalid-hash", requests.codes.ok, '{"Txs":null,"NextTxHash":""}'),
        # Successful response, with at least one transaction in the list.
        ("start", requests.codes.ok, '{"Txs":[{"BlockHeight":'),
        # Successful response, with at least one transaction in the list.
        (
            "start?type=X&type=SetValidation&limit=1",
            requests.codes.ok,
            '{"Txs":[{"BlockHeight":',
        ),
        # Successful response, with at least one transaction in the list.
        (None, requests.codes.ok, '{"Txs":[{"BlockHeight":'),
    ],
)
def test_tx_before_hash(
    ndauapi, set_validation, set_validation_txhash, txhash, want_status, want_body
):
    if txhash is None:
        txhash = set_validation_txhash

    resp = requests.get(f"{ndauapi}/transaction/before/{txhash}")
    assert resp.status_code == want_status
    assert want_body in resp.text


@pytest.mark.api
def test_tx_prevalidate_and_submit(ndauapi, ndau, ndautool_toml):
    # Any transaction will do.  Here we RFE to the rfe address.
    txtype = "ReleaseFromEndowment"
    name = random_string("prevalsubmit-acct")
    ndau(f"account new {name}")
    tx = json.loads(ndau(f"-j rfe 1 {name}"))

    # We need the tx in a temp file to get the signable bytes.
    tf = NamedTemporaryFile(mode="w+t")
    json.dump(tx, tf)
    tf.flush()
    tx_file = tf.name

    # We can calculate the expected tx hash before we submit the transaction.
    signable_bytes_b64 = ndau(f"signable-bytes --strip {txtype} {tx_file}")
    signable_bytes = base64.b64decode(signable_bytes_b64, validate=True)
    txhash = (
        base64.urlsafe_b64encode(hashlib.md5(signable_bytes).digest())
        .decode("utf-8")
        .strip("=")  # tx hashes do not include base64 padding characters
    )

    # We expect the next transactions to succeed when posted.
    want_body = f'"hash":"{txhash}"'
    want_status = requests.codes.ok

    # Prevalidate new tx.
    resp = requests.post(f"{ndauapi}/tx/prevalidate/{txtype}", json=tx)
    assert resp.status_code == want_status
    assert want_body in resp.text

    # Submit new tx.
    resp = requests.post(f"{ndauapi}/tx/submit/{txtype}", json=tx)
    assert resp.status_code == want_status
    assert want_body in resp.text

    # We'll repost the same transactions for expected no-ops.
    want_status = requests.codes.accepted

    # Prevalidate tx again.
    resp = requests.post(f"{ndauapi}/tx/prevalidate/{txtype}", json=tx)
    assert resp.status_code == want_status
    assert want_body in resp.text

    # Submit tx again.
    resp = requests.post(f"{ndauapi}/tx/submit/{txtype}", json=tx)
    assert resp.status_code == want_status
    assert want_body in resp.text
