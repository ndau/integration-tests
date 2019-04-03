import requests
import pytest


# requests codes aren't technically members of their containing objects
# pylint: disable=no-member


@pytest.mark.api
def test_get_health(ndauapi):
    resp = requests.get(f"{ndauapi}/node/health")
    assert resp.status_code == requests.codes.ok
