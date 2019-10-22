import requests
import pytest


# requests codes aren't technically members of their containing objects
# pylint: disable=no-member


@pytest.mark.api
@pytest.mark.parametrize(
    "path",
    [
        "node/abci",
        "node/consensus",
        "node/genesis",
        "node/health",
        "node/net",
        "node/nodes",
    ],
)
def test_simple_query(ndauapi, path):
    resp = requests.get(f"{ndauapi}/{path}")
    assert resp.status_code == requests.codes.ok

# JSG this test used to infinite loop, now test we get appropriate error msg
def test_malformed_node_query(ndauapi):
    resp = requests.get(f"{ndauapi}/node/statuss")
    assert resp.status_code == requests.codes.not_found
    respj = resp.json()
    assert respj["msg"] == "could not find node: statuss"
