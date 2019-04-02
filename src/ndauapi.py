import pytest
import requests

# requests codes aren't technically members of their containing objects
# pylint: disable=no-member


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
