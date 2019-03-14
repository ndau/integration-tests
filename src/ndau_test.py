"""Tests that the ndau blockchain operates as expected."""

import base64
import json
import src.util.constants as constants
from time import sleep


def test_get_ndau_status(node_net, ndau):
    """`ndautool` can connect to `ndau node` and get status."""
    info = json.loads(ndau("info"))
    moniker = info["node_info"]["moniker"]
    assert moniker == f"{node_net}-0"


def test_create_account(ndau, rfe, ensure_post_genesis_tx_fees, random_string):
    """Create account, RFE to it, and check attributes"""
    _random_string = random_string("generic")
    known_ids = ndau("account list").splitlines()
    # make sure account does not already exist
    assert not any(_random_string in id_line for id_line in known_ids)
    # create new randomly named account
    ndau(f"account new {_random_string}")
    new_ids = ndau("account list").splitlines()
    # check that account now exists
    assert any(_random_string in id_line for id_line in new_ids)
    id_line = [s for s in new_ids if _random_string in s]
    # check that account is not claimed (has 0 tx keys)
    assert "(0 tr keys)" in id_line[0]
    account_data = json.loads(ndau(f"account query {_random_string}"))
    assert account_data["validationKeys"] is None
    # RFE to account 10 ndau
    orig_ndau = 10
    orig_napu = orig_ndau * 1e8
    rfe(orig_ndau, _random_string)
    account_data = json.loads(ndau(f"account query {_random_string}"))
    # check that account balance is 10 ndau
    assert account_data["balance"] == orig_napu
    # We want to test non-zero transaction fees.
    ensure_post_genesis_tx_fees()
    # claim account, and check that account now has validation keys
    ndau(f"account claim {_random_string}")
    account_data = json.loads(ndau(f"account query {_random_string}"))
    assert account_data["validationKeys"] is not None
    # check that 1 napu tx fee was deducted from account
    assert account_data["balance"] == orig_napu - constants.ONE_NAPU_FEE


# This test purposely positioned after one where tx fees are changed to non-zero,
# which requires genesis to have been performed.  This was useful when ensuring
# perform_genesis() is only ever called once per test session.  We don't need
# to keep this here, but it doesn't hurt.  Still, we leave it here since it
# eases debugability of these tests.
def test_genesis(perform_genesis):
    """Simulate genesis operations, even if they've happened already."""
    perform_genesis()


def test_transfer(ndau, ensure_post_genesis_tx_fees, random_string, set_up_account):
    """Test Transfer transaction"""

    # We want to test non-zero transaction fees.
    ensure_post_genesis_tx_fees()

    # Set up accounts to transfer between.
    account1 = random_string("xfer1")
    set_up_account(account1)
    account2 = random_string("xfer2")
    set_up_account(account2)

    orig_ndau = 10  # from set_up_account()
    orig_napu = orig_ndau * 1e8
    xfer_ndau = 1  # We'll transfer this amount
    xfer_napu = xfer_ndau * 1e8

    # One napu for the claim transaction.
    account_data1 = json.loads(ndau(f"account query {account1}"))
    assert account_data1["balance"] == orig_napu - constants.ONE_NAPU_FEE

    # Transfer
    ndau(f"transfer {xfer_ndau} {account1} {account2}")
    account_data1 = json.loads(ndau(f"account query {account1}"))
    account_data2 = json.loads(ndau(f"account query {account2}"))
    # Subtract one napu for the claim transaction, one for the transfer.
    assert (
        account_data1["balance"] == orig_napu - xfer_napu - 2 * constants.ONE_NAPU_FEE
    )
    assert account_data1["lock"] is None
    # Subtract one napu for the claim transaction.
    assert account_data2["balance"] == orig_napu + xfer_napu - constants.ONE_NAPU_FEE
    assert account_data2["lock"] is None


