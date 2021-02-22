#  ----- ---- --- -- -
#  Copyright 2020 The Axiom Foundation. All Rights Reserved.
# 
#  Licensed under the Apache License 2.0 (the "License").  You may not use
#  this file except in compliance with the License.  You can obtain a copy
#  in the file LICENSE in the source distribution or at
#  https://www.apache.org/licenses/LICENSE-2.0.txt
#  - -- --- ---- -----

"""
Define pytest fixtures.

These fixtures configure and run the chain and tools.
"""

import json
import os
import os.path
from pathlib import Path
import pytest
import shutil
import subprocess
import tempfile
import toml

from src.util import constants
from src.util.subp import subpv, ndenv
from src.util.tx_fees import ensure_tx_fees


def pytest_addoption(parser):
    """See https://docs.pytest.org/en/latest/example/simple.html."""
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )
    parser.addoption(
        "--skipmeta", action="store_true", default=False, help="skip meta tests"
    )
    parser.addoption(
        "--keeptemp",
        action="store_true",
        default=False,
        help="keep temporary files for debugging failures",
    )
    parser.addoption("--ip", default="localhost", help="ip of the localnet-0 node")


@pytest.fixture(scope="session")
def verbose(request):
    return request.config.getoption("verbose") > 0


@pytest.fixture(scope="session")
def ndauapi(localnet0_ip):
    return f"http://{localnet0_ip}:{constants.LOCALNET0_NDAUAPI}"


@pytest.fixture(scope="session")
def keeptemp(request):
    return request.config.getoption("--keeptemp")


@pytest.fixture(scope="session")
def localnet0_ip(request):
    return request.config.getoption("--ip")


def pytest_collection_modifyitems(config, items):
    """Pytest func to adjust which tests are run."""
    if not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
    if config.getoption("--skipmeta"):
        skip_meta = pytest.mark.skip(reason="skipped due to --skipmeta option")
        for item in items:
            if "meta" in item.keywords:
                item.add_marker(skip_meta)


@pytest.fixture(scope="session")
def get_ndauhome_dir():
    # Use the local ndau home directory that's already there,
    # set up by the localnet.
    ndauhome_dir = os.path.expanduser("~/.localnet/data/ndau-0")
    # Make sure it's really there.  If it isn't, the user hasn't
    # set up a local server.
    assert os.path.isdir(ndauhome_dir)
    yield ndauhome_dir


@pytest.fixture(scope="session")
def get_ndau_tmhome_dir():
    # Use the local tm home directory that's already there, set up by the localnet.
    tmhome_dir = os.path.expanduser("~/.localnet/data/tendermint-ndau-0")
    # Make sure it's really there.  If it isn't, the user hasn't
    # set up a local server.
    assert os.path.isdir(tmhome_dir)
    yield tmhome_dir


def findpath(name):
    cmds = Path(os.path.expandvars("$GOPATH/src/github.com/ndau/commands"))
    for subpath in (name, f"cmd/{name}/{name}"):
        p = cmds / subpath
        if p.exists() and p.is_file() and p.stat().st_mode & 1 == 1:
            # file exists and u-x bit is set
            return p
    raise Exception(f"{name} not found")


@pytest.fixture(scope="session")
def ndautool_path():
    return findpath("ndau")


@pytest.fixture(scope="session")
def keytool_path():
    return findpath("keytool")


@pytest.fixture(scope="session")
def netconf(localnet0_ip):
    return {"address": localnet0_ip, "nodenet0_rpc": str(constants.LOCALNET0_RPC)}


@pytest.fixture(scope="session")
def ndau(ndautool_path, netconf, keeptemp):
    """
    Fixture providing a ndau function.
    """

    def nd(cmd, **kwargs):
        try:
            return subpv(f"{ndautool_path} {cmd}", env=ndenv(), **kwargs)
        except subprocess.CalledProcessError as e:
            print(e.stdout)
            raise

    # preserve existing config
    conf_path = nd("conf-path")
    conf_exists = os.path.exists(conf_path)
    if conf_exists:
        _, temp_conf_path = tempfile.mkstemp(prefix="ndautool_toml-")
        shutil.copy2(conf_path, temp_conf_path)
        print(f"temp ndautool.toml: {temp_conf_path}")

    # configure
    nd(f"conf {netconf['address']}:{netconf['nodenet0_rpc']}")

    try:
        yield nd
    finally:
        if keeptemp:
            print(temp_conf_path)
        #    shutil.copy2(temp_conf_path, conf_path)
        elif conf_exists:
            # restore existing config
            shutil.move(temp_conf_path, conf_path)
        else:
            os.remove(conf_path)


@pytest.fixture(scope="session")
def keytool(keytool_path):
    """
    Fixture providing a ndau function.
    """

    def kt(cmd, **kwargs):
        try:
            return subpv(f"{keytool_path} {cmd}", env=ndenv(), **kwargs)
        except subprocess.CalledProcessError as e:
            print(e.stdout)
            raise

    return kt


