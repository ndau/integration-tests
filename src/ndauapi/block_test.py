import pytest
import requests
from src.util.random_string import random_string

# requests codes aren't technically members of their containing objects
# pylint: disable=no-member


@pytest.fixture(scope="module")
def current_block(set_up_account, ndauapi):
    # the hash doesn't get recorded unless there is a tx in it.
    # simplest way to accomplish that is to set up a random account real quick.
    set_up_account(random_string("create-block-for-hash"))
    resp = requests.get(f"{ndauapi}/block/current")
    if resp.status_code != requests.codes.ok:
        pytest.skip(f"failed to get current block data")
    return resp.json()


@pytest.fixture(scope="module")
def current_hash(current_block):
    return current_block["block_meta"]["block_id"]["hash"]


@pytest.fixture(scope="module")
def current_height(current_block):
    return current_block["block_meta"]["header"]["height"]


@pytest.fixture(scope="module")
def min_height(current_height):
    MIN_HEIGHT = 3
    if current_height < MIN_HEIGHT:
        pytest.skip(
            f"this test requires a min block height of {MIN_HEIGHT} "
            f"but current chain height is {current_height}"
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


@pytest.mark.api
@pytest.mark.parametrize(
    "send_valid_hash,want_code,want_body",
    [
        (None, requests.codes.bad, "blockhash parameter required"),
        (False, requests.codes.ok, "null"),  # response is empty, so produces null
        # note: this test currently fails. I don't know why, but I suspect we're
        # searching for the wrong hash. That said,
        (True, requests.codes.ok, None),  # should include hash we searched for
    ],
)
def test_block_hash(ndauapi, current_hash, send_valid_hash, want_code, want_body):
    if send_valid_hash is None:
        hash = ""
    elif send_valid_hash:
        hash = current_hash
    else:
        hash = "invalid"

    resp = requests.get(f"{ndauapi}/block/hash/{hash}")
    print(resp.url)
    assert resp.status_code == want_code
    if want_body is None:
        want_body = current_hash
    assert want_body in resp.text


@pytest.mark.api
def test_block_transactions(ndauapi, current_height):
    resp = requests.get(f"{ndauapi}/block/transactions/{current_height}")
    assert resp.status_code == requests.codes.ok
