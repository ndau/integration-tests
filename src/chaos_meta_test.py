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
def test_chaos_go_repo(chaos_go_repo, request):
    #    pdb.set_trace()
    requested_label = request.config.getoption("--chaos-go-label")
    current_label = subp("git rev-parse --abbrev-ref HEAD")
    if requested_label == current_label:
        assert os.path.exists(chaos_go_repo)
        with within(chaos_go_repo):
            requested_hash = subp(f'git log {requested_label} -1 --pretty=tformat:"%H"')
            actual_hash = subp('git log -1 --pretty=tformat:"%H"')
            assert requested_hash == actual_hash


@pytest.mark.meta
def test_chaostool_repo(chaostool_repo, request):
    requested_label = request.config.getoption("--chaostool-label")
    current_label = subp("git rev-parse --abbrev-ref HEAD")
    if requested_label == current_label:
        assert os.path.exists(chaostool_repo)
        with within(chaostool_repo):
            requested_hash = subp(f'git log {requested_label} -1 --pretty=tformat:"%H"')
            actual_hash = subp('git log -1 --pretty=tformat:"%H"')
            assert requested_hash == actual_hash


@pytest.mark.meta
def test_whitelist_repo(whitelist_repo, request):
    requested_label = request.config.getoption("--whitelist-label")
    assert os.path.exists(whitelist_repo)
    with within(whitelist_repo):
        requested_hash = subp(f'git log {requested_label} -1 --pretty=tformat:"%H"')
        actual_hash = subp('git log -1 --pretty=tformat:"%H"')
        assert requested_hash == actual_hash


@pytest.mark.meta
def test_chaos_node(chaos_node_exists):
    # see https://tendermint.readthedocs.io/en/master/getting-started.html
    try:
        print(f'address: {chaos_node_exists["address"]}')

        subp(
            f'curl -s http://{chaos_node_exists["address"]}:'
            f'{chaos_node_exists["nodenet0_rpc"]}/status'
        )

    except subprocess.CalledProcessError as e:
        print("--STDOUT--")
        print(e.stdout)
        print("--RETURN CODE--")
        print(e.returncode)
        raise


@pytest.mark.meta
def test_chaos_node_and_tool(chaos_node_and_tool):
    c = chaos_node_and_tool
    #    pdb.set_trace()
    # ensure that 'chaos conf' has already been run
    ret = subp(f'{c["tool"]["bin"]} id list', env=c["env"])
    print(f"chaostool ret = {ret}")
    # ensure that the node is running and the tool is configured
    # to connect to it
    ret = subp(f'{c["tool"]["bin"]} info', env=c["env"])
    print(f"chaostool ret = {ret}")


@pytest.mark.meta
def test_whitelist_build(whitelist_build):
    # ensure the binary exists and can run
    try:
        subp(f'{whitelist_build["bin"]} chaos path', stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print(e.stdout)
        raise


@pytest.mark.meta
@pytest.mark.skip(reason="flaky for as-yet undiagnosed reasons")
def test_chaos_node_two_validator_build(chaos_node_two_validator_build):
    """Ensure that all expected outputs exist for two validator build."""
    for pk in ("multinode", "repo", "scripts"):
        path = chaos_node_two_validator_build[pk]
        assert os.path.exists(path)
    output_scripts = glob(
        os.path.join(chaos_node_two_validator_build["scripts"], "*.sh")
    )
    print("scripts generated:")
    for script in output_scripts:
        print(script)
    assert len(output_scripts) > 0


@pytest.mark.meta
@pytest.mark.skip(reason="flaky for as-yet undiagnosed reasons")
def test_chaos_node_two_validator(chaos_node_two_validator):
    """Ensure that both validators of the chaos node are up."""
    gen_nodes = chaos_node_two_validator["gen_nodes"]
    for address in gen_nodes("2 --rpc-address").splitlines():
        subp(f"curl -s {address}/status")


@pytest.mark.meta
@pytest.mark.skip(reason="flaky for as-yet undiagnosed reasons")
def test_two_chaos_nodes_and_tool(two_chaos_nodes_and_tool):
    """Ensure that chaos tool setup worked with two nodes."""
    chaos = two_chaos_nodes_and_tool["chaos"]
    chaos_path = chaos("conf-path")
    print("chaos path:", chaos_path)
    assert chaos_path.startswith(two_chaos_nodes_and_tool["node"]["multinode"])