def test_transfer_lock(
    ndau, ensure_post_genesis_tx_fees, random_string, set_up_account
):
    """Test TransferLock transaction"""

    # We want to test non-zero transaction fees.
    ensure_post_genesis_tx_fees()

    # Set up source claimed account with funds.
    account1 = random_string("xferlock1")
    set_up_account(account1)

    # Create destination account, but don't claim or rfe to it
    # (otherwise transfer-lock fails).
    account2 = random_string("xferlock2")
    ndau(f"account new {account2}")

    orig_ndau = 10  # from set_up_account()
    orig_napu = orig_ndau * 1e8
    xfer_ndau = 1  # We'll transfer this amount
    xfer_napu = xfer_ndau * 1e8

    # One napu for the claim transaction.
    account_data1 = json.loads(ndau(f"account query {account1}"))
    assert account_data1["balance"] == orig_napu - constants.ONE_NAPU_FEE

    # TransferLock
    lock_months = 3
    ndau(f"transfer-lock {xfer_ndau} {account1} {account2} {lock_months}m")
    account_data1 = json.loads(ndau(f"account query {account1}"))
    account_data2 = json.loads(ndau(f"account query {account2}"))
    # Subtract one napu for the claim transaction, one for the transfer-lock.
    assert (
        account_data1["balance"] == orig_napu - xfer_napu - 2 * constants.ONE_NAPU_FEE
    )
    assert account_data1["lock"] is None
    # No claim transaction, no fee.  Just gain the amount transferred.
    assert account_data2["balance"] == xfer_napu
    assert account_data2["lock"] is not None
    assert account_data2["lock"]["unlocksOn"] is None


def test_lock_notify(ndau, random_string, set_up_account):
    """Test Lock and Notify transactions"""

    # Set up account to lock.
    account = random_string("lock-notify")
    set_up_account(account)

    # Lock
    lock_months = 3
    ndau(f"account lock {account} {lock_months}m")
    account_data = json.loads(ndau(f"account query {account}"))
    assert account_data["lock"] is not None
    assert account_data["lock"]["unlocksOn"] is None

    # Notify
    ndau(f"account notify {account}")
    account_data = json.loads(ndau(f"account query {account}"))
    assert account_data["lock"] is not None
    assert account_data["lock"]["unlocksOn"] is not None


def test_change_settlement_period(ndau, random_string, set_up_account):
    """Test ChangeSettlementPeriod transaction"""

    # Pick something that we wouldn't ever use as a default.  That way, we can assert on the
    # initial value is not this (rather than assserting on the default value, which would fail
    # if we ever changed it).  We will then change the settlement period to this and assert.
    new_period = "2m3dt5h7m11s"

    # Set up a new account, which will have the default settlement period.
    account = random_string("settlement-period")
    set_up_account(account)
    account_data = json.loads(ndau(f"account query {account}"))
    assert account_data["settlementSettings"] is not None
    old_period = account_data["settlementSettings"]["period"]
    assert old_period is not None
    assert old_period != ""
    assert old_period != new_period
    assert account_data["settlementSettings"]["next"] is None

    # ChangeSettlementPeriod
    ndau(f"account change-settlement-period {account} {new_period}")
    account_data = json.loads(ndau(f"account query {account}"))
    assert account_data["settlementSettings"] is not None
    assert account_data["settlementSettings"]["period"] == old_period
    assert account_data["settlementSettings"]["next"] == new_period


def test_change_validation(ndau, random_string, set_up_account):
    """Test ChangeValidation transaction"""

    # Set up an account.
    account = random_string("change-validation")
    set_up_account(account)
    account_data = json.loads(ndau(f"account query {account}"))
    assert account_data["validationKeys"] is not None
    assert len(account_data["validationKeys"]) == 1
    key1 = account_data["validationKeys"][0]
    assert account_data["validationScript"] is None

    # Add
    ndau(f"account validation {account} add")
    account_data = json.loads(ndau(f"account query {account}"))
    assert account_data["validationKeys"] is not None
    assert len(account_data["validationKeys"]) == 2
    assert account_data["validationKeys"][0] == key1
    assert account_data["validationKeys"][1] != key1
    assert account_data["validationScript"] is None

    # Reset
    ndau(f"account validation {account} reset")
    account_data = json.loads(ndau(f"account query {account}"))
    assert account_data["validationKeys"] is not None
    assert len(account_data["validationKeys"]) == 1
    assert account_data["validationKeys"][0] != key1
    assert account_data["validationScript"] is None

    # SetScript
    ndau(f"account validation {account} set-script oAAgiA")
    account_data = json.loads(ndau(f"account query {account}"))
    assert account_data["validationScript"] == "oAAgiA=="


