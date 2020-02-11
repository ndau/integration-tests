#  ----- ---- --- -- -
#  Copyright 2020 The Axiom Foundation. All Rights Reserved.
# 
#  Licensed under the Apache License 2.0 (the "License").  You may not use
#  this file except in compliance with the License.  You can obtain a copy
#  in the file LICENSE in the source distribution or at
#  https://www.apache.org/licenses/LICENSE-2.0.txt
#  - -- --- ---- -----

import requests
import pytest


# requests codes aren't technically members of their containing objects
# pylint: disable=no-member


@pytest.mark.api
@pytest.mark.parametrize(
    "body,want_status,want_response",
    [
        ([], requests.codes.ok, []),
        (None, requests.codes.bad, None),
        (
            [
                {
                    "address": "zero",
                    "weightedAverageAge": "t0s",
                    "lock": {"noticePeriod": "t0s", "unlocksOn": None, "bonus": 0},
                    "at": "2019-04-03T13:08:50Z",
                }
            ],
            requests.codes.ok,
            [{"address": "zero", "eairate": 0}],
        ),
        (
            [
                {
                    "address": "3L0",
                    "weightedAverageAge": "3m",
                    "lock": {"noticePeriod": "t0s", "unlocksOn": None, "bonus": 0},
                    "at": "2019-04-03T13:13:22Z",
                }
            ],
            requests.codes.ok,
            [{"address": "3L0", "eairate": 40_000_000_000}],
        ),
        (
            [
                {
                    "address": "0L90",
                    "weightedAverageAge": "t0s",
                    "lock": {
                        "noticePeriod": "3m",
                        "unlocksOn": None,
                        "bonus": 10_000_000_000,
                    },
                    "at": "2019-04-03T13:13:22Z",
                }
            ],
            requests.codes.ok,
            [{"address": "0L90", "eairate": 50_000_000_000}],
        ),
        (
            [
                {
                    "address": "90L90",
                    "weightedAverageAge": "3m",
                    "lock": {
                        "noticePeriod": "3m",
                        "unlocksOn": None,
                        "bonus": 10_000_000_000,
                    },
                    "at": "2019-04-03T13:13:22Z",
                },
                {
                    "address": "0L90",
                    "weightedAverageAge": "t0s",
                    "lock": {
                        "noticePeriod": "3m",
                        "unlocksOn": None,
                        "bonus": 10_000_000_000,
                    },
                    "at": "2019-04-03T13:13:22Z",
                },
                {
                    "address": "90L0",
                    "weightedAverageAge": "3m",
                    "lock": {"noticePeriod": "t0s", "unlocksOn": None, "bonus": 0},
                    "at": "2019-04-03T13:13:22Z",
                },
                {
                    "address": "400L1095",
                    "weightedAverageAge": "1y1m5d",
                    "lock": {
                        "noticePeriod": "3y",
                        "unlocksOn": None,
                        "bonus": 50_000_000_000,
                    },
                    "at": "2019-04-03T13:13:22Z",
                },
            ],
            requests.codes.ok,
            [
                {"address": "90L90", "eairate": 80_000_000_000},
                {"address": "0L90", "eairate": 50_000_000_000},
                {"address": "90L0", "eairate": 40_000_000_000},
                {"address": "400L1095", "eairate": 150_000_000_000},
            ],
        ),
    ],
)
def test_get_eai_rate(ndauapi, body, want_status, want_response):
    resp = requests.post(f"{ndauapi}/system/eai/rate", json=body)
    assert resp.status_code == want_status
    if want_response is not None:
        assert resp.json() == want_response
