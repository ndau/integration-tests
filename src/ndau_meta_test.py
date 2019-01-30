"""
Test that the fixtures we build work properly.
"""

import os
import subprocess
from glob import glob
import pytest

from src.util.repo import within
from src.util.subp import subp


@pytest.mark.meta
def test_ndau_go_repo(ndau_go_repo, request):
    #    pdb.set_trace()
    requested_label = request.config.getoption("--ndau-go-label")
    current_label = subp("git rev-parse --abbrev-ref HEAD")
    if requested_label == current_label:
        assert os.path.exists(ndau_go_repo)
        with within(ndau_go_repo):
            requested_hash = subp(f'git log {requested_label} -1 --pretty=tformat:"%H"')
            actual_hash = subp('git log -1 --pretty=tformat:"%H"')
            assert requested_hash == actual_hash


@pytest.mark.meta
def test_ndautool_repo(ndautool_repo, request):
    requested_label = request.config.getoption("--ndautool-label")
    current_label = subp("git rev-parse --abbrev-ref HEAD")
    if requested_label == current_label:
        assert os.path.exists(ndautool_repo)
        with within(ndautool_repo):
            requested_hash = subp(f'git log {requested_label} -1 --pretty=tformat:"%H"')
            actual_hash = subp('git log -1 --pretty=tformat:"%H"')
            assert requested_hash == actual_hash


@pytest.mark.meta
def test_ndau_node(ndau_node_exists):
    # see https://tendermint.readthedocs.io/en/master/getting-started.html
    try:
        print(f'address: {ndau_node_exists["address"]}')

        subp(
            f'curl -s http://{ndau_node_exists["address"]}:'
            f'{ndau_node_exists["nodenet0_rpc"]}/status'
        )

    except subprocess.CalledProcessError as e:
        print("--STDOUT--")
        print(e.stdout)
        print("--RETURN CODE--")
        print(e.returncode)
        raise


@pytest.mark.meta
def test_ndau_node_and_tool(ndau_node_and_tool):
    c = ndau_node_and_tool
    #    pdb.set_trace()
    # ensure that the node is running and the tool is configured
    # to connect to it
    ret = subp(f'{c["tool"]["bin"]} info', env=c["env"], stderr=subprocess.STDOUT)
    print(f"ndautool ret = {ret}")