@pytest.fixture(scope="session")
def ndautool_toml(ndau):
    conf_path = ndau("conf-path")

    with open(conf_path, "rt") as conf_fp:
        return toml.load(conf_fp)


@pytest.fixture
def ndau_suppress_err(ndau):
    """
    Fixture providing a ndau function.

    This function calls the ndau command in a configured environment.
    Any exception returned is suppressed.
    """

    def rf(cmd, **kwargs):
        try:
            return ndau(cmd, **kwargs)
        except subprocess.CalledProcessError as e:
            # Don't raise.  Callers use this to process the error message.
            return e.stdout.rstrip("\n")

    return rf


@pytest.fixture(scope="session")
def rfe_to_rfe(ndau, ndautool_toml, verbose):
    """
    Ensure the RFE account has a non-zero balance

    This has session scope, so it should only run once for a given test run

    Note: this depends on the RFE account having sufficient balance to perform
    RFE transactions at the beginning of the test session. If the test session
    opens with 0 RFE balance and non-zero tx fee, this fixture (and all tests
    which depend on it) will necessarily fail.
    """
    rfe_acct = ndautool_toml["rfe"]["address"]
    rfe_bal = json.loads(ndau(f"account query -a {rfe_acct}"))["balance"]
    must_r2r = rfe_bal < 1e8  # 1 ndau
    if verbose:
        print("rfe address:", rfe_acct)
        print("    balance:", rfe_bal)
        print("   must_r2r:", must_r2r)
    if must_r2r:
        ndau(f"rfe 10 -a {rfe_acct}")
        ndau("issue 10")
    return must_r2r


@pytest.fixture(scope="session")
def rfe_to_ssv(ndau, ndautool_toml, rfe_to_rfe):
    """
    Ensure the SSV account has a non-zero balance

    This has session scope, so it should only run once for a given test run
    """
    ssv_acct = ndautool_toml["set_sysvar"]["address"]
    ssv_bal = json.loads(ndau(f"account query -a {ssv_acct}"))["balance"]
    if ssv_bal < 1e8:  # 1 ndau
        ndau(f"rfe 10 -a {ssv_acct}")
        ndau("issue 10")


@pytest.fixture(scope="session")
def rfe_to_rp(ndau, ndautool_toml, rfe_to_rfe):
    """
    Ensure the RecordPrice account has a non-zero balance

    This has session scope, so it should only run once for a given test run
    """
    rp_acct = ndautool_toml["record_price"]["address"]
    rp_bal = json.loads(ndau(f"account query -a {rp_acct}"))["balance"]
    if rp_bal < 1e8:  # 1 ndau
        ndau(f"rfe 10 -a {rp_acct}")
        ndau("issue 10")


@pytest.fixture(scope="session")
def rfe(ndau, rfe_to_rfe):
    """
    Wrapper for ndau(f"rfe {amount} {account}") that ensures the RFE'd amount
    is subsequently issued.
    """

    def rf(amount, account):
        ndau(f"rfe {amount} {account}")
        ndau(f"issue {amount}")

    return rf


@pytest.fixture(scope="session")
def set_up_account(ndau, rfe):
    """
    Helper function for creating a new account, rfe'ing to it, setting validation rules.
    """

    def rf(account, recovery_phrase=None):
        if recovery_phrase is None:
            ndau(f"account new {account}")
        else:
            ndau(f"account recover {account} {recovery_phrase}")
        rfe(10, account)
        ndau(f"account set-validation {account}")

    return rf


@pytest.fixture
def zero_tx_fees(ndau, rfe_to_ssv):
    yield from ensure_tx_fees(ndau, rfe_to_ssv, constants.ZERO_FEE_SCRIPT)


@pytest.fixture
def nonzero_tx_fees(ndau, rfe_to_ssv):
    yield from ensure_tx_fees(ndau, rfe_to_ssv, constants.ONE_NAPU_FEE_SCRIPT)


@pytest.fixture
def zero_sib(ndau, rfe_to_rp):
    target_price = json.loads(ndau("sib"))["TargetPrice"]
    ndau(f"record-price --nanocents {target_price}")


@pytest.fixture
def max_sib(ndau, rfe_to_rp):
    ndau(f"record-price --nanocents 1")
    # we can't validate any particular number for the outcome of SIB; we've
    # already changed the SIB chaincode in a way which invalidated the previous
    # check of its outcome. What we can do, at least, is ensure it is non-0 when
    # the market price is the minimum legal value

    # validate that we have some sib
    sib = json.loads(ndau("sib"))["SIB"]
    assert sib > 0


@pytest.fixture(scope="session")
def node_rules_account(ndau, rfe):
    address = json.loads(ndau(f"sysvar get NodeRulesAccountAddress"))[
        "NodeRulesAccountAddress"
    ][0]
    data = json.loads(ndau(f"account query -a={address}"))
    if data["stake_rules"] is None:
        ndau(f"account set-stake-rules {address} {constants.ZERO_FEE_SCRIPT}")

    return address
