"""Tests that the ndau blockchain operates as expected."""

import base64
import json
import pytest
from src.util import constants
from src.util.random_string import random_string
from time import sleep


def test_get_ndau_status(node_net, ndau):
    """`ndautool` can connect to `ndau node` and get status."""
    info = json.loads(ndau("info"))
    moniker = info["node_info"]["moniker"]
    assert moniker == f"{node_net}-0"


def test_create_account(ndau, rfe, zero_tx_fees):
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
    orig_napu = 10 * 1e8
    rfe(orig_ndau, _random_string)
    account_data = json.loads(ndau(f"account query {_random_string}"))
    # check that account balance is 10 ndau
    assert account_data["balance"] == orig_napu
    # claim account, and check that account now has validation keys
    ndau(f"account claim {_random_string}")
    account_data = json.loads(ndau(f"account query {_random_string}"))
    assert account_data["validationKeys"] is not None


def test_genesis(ndau, rfe, ndau_suppress_err, netconf, zero_tx_fees):
    # Set up a purchaser account.  We don't have to rfe to it to pay for
    # 0-napu claim tx fee.
    purchaser_account = random_string("genesis-purchaser")
    ndau(f"account new {purchaser_account}")
    ndau(f"account claim {purchaser_account}")

    # Put a lot of ndau in there so small EAI fee percentages are non-zero.
    ndau_locked = 1_000_000
    ndau(f"rfe {ndau_locked} {purchaser_account}")
    ndau(f"issue {ndau_locked}")

    # Lock it for a long time to maximize EAI.
    lock_years = 3
    ndau(f"account lock {purchaser_account} {lock_years}y")

    # Set up a node operator account with 1000 ndau needed to self-stake.
    node_account = random_string("genesis-node")
    ndau(f"account new {node_account}")
    # We can claim the accont before funding it since tx fees are zero.
    ndau(f"account claim {node_account}")
    rfe(1000, node_account)

    # Self-stake and register the node account to the node.
    ndau(f"account stake {node_account} {node_account}")
    rpc_address = f'http://{netconf["address"]}:{netconf["nodenet0_rpc"]}'
    # Bytes lifted from tx_register_node_test.go.
    distribution_script_bytes = b"\xa0\x00\x88"
    distribution_script = base64.b64encode(distribution_script_bytes).decode("utf-8")
    err_msg = ndau_suppress_err(
        f"account register-node {node_account} {rpc_address} {distribution_script}"
    )
    assert err_msg == "" or err_msg.startswith("acct is already staked")

    # Delegate purchaser account to node account.
    ndau(f"account delegate {purchaser_account} {node_account}")
    node_addr = ndau(f"account addr {node_account}")

    # ensure the delegation succeeded
    purchaser_acct_data = json.loads(ndau(f"account query {purchaser_account}"))
    assert purchaser_acct_data["delegationNode"] == node_addr

    # We want to ensure that every account which is supposed to get a cut of EAI
    # receives non-zero EAI on a CreditEAI tx. But which accounts are supposed
    # to receive EAI?
    # - Every account in the EAI fee table
    # - All accounts delegated to the node account
    # - _Not_ the node account itself

    eai_fee_table = json.loads(ndau(f"sysvar get {constants.EAI_FEE_TABLE_KEY}"))[
        constants.EAI_FEE_TABLE_KEY
    ]

    # start acct_balances from the fee table
    acct_balances = {
        addr: json.loads(ndau(f"account query -a {addr}"))["balance"]
        for fee in eai_fee_table
        if fee["To"] is not None
        for addr in fee["To"]
    }
    # add the purchaser_account as a proxy for every accoutn delegated to this node
    acct_balances[ndau(f"account addr {purchaser_account}")] = purchaser_acct_data[
        "balance"
    ]
    node_past_balance = json.loads(ndau(f"account query {node_account}"))["balance"]

    # Submit CreditEAI tx so that bpc operations can have ndau to
    # pay for changing sysvars.
    ndau(f"account credit-eai {node_account}")

    for addr, past_balance in acct_balances.items():
        current_balance = json.loads(ndau(f"account query -a {addr}"))["balance"]
        # it is outside the scope of this test to compute _how much_ EAI each account
        # should have earned; that's the province of EAI unit tests. We just want to
        # ensure that they all got credited.
        assert current_balance > past_balance

    # ensure the node didn't yet receive any EAI
    assert (
        node_past_balance
        == json.loads(ndau(f"account query {node_account}"))["balance"]
    )

    # Now  attempt to test NNR
    #
    # Unfortunately, we can only run this integration test once per day.  When
    # running against localnet, we can do a reset to test NNR repeatedly. We
    # use a value of 0 (any value will do) for deterministic nomination.

    # Set up a reward target account.  Tx fee is still zero so we don't
    # have to rfe to it.
    reward_account = random_string("genesis-node-reward")
    ndau(f"account new {reward_account}")
    ndau(f"account claim {reward_account}")
    ndau(f"account set-rewards-target {node_account} {reward_account}")

    nnr_result = ndau_suppress_err(f"nnr 0")
    if not nnr_result.startswith("not enough time since last NNR"):
        # Claim node rewards and see that the node operator gets his EAI in
        # the reward account.  We check the reward account.  If we didn't
        # set a reward target, then the node account would receive the ndau
        # here.  That was tested and worked, but since we can only do one
        # NNR per day, we test the more complex situation of awarding to a
        # target reward account.
        reward_result = ndau_suppress_err(f"account claim-node-reward {node_account}")
        # Despite sending a constant "random" number to the NNR calc, we
        # can't know which node will win; that depends on the state of the
        # network, which nodes are delegated, and which have balances.
        # What we can test is that if the one we're watching happened to win,
        # its reward target received its reward.
        if reward_result.startswith("winner was"):
            winner = reward_result.split()[2]
            if winner == node_addr:
                reward_balance = json.loads(ndau(f"account query {reward_account}"))[
                    "balance"
                ]
                # this works because this is an otherwise brand-new account,
                # which has never received any other rewards or transfers
                assert reward_balance > 0


