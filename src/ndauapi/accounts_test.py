import pytest
import requests
from src.util.random_string import random_string

# requests codes aren't technically members of their containing objects
# pylint: disable=no-member


@pytest.fixture(scope="session")
def accounts_with_history(ndau, rfe):
    # set up some accounts with some history
    names = []
    for _ in range(3):
        name = random_string("test-acct")
        names.append(name)
        ndau(f"account new {name}")
        ndau(f"account claim {name}")
        rfe(1, name)
    for _ in range(5):
        for source in names:
            for dest in names:
                if dest != source:
                    ndau(f"transfer --napu=1 {source} {dest}")

    return names


@pytest.mark.api
@pytest.mark.parametrize(
    "input,expect_code",
    [
        ([], requests.codes.ok),
        (["asdf"], requests.codes.bad),
        ({"addresses": ["asdf"]}, requests.codes.bad),
    ],
)
def test_handle_accounts(ndauapi, input, expect_code):
    resp = requests.post(f"{ndauapi}/account/accounts", json=input)
    assert resp.status_code == expect_code


@pytest.mark.api
@pytest.mark.parametrize(
    "valid_addr,params,want_status,want_body",
    [
        (None, None, requests.codes.bad, "address parameter required"),
        (False, None, requests.codes.bad, "could not validate address"),
        (True, None, requests.codes.ok, None),
        (
            True,
            {"pageindex": "not_a_number"},
            requests.codes.bad,
            "pageindex must be a valid number",
        ),
        (
            True,
            {"pagesize": "not_a_number"},
            requests.codes.bad,
            "pagesize must be a valid number",
        ),
        (True, {"pagesize": -3}, requests.codes.bad, "pagesize must be non-negative"),
        (
            True,
            {"pageindex": 0, "pagesize": 1},
            requests.codes.ok,
            # the first transaction should have zero balance, and must show up
            '"Balance":0',
        ),
        (
            True,
            {"pageindex": -1, "pagesize": 1},
            requests.codes.ok,
            # the first transaction should have zero balance, and must show up
            None,
        ),
    ],
)
def test_account_history(
    ndau, ndauapi, accounts_with_history, valid_addr, params, want_status, want_body
):
    name = accounts_with_history[0]

    # create the url based on the address provided
    if valid_addr is None:
        addr = ""
    elif not valid_addr:
        addr = "invalid"
    else:
        addr = ndau(f"account addr {name}")
    url = f"{ndauapi}/account/history/{addr}"

    # craft the request based on other test params
    if params is None:
        params = {}

    # send request, perform tests
    response = requests.get(url, params=params)
    assert response.status_code == want_status
    assert len(response.text) > 0
    if want_body is not None:
        assert want_body in response.text
