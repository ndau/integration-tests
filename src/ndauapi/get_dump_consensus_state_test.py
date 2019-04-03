import requests
import pytest


# requests codes aren't technically members of their containing objects
# pylint: disable=no-member


@pytest.mark.api
def test_dump_consensus_state(ndauapi):
    resp = requests.get(f"{ndauapi}/node/consensus")
    assert resp.status_code == requests.codes.ok
