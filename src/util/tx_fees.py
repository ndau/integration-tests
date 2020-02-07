#  ----- ---- --- -- -
#  Copyright 2020 The Axiom Foundation. All Rights Reserved.
# 
#  Licensed under the Apache License 2.0 (the "License").  You may not use
#  this file except in compliance with the License.  You can obtain a copy
#  in the file LICENSE in the source distribution or at
#  https://www.apache.org/licenses/LICENSE-2.0.txt
#  - -- --- ---- -----

import json
from src.util import constants


def ensure_tx_fees(ndau, rfe_to_ssv, fee_script):
    """Set up transaction fees"""
    key = constants.TRANSACTION_FEE_SCRIPT_KEY
    current_script = json.loads(ndau(f"sysvar get {key}"))[key]
    quoted_current = f'"{current_script}"'
    # If the tx fees are already zero, there is nothing to do.
    changed = quoted_current != fee_script
    if changed:
        new_script = fee_script.replace('"', r"\"")
        ndau(f"sysvar set {key} --json {new_script}")

        # Check that it worked.
        current_script = json.loads(ndau(f"sysvar get {key}"))[key]
        assert current_script == fee_script.strip('"')

    yield

    # cleanup and restore existing tx fees
    if changed:
        ndau(f"sysvar set {key} --json '{quoted_current}'")
