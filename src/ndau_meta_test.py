"""
Test that the fixtures we build work properly.
"""

import subprocess
import pytest

from src.util.subp import subp


@pytest.mark.api
@pytest.mark.meta
def test_ndauapi(ndauapi_exists):
    # see https://tendermint.readthedocs.io/en/master/getting-started.html
    try:
        print(f'address: {ndauapi_exists["address"]}')

        subp(
            f'curl -s http://{ndauapi_exists["address"]}:'
            f'{ndauapi_exists["nodenet0_rpc"]}/status'
        )

    except subprocess.CalledProcessError as e:
        print("--STDOUT--")
        print(e.stdout)
        print("--RETURN CODE--")
        print(e.returncode)
        raise


@pytest.mark.meta
def test_ndau_node_connection(ndau):
    ndau("-v version check")

