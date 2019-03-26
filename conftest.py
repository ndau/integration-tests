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

from src.util.subp import subp, subpv
import src.util.constants as constants


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
    parser.addoption(
        "--net",
        action="store",
        default="localnet",
        help="which node net to use, e.g. devnet or localnet",
    )
    parser.addoption(
        "--testapi",
        action="store_true",
        default=False,
        help="test communication with the ndau api",
    )


@pytest.fixture(scope="session")
def keeptemp(request):
    return request.config.getoption("--keeptemp")


@pytest.fixture(scope="session")
def node_net(request):
    return request.config.getoption("--net")


@pytest.fixture(scope="session")
def is_localnet(node_net):
    return node_net.lower().startswith("local")


@pytest.fixture(scope="session")
def use_kub(is_localnet):
    return not is_localnet


def pytest_collection_modifyitems(config, items):
    """Pytest func to adjust which tests are run."""
    if not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
    if not config.getoption("--testapi"):
        skip_api = pytest.mark.skip(reason="need --testapi option to test ndauapi")
        for item in items:
            if "api" in item.keywords:
                item.add_marker(skip_api)
    if config.getoption("--skipmeta"):
        skip_meta = pytest.mark.skip(reason="skipped due to --skipmeta option")
        for item in items:
            if "meta" in item.keywords:
                item.add_marker(skip_meta)


@pytest.fixture(scope="session")
def get_ndauhome_dir(use_kub, keeptemp):
    if use_kub:
        ndauhome_dir = tempfile.mkdtemp(prefix="ndauhome-", dir="/tmp")
    else:
        # Use the local ndau home directory that's already there,
        # set up by the localnet.
        ndauhome_dir = os.path.expanduser("~/.localnet/data/ndau-0")
        # Make sure it's really there.  If it isn't, the user hasn't
        # set up a local server.
        assert os.path.isdir(ndauhome_dir)
    yield ndauhome_dir
    if use_kub and not keeptemp:
        shutil.rmtree(ndauhome_dir, True)


@pytest.fixture(scope="session")
def get_ndau_tmhome_dir(use_kub, keeptemp):
    if use_kub:
        tmhome_dir = tempfile.mkdtemp(prefix="tmhome-", dir="/tmp")
    else:
        # Use the local tm home directory that's already there, set up by the localnet.
        tmhome_dir = os.path.expanduser("~/.localnet/data/tendermint-ndau-0")
        # Make sure it's really there.  If it isn't, the user hasn't
        # set up a local server.
        assert os.path.isdir(tmhome_dir)
    yield tmhome_dir
    if use_kub and not keeptemp:
        shutil.rmtree(tmhome_dir, True)


@pytest.fixture(scope="session")
def ndautool_path():
    cmds = Path(os.path.expandvars("$GOPATH/src/github.com/oneiro-ndev/commands"))
    for subpath in ("ndau", "cmd/ndau/ndau"):
        p = cmds / subpath
        if p.exists() and p.is_file() and p.stat().st_mode & 1 == 1:
            # file exists and u-x bit is set
            return p
    raise Exception("ndautool not found")


@pytest.fixture(scope="session")
def netconf(is_localnet, node_net):
    if is_localnet:
        return {
            "address": "localhost",
            "nodenet0_rpc": str(constants.LOCALNET0_NDAU_RPC),
            "nodenet1_rpc": str(constants.LOCALNET1_NDAU_RPC),
        }

    return {
        "address": subpv(
            "kubectl get nodes -o "
            "jsonpath='{.items[*].status.addresses[?(@.type==\"ExternalIP\")].address}'"
            ' | tr " " "\n" | head -n 1 | tr -d "[:space:]"'
        ),
        "nodenet0_rpc": subpv(
            "kubectl get service --namespace default -o "
            "jsonpath='{.spec.ports[?(@.name==\"rpc\")].nodePort}' "
            + node_net
            + "-0-nodegroup-ndau-tendermint-service"
        ),
        "nodenet1_rpc": subpv(
            "kubectl get service --namespace default -o "
            "jsonpath='{.spec.ports[?(@.name==\"rpc\")].nodePort}' "
            + node_net
            + "-1-nodegroup-ndau-tendermint-service"
        ),
    }


