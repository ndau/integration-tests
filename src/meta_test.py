"""
Test that the fixtures we build work properly.
"""

import os
import subprocess
from glob import glob
import pdb
import pytest

from src.repo import within
from src.subp import subp


@pytest.mark.meta
def test_chaos_go_repo(chaos_go_repo, request):
    requested_label = request.config.getoption('--chaos-go-label')
    requested_hash = subp(
        f'git log {requested_label} -1 --pretty=tformat:"%H"'
    )
    assert os.path.exists(chaos_go_repo)
    with within(chaos_go_repo):
        actual_hash = subp('git log -1 --pretty=tformat:"%H"')
        assert requested_hash == actual_hash


@pytest.mark.meta
def test_chaostool_repo(chaostool_repo, request):
    requested_label = request.config.getoption('--chaostool-label')
    requested_hash = subp(
        f'git log {requested_label} -1 --pretty=tformat:"%H"'
    )
    assert os.path.exists(chaostool_repo)
    with within(chaostool_repo):
        actual_hash = subp('git log -1 --pretty=tformat:"%H"')
        assert requested_hash == actual_hash


@pytest.mark.meta
def test_whitelist_repo(whitelist_repo, request):
    requested_label = request.config.getoption('--whitelist-label')
    requested_hash = subp(
        f'git log {requested_label} -1 --pretty=tformat:"%H"'
    )
    assert os.path.exists(whitelist_repo)
    with within(whitelist_repo):
        actual_hash = subp('git log -1 --pretty=tformat:"%H"')
        assert requested_hash == actual_hash


@pytest.mark.meta
def test_chaos_node(run_kub, chaos_node, chaos_node_exists):
    # see https://tendermint.readthedocs.io/en/master/getting-started.html
    if run_kub:
        env = {
            'PATH': os.environ['PATH']
        }
    else:
        env = {
            'TMHOME': chaos_node['tmhome'],
            'NDAUHOME': chaos_node['ndauhome'],
            'PATH': os.environ['PATH'],
        }        
    print(f'env: {env}')

    try:
        if run_kub:
            print(f'address: {chaos_node_exists["address"]}')

            curl_res = subp(f'curl -s http://{chaos_node_exists["address"]}:{chaos_node_exists["devnet0_rpc"]}/status')
        else:
            address = subp(
                # JSG change port to current default TM port: 26657
                'docker-compose port tendermint 26657',
                env=env,
                stderr=subprocess.STDOUT,
            )
            print(f'address: {address}')

            curl_res = subp(f'curl -s {address}/status')        

    except subprocess.CalledProcessError as e:
        print('--STDOUT--')
        print(e.stdout)
        print('--RETURN CODE--')
        print(e.returncode)
        raise


@pytest.mark.meta
def test_chaos_node_and_tool(chaos_node_and_tool):
    c = chaos_node_and_tool
#    pdb.set_trace()
    # ensure that 'chaos conf' has already been run
    ret = subp(f'{c["tool"]["bin"]} id list', env=c['env'])
    print(f'chaostool ret = {ret}')
    # ensure that the node is running and the tool is configured
    # to connect to it
    ret = subp(f'{c["tool"]["bin"]} info', env=c['env'])
    print(f'chaostool ret = {ret}')


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
    for pk in ('multinode', 'repo', 'scripts'):
        path = chaos_node_two_validator_build[pk]
        assert os.path.exists(path)
    output_scripts = glob(os.path.join(
        chaos_node_two_validator_build['scripts'],
        '*.sh'
    ))
    print("scripts generated:")
    for script in output_scripts:
        print(script)
    assert len(output_scripts) > 0


@pytest.mark.meta
@pytest.mark.skip(reason="flaky for as-yet undiagnosed reasons")
def test_chaos_node_two_validator(chaos_node_two_validator):
    """Ensure that both validators of the chaos node are up."""
    gen_nodes = chaos_node_two_validator['gen_nodes']
    for address in gen_nodes('2 --rpc-address').splitlines():
        subp(f'curl -s {address}/status')

@pytest.mark.meta
@pytest.mark.skip(reason="flaky for as-yet undiagnosed reasons")
def test_two_chaos_nodes_and_tool(two_chaos_nodes_and_tool):
    """Ensure that chaos tool setup worked with two nodes."""
    chaos = two_chaos_nodes_and_tool['chaos']
    chaos_path = chaos('conf-path')
    print('chaos path:', chaos_path)
    assert chaos_path.startswith(
        two_chaos_nodes_and_tool['node']['multinode']
    )
