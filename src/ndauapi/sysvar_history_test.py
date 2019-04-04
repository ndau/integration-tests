import base64
import json
import requests
import pytest
from src.util.random_string import random_string


# requests codes aren't technically members of their containing objects
# pylint: disable=no-member


@pytest.mark.api
def test_sysvar_history(ndau, ndauapi):
    # Fill a new sysvar with some history so it won't conflict with another sysvar's history.
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
