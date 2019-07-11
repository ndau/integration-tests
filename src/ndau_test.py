"""Tests that the ndau blockchain operates as expected."""

import base64
import json
import os
import tarfile
import tempfile
import toml
from pathlib import Path
from src.util import constants
from src.util.random_string import random_string
from src.util.subp import subpv
from time import sleep


def test_get_ndau_status(ndau):
    """`ndautool` can connect to `ndau node` and get status."""
    info = json.loads(ndau("info"))
    moniker = info["node_info"]["moniker"]
    assert moniker == constants.LOCALNET0_MONIKER


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
    # check that account has no validation keys
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
    # set validation, and check that account now has validation keys
    ndau(f"account set-validation {_random_string}")
    account_data = json.loads(ndau(f"account query {_random_string}"))
    assert account_data["validationKeys"] is not None


def test_genesis(
    ndau, rfe, ndau_suppress_err, netconf, zero_tx_fees, node_rules_account
):
    # Set up a purchaser account.  We don't have to rfe to it to pay for
    # 0-napu set-validation tx fee.
    purchaser_account = random_string("genesis-purchaser")
    ndau(f"account new {purchaser_account}")
    ndau(f"account set-validation {purchaser_account}")

    # Put a lot of ndau in there so small EAI fee percentages are non-zero.
    ndau_locked = 1_000_000
    ndau(f"rfe {ndau_locked} {purchaser_account}")
    ndau(f"issue {ndau_locked}")

    # Lock it for a long time to maximize EAI.
    lock_years = 3
    ndau(f"account lock {purchaser_account} {lock_years}y")

    # Set up a node operator account with 1000 ndau needed to self-stake.
    stake_ndau = 1000
    node_account = random_string("genesis-node")
    ndau(f"account new {node_account}")
    # We can set-validation the accont before funding it since tx fees are zero.
    ndau(f"account set-validation {node_account}")
    rfe(stake_ndau, node_account)

    # Stake to node rules account
    ndau(
        f"account stake {node_account} "
        f"--rules-address={node_rules_account} --staketo-address={node_rules_account} "
        f"{stake_ndau}"
    )

    # Bytes lifted from tx_register_node_test.go.
    distribution_script_bytes = b"\xa0\x00\x88"
    distribution_script = base64.b64encode(distribution_script_bytes).decode("utf-8")
    err_msg = ndau_suppress_err(
        f"account register-node {node_account} {distribution_script}"
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
    ndau(f"account set-validation {reward_account}")
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


def test_transfer(ndau, nonzero_tx_fees, set_up_account, zero_sib):
    """Test Transfer transaction"""
    # Set up accounts to transfer between.
    account1 = random_string("xfer1")
    set_up_account(account1)
    account2 = random_string("xfer2")
    set_up_account(account2)

    orig_ndau = 10  # from set_up_account()
    orig_napu = int(orig_ndau * 1e8)
    xfer_ndau = 1  # We'll transfer this amount
    xfer_napu = int(xfer_ndau * 1e8)

    # One napu for the set-validation transaction.
    account_data1 = json.loads(ndau(f"account query {account1}"))
    assert account_data1["balance"] == orig_napu - constants.ONE_NAPU_FEE

    # Transfer
    ndau(f"transfer {xfer_ndau} {account1} {account2}")
    account_data1 = json.loads(ndau(f"account query {account1}"))
    account_data2 = json.loads(ndau(f"account query {account2}"))
    # Subtract one napu for the set-validation transaction, one for the transfer.
    assert (
        account_data1["balance"] == orig_napu - xfer_napu - 2 * constants.ONE_NAPU_FEE
    )
    assert account_data1["lock"] is None
    # Subtract one napu for the set-validation transaction.
    assert account_data2["balance"] == orig_napu + xfer_napu - constants.ONE_NAPU_FEE
    assert account_data2["lock"] is None


def test_transfer_lock(ndau, nonzero_tx_fees, set_up_account, zero_sib):
    """Test TransferLock transaction"""
    # Set up source account with funds.
    account1 = random_string("xferlock1")
    set_up_account(account1)

    # Create destination account, but don't set-validation or rfe to it
    # (otherwise transfer-lock fails).
    account2 = random_string("xferlock2")
    ndau(f"account new {account2}")

    orig_ndau = 10  # from set_up_account()
    orig_napu = int(orig_ndau * 1e8)
    xfer_ndau = 1  # We'll transfer this amount
    xfer_napu = int(xfer_ndau * 1e8)

    # One napu for the set-validation transaction.
    account_data1 = json.loads(ndau(f"account query {account1}"))
    assert account_data1["balance"] == orig_napu - constants.ONE_NAPU_FEE

    # TransferLock
    lock_months = 3
    ndau(f"transfer-lock {xfer_ndau} {account1} {account2} {lock_months}m")
    account_data1 = json.loads(ndau(f"account query {account1}"))
    account_data2 = json.loads(ndau(f"account query {account2}"))
    # Subtract one napu for the set-validation transaction, one for the transfer-lock.
    assert (
        account_data1["balance"] == orig_napu - xfer_napu - 2 * constants.ONE_NAPU_FEE
    )
    assert account_data1["lock"] is None
    # No set-validation transaction, no fee.  Just gain the amount transferred.
    assert account_data2["balance"] == xfer_napu
    assert account_data2["lock"] is not None
    assert account_data2["lock"]["unlocksOn"] is None


def test_transfer_with_sib(ndau, nonzero_tx_fees, set_up_account, max_sib):
    """Test Transfer transaction"""
    # Set up accounts to transfer between.
    account1 = random_string("xfer1")
    set_up_account(account1)
    account2 = random_string("xfer2")
    set_up_account(account2)

    orig_ndau = 10  # from set_up_account()
    orig_napu = int(orig_ndau * 1e8)
    xfer_ndau = 1  # We'll transfer this amount
    xfer_napu = int(xfer_ndau * 1e8)

    # One napu for the set-validation transaction.
    account_data1 = json.loads(ndau(f"account query {account1}"))
    assert account_data1["balance"] == orig_napu - constants.ONE_NAPU_FEE

    # Transfer
    ndau(f"transfer {xfer_ndau} {account1} {account2}")
    account_data1 = json.loads(ndau(f"account query {account1}"))
    account_data2 = json.loads(ndau(f"account query {account2}"))
    # Subtract one napu for the set-validation transaction, one for the transfer.
    assert account_data1["balance"] < orig_napu - xfer_napu - 2 * constants.ONE_NAPU_FEE
    assert account_data1["lock"] is None
    # Subtract one napu for the set-validation transaction.
    assert account_data2["balance"] == orig_napu + xfer_napu - constants.ONE_NAPU_FEE
    assert account_data2["lock"] is None


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
    assert account_data["recourseSettings"] is not None
    old_period = account_data["recourseSettings"]["period"]
    assert old_period is not None
    assert old_period != ""
    assert old_period != new_period
    assert account_data["recourseSettings"]["next"] is None

    # ChangeSettlementPeriod
    ndau(f"account change-recourse-period {account} {new_period}")
    account_data = json.loads(ndau(f"account query {account}"))
    assert account_data["recourseSettings"] is not None
    assert account_data["recourseSettings"]["period"] == old_period
    assert account_data["recourseSettings"]["next"] == new_period


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


def get_pvk():
    """
    Get the private validator key JSON file for node 0 of the appropriate network.

    Tries to find the file for localnet node 0. If that fails, tries to find
    the file on a localnet running in the Circle CI integration job.

    Returns the parsed JSON data from the file, or an exception.
    """

    name = "priv_validator_key.json"

    # Look for the file on localnet.
    PVK_PATH = (
        Path.home()
        / ".localnet"
        / "data"
        / "tendermint-ndau-0"
        / "config"
        / name
    )

    if PVK_PATH.exists():
        with open(PVK_PATH, "r") as f:
            return json.load(f)

    # Try again, but check in a place that we use in the Circle CI integration job.
    PVK_PATH = Path(f"/{name}")

    if PVK_PATH.exists():
        with open(PVK_PATH, "r") as f:
            return json.load(f)

    raise Exception(f"{name} not found locally")


def test_command_validator_change(
    ndau, ndau_suppress_err, keytool, set_up_account, node_rules_account
):
    """Test CommandValidatorChange transaction"""

    # testing CVC necessarily involves testing the node to which we are
    # connected: that's the only one which shows up in the info section.
    # however, we have to make some assumptions. In particular, we assume
    # that we're connected to a TM localnet whose config data is in a
    # standardized location. If that's not in fact the case, then we have to
    # just skip this test.

    pvk = get_pvk()

    # Get info about the connected validator
    info = json.loads(ndau("info"))
    assert info["validator_info"] is not None
    assert info["validator_info"]["address"] == pvk["address"]

    info_pkb = bytes(info["validator_info"]["pub_key"])
    pvk_pkb = base64.b64decode(pvk["pub_key"]["value"])
    assert info_pkb == pvk_pkb

    # with this, we're satisfied that info contains the public-private keypair
    # used to construct this validator.
    #
    # First, create the ndau variants of these keys
    ndpvt = keytool(f"ed raw private {pvk['priv_key']['value']} --b64")
    ndpub = keytool(f"ed raw public {pvk['pub_key']['value']} --b64")
    address = keytool(f"addr {ndpub}")

    # Now, we need to inject that data into ndautool.toml appropriately
    conf_path = ndau("conf-path")
    with open(conf_path, "r") as f:
        cpd = toml.load(f)

    # do we already have an account referring to the node we're connected to?
    ln0 = None
    for account in cpd["accounts"]:
        # skip accounts which don't have public ownership keys
        if "ownership" not in account or "public" not in account["ownership"]:
            continue
        if account["ownership"]["public"] == ndpub:
            ln0 = account
            break

    # create an account if it doesn't exist
    if ln0 is None:
        name = random_string("localnet-0")
        ln0 = {
            "name": name,
            "address": address,
            "ownership": {"public": ndpub, "private": ndpvt},
        }
        cpd["accounts"].append(ln0)

    # Set validation rules for the account if it has none
    set_validation = None
    if "validation" not in ln0 or len(ln0["validation"]) == 0:
        # in order for this test to be repeatable, we need predictable validation keys
        # the ndau tool can't do this for us directly, so we have to work around it.
        # these keys are arbitrary constants
        ln0["validation"] = [
            {
                "public": "npuba8jadtbbebbp5iixnbv2kp5suzt35am2zu4gjg2e9t4ghzci97nj7a5mnrvx823883tpfa3f",  # noqa: E501 this line can't usefully be shortened
                "private": "npvtayjadtcbiahcbm8k5ik5piz5n86itab9ffx7qf244ayhnaqwz5fw3c4aj3zmqsy7wekya36fg72jm267sf6m3pdevncr27dd5ter8ye8spxyh349uxz8s684",  # noqa: E501 this one either
            }
        ]
        acct_data = json.loads(ndau("account query -a=" + ln0["address"]))
        pubkeys = [t["public"] for t in ln0["validation"]]

        valkeys = acct_data.get("validationKeys", [])
        if valkeys is None:
            valkeys = []
        if len(valkeys) == 0:
            valkeys = pubkeys
            set_validation = {
                "target": ln0["address"],
                "ownership": ndpub,
                "validation_keys": valkeys,
                "validation_script": None,
                "sequence": 1 + acct_data["sequence"],
            }

        valkeys.sort()
        pubkeys.sort()

        assert valkeys == pubkeys

    # now update ndautool.toml
    with open(conf_path, "w") as f:
        toml.dump(cpd, f)

    if set_validation is not None:
        txb64 = ndau(
            f"signable-bytes setvalidation", input=json.dumps(set_validation)
        )
        set_validation["signature"] = keytool(f"sign {ndpvt} {txb64} --b64")
        stdout = ndau("send setvalidation", input=json.dumps(set_validation))

    # rfe enough ndau to stake
    ndau(f'rfe 1000 {ln0["name"]}')
    # Stake to node rules account
    stdout = ndau_suppress_err(
        f"account stake {ln0['name']} "
        f"--rules-address={node_rules_account} --staketo-address={node_rules_account} "
        "1000"
    )
    if len(stdout.strip()) > 0:
        # the most likely error in this case is that the account is already staked
        # to the node rules account, and you can't have two primary stakes to the same
        # rules account. If that's the case, then everything is fine.
        print(stdout)

    stdout = ndau_suppress_err(
        # script from
        # https://github.com/oneiro-ndev/commands/blob/master/
        #         cmd/chasm/examples/zero.chbin
        f"account register-node {ln0['name']} oAAgiA"
    )
    if len(stdout.strip()) > 0:
        # the most likely error in this case is that the node is already registered,
        # in which case everything is fine
        print(stdout)

    assert info["validator_info"]["voting_power"] is not None
    old_power = info["validator_info"]["voting_power"]

    # Cycle over a power range of 5, starting at the default power of 10.
    new_power = 10 + (old_power + 6) % 5

    # CVC
    ndau(f"cvc {ln0['name']} {new_power}")

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


def test_create_child_account(ndau, set_up_account):
    """Test CreateChildAccount transaction"""

    # Set up parent account.
    parent_account = random_string("create-parent")
    set_up_account(parent_account)

    # Set up delegation account
    delegation_account = random_string("child-delegate")
    set_up_account(delegation_account)

    # Declare a child account and create it.
    child_account = random_string("create-child")
    settlement_period = "2m3dt5h7m11s"
    ndau(
        f"account create-child {parent_account} {child_account} "
        f"-p={settlement_period} {delegation_account}"
    )

    # Ensure the child account was created properly.
    account_data = json.loads(ndau(f"account query {child_account}"))
    assert account_data["validationKeys"] is not None
    assert len(account_data["validationKeys"]) == 1
    parent_address = account_data["parent"]
    assert account_data["progenitor"] == parent_address
    assert account_data["recourseSettings"] is not None
    assert account_data["recourseSettings"]["period"] == settlement_period

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
    # Clear the account_attributes if there are any, so we can use the
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


def test_sysvar_history(ndau):
    """Test system variable history"""
    # make up a fake sv and ensure it doesn't already exist
    fake_sv_name = random_string("fake-sysvar")
    sv_json = ndau(f"sysvar get {fake_sv_name}")
    print(sv_json)
    sv_data = json.loads(sv_json)[fake_sv_name]
    assert sv_data == ""

    # set it a few times
    data = ["one", "two", "three"]
    for val in data:
        ndau(f"sysvar set {fake_sv_name} {val}")

    # get history
    sv_json = ndau(f"sysvar history {fake_sv_name}")
    print(sv_json)
    sv_data = json.loads(sv_json)["history"]
    last_height = 0
    for i in range(len(data)):
        sv_data_i = sv_data[i]
        h = sv_data_i["height"]
        v = sv_data_i["value"]

        height = int(h)
        assert height > last_height
        last_height = height

        value = base64.b64decode(v).decode("utf-8")
        assert value == data[i]

    # ensure the blockchain is still alive
    ndau("info")
