import base64
import json
import msgpack
import requests
import pytest
from src.util.random_string import random_string


# requests codes aren't technically members of their containing objects
# pylint: disable=no-member


@pytest.mark.api
def test_sysvar_history(ndau, ndauapi):
    # Fill a new sysvar with some history so it won't conflict with another
    # sysvar's history.
    count = 3
    sysvar = random_string()
    for i in range(count):
        ndau(f"sysvar set {sysvar} bar{i}")

    # Get history.
    resp = requests.get(f"{ndauapi}/system/history/{sysvar}")
    assert resp.status_code == requests.codes.ok

    # Validate each element in the response.
    data = json.loads(resp.text)
    history = data["history"]
    assert len(history) == count
    last_height = 0
    for i in range(count):
        history_i = history[i]
        h = history_i["height"]
        v = history_i["value"]

        height = int(h)
        assert height > last_height
        last_height = height

        value = base64.b64decode(v).decode("utf-8")
        assert value == f"bar{i}"


@pytest.mark.api
def test_sysvar(ndauapi, ndau):
    resp = requests.get(f"{ndauapi}/system/all")
    assert resp.status_code == requests.codes.ok

    sysvars = resp.json()

    assert "TransactionFeeScript" in sysvars
    print("TransactionFeeScript:", sysvars["TransactionFeeScript"])
    fee_bytes = base64.b64decode(sysvars["TransactionFeeScript"], validate=True)

    # shouldn't be msgp
    with pytest.raises(Exception):
        msgpack.loads(fee_bytes)

    # double-check against output from ndau tool, which we know unpacks things properly
    tool_fee = json.loads(ndau("sysvar get TransactionFeeScript"))[
        "TransactionFeeScript"
    ]
    assert tool_fee == sysvars["TransactionFeeScript"]

