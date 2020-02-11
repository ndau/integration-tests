#  ----- ---- --- -- -
#  Copyright 2020 The Axiom Foundation. All Rights Reserved.
# 
#  Licensed under the Apache License 2.0 (the "License").  You may not use
#  this file except in compliance with the License.  You can obtain a copy
#  in the file LICENSE in the source distribution or at
#  https://www.apache.org/licenses/LICENSE-2.0.txt
#  - -- --- ---- -----

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
