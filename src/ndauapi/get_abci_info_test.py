import requests
import pytest


# requests codes aren't technically members of their containing objects
# pylint: disable=no-member


@pytest.mark.api
def test_abci_info(ndauapi):
    resp = requests.get(f"{ndauapi}/node/abci")
    assert resp.status_code == requests.codes.ok