def test_command_validator_change(ndau):
    """Test CommandValidatorChange transaction"""

    # Get info about the validator we want to change.
    info = json.loads(ndau("info"))
    assert info["validator_info"] is not None
    assert info["validator_info"]["pub_key"] is not None

    assert len(info["validator_info"]["pub_key"]) > 0
    pubkey_bytes = bytes(info["validator_info"]["pub_key"])

    assert info["validator_info"]["voting_power"] is not None
    old_power = info["validator_info"]["voting_power"]

    # Get non-padded base64 encoding.
    pubkey = base64.b64encode(pubkey_bytes).decode("utf-8").rstrip("=")

    # Cycle over a power range of 5, starting at the default power of 10.
    new_power = 10 + (old_power + 6) % 5

    # CVC
    ndau(f"cvc {pubkey} {new_power}")

    # Wait up to 10 seconds for the change in power to propagate.
    new_voting_power_was_set = False
    for _ in range(10):
        sleep(1)
        info = json.loads(ndau("info"))
        assert info["validator_info"] is not None
        voting_power = info["validator_info"]["voting_power"]
        if voting_power == new_power:
            new_voting_power_was_set = True
            break
        assert voting_power == old_power
    assert new_voting_power_was_set


def test_claim_child_account(ndau, random_string, set_up_account):
    """Test ClaimChildAccount transaction"""

    # Set up parent account.
    parent_account = random_string("claim-parent")
    set_up_account(parent_account)

    # Declare a child account and claim it.
    child_account = random_string("claim-child")
    settlement_period = "2m3dt5h7m11s"
    ndau(f"account claim-child {parent_account} {child_account} -p={settlement_period}")

    # Ensure the child account was claimed properly.
    account_data = json.loads(ndau(f"account query {child_account}"))
    assert account_data["validationKeys"] is not None
    assert len(account_data["validationKeys"]) == 1
    parent_address = account_data["parent"]
    assert account_data["progenitor"] == parent_address
    assert account_data["settlementSettings"] is not None
    assert account_data["settlementSettings"]["period"] == settlement_period

    # See that the parent/progenitor address matches that of the parent account.
    account_data = json.loads(ndau(f"account query -a {parent_address}"))
    # This just proves that we get back non-degenerate account data, proving the parent exists.
    assert len(account_data["validationKeys"]) > 0
    # This parent account is the progenitor (both are null).
    assert account_data["parent"] is None
    assert account_data["progenitor"] is None


def test_change_sysvar(ndau, ensure_pre_genesis_tx_fees, ensure_post_genesis_tx_fees):
    """Test that changing a system variable doesn't kill the blockchain"""
    ensure_pre_genesis_tx_fees()
    ensure_post_genesis_tx_fees()
    ndau("info")


def test_svi_and_account_attributes(ndau, ndau_no_error, chaos, rfe):
    """Test setting svi and AccountAttributes system variables"""

    # Set up the AccountAttributes system variable in the svi map.
    sysvar = "AccountAttributes"
    sysvar_b64 = base64.b64encode(bytes(sysvar.encode())).decode("utf-8")
    svi_json = json.loads(chaos("get sysvar svi -m"))
    svi_json[sysvar] = {
        "Current":  [constants.SYSVAR_NAMESPACE, sysvar_b64],
        "Future":   [constants.SYSVAR_NAMESPACE, sysvar_b64],
        "ChangeOn": 0,
    }
    svi = json.dumps(svi_json)
    type_hints = '{"ChangeOn":["uint64"]}'
    chaos(f"set sysvar svi --value-json '{svi}' --value-json-types '{type_hints}'")

    # Clear the account_attributes if there are any, so we can claim the elephant account below.
    account_attributes = '{}'
    chaos(f"set sysvar AccountAttributes --value-json '{account_attributes}'")

    # Set up the elephant account as an exchange account.
    account = "elephant-test"
    ndau_no_error(f"account destroy {account} --force")
    ndau(f"account recover {account} elephant elephant elephant elephant elephant elephant elephant elephant elephant elephant elephant elephant")
    rfe(10, account) # Give the account some ndau to pay for the claim transaction.
    ndau(f"account claim {account}")

    # Make it an exchange account.
    account_attributes = '{"ndaegwggj8qv7tqccvz6ffrthkbnmencp9t2y4mn89gdq3yk":{"x":{}}}'
    chaos(f"set sysvar AccountAttributes --value-json '{account_attributes}'")

    # One of the rules of exchange accounts is that you cannot lock them.
    # Testing this means we've verified that the AccountAttributes in svi is set up properly.
    assert ndau_no_error("account lock elephant-test 2d") == "Cannot lock exchange accounts"
