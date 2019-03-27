import json
from src.util import constants


def ensure_tx_fees(ndau, rfe_to_ssv, fee_script):
    """Set up transaction fees"""
    key = constants.TRANSACTION_FEE_SCRIPT_KEY
    current_script = json.loads(ndau(f"sysvar get {key}"))[key]
    quoted_current = f'"{current_script}"'
    # If the tx fees are already zero, there is nothing to do.
    if quoted_current != fee_script:
        new_script = fee_script.replace('"', r"\"")
        ndau(f"sysvar set {key} --json {new_script}")

        # Check that it worked.
        current_script = json.loads(ndau(f"sysvar get {key}"))[key]
        assert current_script == fee_script.strip('"')

    yield

    # cleanup and restore existing tx fees
    ndau(f"sysvar set {key} --json '{quoted_current}'")
