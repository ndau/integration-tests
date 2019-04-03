import pytest
import requests

# requests codes aren't technically members of their containing objects
# pylint: disable=no-member


@pytest.fixture
def min_height(ndauapi):
    MIN_HEIGHT = 3
    resp = requests.get(f"{ndauapi}/block/current")
    if resp.status_code != requests.codes.ok:
        pytest.skip(f"failed to get current height; need min {MIN_HEIGHT}")
    chain_height = resp.json()["block"]["header"]["height"]
    if chain_height < MIN_HEIGHT:
        pytest.skip(
            f"this test requires a min block height of {MIN_HEIGHT} "
            f"but current chain height is {chain_height}"
        )


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


@pytest.mark.api
@pytest.mark.parametrize(
    "start,end,want_code",
    [
        ("one", 2, requests.codes.bad),  # not a number
        (0, 2, requests.codes.bad),  # start too low
        (1, 0, requests.codes.bad),  # end too low
        (4, 2, requests.codes.bad),  # start > end
        (1, 102, requests.codes.bad),  # range > 100
        (3, 3, requests.codes.ok),
        (1, 2, requests.codes.ok),
    ],
)
def test_block_range(ndauapi, min_height, start, end, want_code):
    resp = requests.get(f"{ndauapi}/block/range/{start}/{end}")
    assert resp.status_code == want_code


@pytest.mark.api
@pytest.mark.parametrize(
    "start,end,want_code",
    [
        ("one", "2018-07-10T20:01:02Z", requests.codes.bad),  # not a date
        ("2018-07-10T20:01:02Z", "2018-07-10T20:01:02Z", requests.codes.ok),
        ("2018-07-10T00:00:00Z", "2018-07-11T00:00:00Z", requests.codes.ok),
    ],
)
def test_block_date_range(ndauapi, min_height, start, end, want_code):
    resp = requests.get(f"{ndauapi}/block/daterange/{start}/{end}")
    assert resp.status_code == want_code
