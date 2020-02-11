#  ----- ---- --- -- -
#  Copyright 2020 The Axiom Foundation. All Rights Reserved.
# 
#  Licensed under the Apache License 2.0 (the "License").  You may not use
#  this file except in compliance with the License.  You can obtain a copy
#  in the file LICENSE in the source distribution or at
#  https://www.apache.org/licenses/LICENSE-2.0.txt
#  - -- --- ---- -----

import json
import pytest
import requests

# requests codes aren't technically members of their containing objects
# pylint: disable=no-member


@pytest.fixture(scope="module")
def node_id(ndau):
    return json.loads(ndau("info"))["node_info"]["id"]


@pytest.mark.api
def test_netinfo(ndauapi, node_id):
    resp = requests.get(f"{ndauapi}/node/{node_id}")
    assert resp.status_code == requests.codes.ok
