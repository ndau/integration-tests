"""
Test that the fixtures we build work properly.
"""

import pytest

from src.util.subp import subpv

@pytest.mark.meta
def test_tm_status(netconf):
    # see https://tendermint.readthedocs.io/en/master/getting-started.html
    subpv(f'curl -s {netconf["address"]}:' f'{netconf["nodenet0_rpc"]}/status')


@pytest.mark.meta
def test_ndau_node_connection(ndau):
    # "version remote" ensures we connect properly not just to TM but also to the
    # remote node via its query ABCI cmd
    ndau("-v version remote")