@pytest.fixture(scope="session")
def ndau(ndautool_path, netconf, keeptemp, use_kub):
    """
    Fixture providing a ndau function.
    """

    # set up env
    env = {}
    for var in ("PATH", "HOME", "TMHOME", "NDAUHOME", "KUBECONFIG"):
        if os.environ.get(var) is not None:
            env[var] = os.environ[var]

    def nd(cmd, **kwargs):
        try:
            return subp(
                f"{ndautool_path} {cmd}", stderr=subprocess.STDOUT, env=env, **kwargs
            )
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
    set_addresses_in_toml(use_kub, nd)
    set_bpc_in_toml(use_kub, nd)

    try:
        yield nd
    finally:
        if keeptemp:
            shutil.copy2(temp_conf_path, conf_path)
        elif conf_exists:
            # restore existing config
            shutil.move(temp_conf_path, conf_path)
        else:
            os.remove(conf_path)


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
def rfe_to_rfe(ndau):
    """
    Ensure the RFE account has a non-zero balance

    This has session scope, so it should only run once for a given test run
    """
    rfe_bal = json.loads(ndau(f"account query -a {constants.RFE_ADDRESS}"))["balance"]
    if rfe_bal < 1e8:  # 1 ndau
        ndau(f"rfe 10 -a {constants.RFE_ADDRESS}")
        ndau("issue 10")


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
def set_up_account(ndau, rfe):
    """
    Helper function for creating a new account, rfe'ing to it, claiming it.
    """

    def rf(account, **kwargs):
        ndau(f"account new {account}")
        rfe(10, account)
        ndau(f"account claim {account}")

    return rf


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
def ensure_tx_fees(ndau, rfe_to_ssv):
    """Ensure we have set up zero transaction fees for pre-genesis tests."""

    def rf(fee_script):
        key = constants.TRANSACTION_FEE_SCRIPT_KEY
        current_script = json.loads(ndau(f"sysvar get {key}"))[key]
        # If the tx fees are already zero, there is nothing to do.
        if current_script != fee_script.strip('"'):
            # Calling ensure_genesis() would cause a recursive fixture dependency.
            # We have no choice but to attempt this sysvar change regardless of
            # current tx fees.
            # If there are non-zero tx fees in place, then it's likely that the
            # BPC has enough ndau to pay for the tx fee for this sysvar change,
            # since it would have gotten funded when we performed genesis before
            # we changed the fees to non-zero.  The only way it wouldn't is if
            # we're testing against a blockchain that had its fees changed
            # outside of our integration test suite.
            new_script = fee_script.replace('"', r"\"")
            ndau(f"sysvar set {key} --json {new_script}")

            # Check that it worked.
            current_script = json.loads(ndau(f"sysvar get {key}"))[key]
            assert current_script == fee_script.strip('"')

    return rf


def set_addresses_in_toml(use_kub, ndau):
    # When running on localnet, the rfe address is already present in the config.
    if not use_kub:
        return

    conf_path = ndau("conf-path")

    with open(conf_path, "rt") as conf_fp:
        conf = toml.load(conf_fp)

    # If the entries are there already, we're done.
    if (
        "rfe" in conf
        and conf["rfe"]["address"] == constants.RFE_ADDRESS
        and "nnr" in conf
        and conf["nnr"]["address"] == constants.NNR_ADDRESS
        and "cvc" in conf
        and conf["cvc"]["address"] == constants.CVC_ADDRESS
    ):
        return

    # Write addresses and keys into the conf.
    conf["rfe"] = {"address": constants.RFE_ADDRESS, "keys": [constants.RFE_KEY]}
    conf["nnr"] = {"address": constants.NNR_ADDRESS, "keys": [constants.NNR_KEY]}
    conf["cvc"] = {"address": constants.CVC_ADDRESS, "keys": [constants.CVC_KEY]}

    # Write the conf to the ndautool.toml file.
    with open(conf_path, "wt") as conf_fp:
        toml.dump(conf, conf_fp)


def set_bpc_in_toml(use_kub, ndau):
    # When running on localnet, the rfe address is already present in the config.
    if not use_kub:
        return

    conf_path = ndau("conf-path")

    with open(conf_path, "rt") as conf_fp:
        conf = toml.load(conf_fp)

    # If the entry is there already, we're done.
    if "accounts" in conf:
        for i in range(len(conf["accounts"])):
            if conf["accounts"][i]["address"] == constants.BPC_ADDRESS:
                return

    # Write addresses and keys into the conf.
    conf["accounts"].append(
        {
            "name": constants.BPC_ACCOUNT,
            "address": constants.BPC_ADDRESS,
            "root": {
                "path": "/",
                "public": constants.BPC_ROOT_PUBLIC_KEY,
                "private": constants.BPC_ROOT_PRIVATE_KEY,
            },
            "ownership": {
                "path": "/44'/20036'/100/1",
                "public": constants.BPC_OWNERSHIP_PUBLIC_KEY,
                "private": constants.BPC_OWNERSHIP_PRIVATE_KEY,
            },
            # don't manually enter keys, let the claim do it below
        }
    )

    # Write the conf to the ndautool.toml file.
    with open(conf_path, "wt") as conf_fp:
        toml.dump(conf, conf_fp)

    # claim bpc account to set transfer keys
    ndau(f"account claim {constants.BPC_ACCOUNT}")