def test_transfer(ndau, nonzero_tx_fees, set_up_account):
    """Test Transfer transaction"""
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


def test_transfer_lock(ndau, nonzero_tx_fees, set_up_account):
    """Test TransferLock transaction"""
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


def test_lock_notify(ndau, set_up_account):
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


def test_change_settlement_period(ndau, set_up_account):
    """Test ChangeSettlementPeriod transaction"""

    # Pick something that we wouldn't ever use as a default.  That way, we can
    # assert on the initial value is not this (rather than assserting on the
    # default value, which would fail if we ever changed it).  We will then
    # change the settlement period to this and assert.
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


def test_change_validation(ndau, set_up_account):
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

    # Make up to 10 attempts for the change in power to propagate.
    new_voting_power_was_set = False
    for _ in range(10):
        info = json.loads(ndau("info"))
        assert info["validator_info"] is not None
        voting_power = info["validator_info"]["voting_power"]
        if voting_power == new_power:
            new_voting_power_was_set = True
            break
        assert voting_power == old_power
        sleep(1)
    assert new_voting_power_was_set


def test_claim_child_account(ndau, set_up_account):
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
    # This just proves that we get back non-degenerate account data, proving
    # the parent exists.
    assert len(account_data["validationKeys"]) > 0
    # This parent account is the progenitor (both are null).
    assert account_data["parent"] is None
    assert account_data["progenitor"] is None


def test_change_sysvar(ndau, rfe_to_ssv):
    """Test that changing a system variable doesn't kill the blockchain"""
    # make up a fake sv and ensure it doesn't already exist
    fake_sv_name = random_string("fake-sysvar")
    sv_json = ndau(f"sysvar get {fake_sv_name}")
    print(sv_json)
    sv_data = json.loads(sv_json)[fake_sv_name]
    assert sv_data == ""

    # set it
    data = random_string("fake-sysvar-data")
    ndau(f"sysvar set {fake_sv_name} --json '\"{data}\"'")

    # ensure it set properly
    sv_json = ndau(f"sysvar get {fake_sv_name}")
    print(sv_json)
    sv_data = json.loads(sv_json)[fake_sv_name]
    assert sv_data == data

    # ensure the blockchain is still alive
    ndau("info")


def test_account_attributes(ndau, ndau_suppress_err, set_up_account, rfe_to_ssv):
    """Test setting AccountAttributes system variable"""
    # Clear the account_attributes if there are any, so we can claim the
    # elephant account below.
    account_attributes = "{}"
    ndau(
        f"sysvar set {constants.ACCOUNT_ATTRIBUTES_KEY} "
        f"--json '{account_attributes}'"
    )

    # Set up the elephant account as an exchange account.
    account = "elephant-test"
    set_up_account(account, " ".join(["elephant"] * 12))

    # Make it an exchange account.
    account_attributes = '{"ndaegwggj8qv7tqccvz6ffrthkbnmencp9t2y4mn89gdq3yk":{"x":{}}}'
    ndau(
        f"sysvar set {constants.ACCOUNT_ATTRIBUTES_KEY} "
        f"--json '{account_attributes}'"
    )

    # One of the rules of exchange accounts is that you cannot lock them.
    # Testing this means we've verified that the AccountAttributes in svi is
    # set up properly.
    assert "InvalidTransaction" in ndau_suppress_err("account lock elephant-test 2d")


@pytest.mark.skip(reason="sysvar history is not implemented")
def test_sysvar_history(ndau):
    """
    Test system variable history over time.

    Not currently implemented, so we can't do anything here.
    """
    pass
