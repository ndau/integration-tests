import pytest
import requests

# requests codes aren't technically members of their containing objects
# pylint: disable=no-member


@pytest.mark.api
@pytest.mark.parametrize(
    "height,want_code",
    [
        (1, requests.codes.ok),
        (999_999_999, requests.codes.bad),
        ("high", requests.codes.bad),
    ],
)
def test_block_height(ndauapi, height, want_code):
    resp = requests.get(f"{ndauapi}/block/height/{height}")
    assert resp.status_code == want_code


@pytest.mark.api
def test_block_current_height(ndauapi):
    resp = requests.get(f"{ndauapi}/block/current")
    assert resp.status_code == requests.codes.ok
