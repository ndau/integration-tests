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
def test_ndau_go_repo(ndau_go_repo, request):
#    pdb.set_trace()
    requested_label = request.config.getoption('--ndau-go-label')
    requested_hash = subp(
        f'git log {requested_label} -1 --pretty=tformat:"%H"'
    )
    assert os.path.exists(ndau_go_repo)
    with within(ndau_go_repo):
        actual_hash = subp('git log -1 --pretty=tformat:"%H"')
        assert requested_hash == actual_hash


@pytest.mark.meta
def test_ndautool_repo(ndautool_repo, request):
    requested_label = request.config.getoption('--ndautool-label')
    requested_hash = subp(
        f'git log {requested_label} -1 --pretty=tformat:"%H"'
    )
    assert os.path.exists(ndautool_repo)
    with within(ndautool_repo):
        actual_hash = subp('git log -1 --pretty=tformat:"%H"')
        assert requested_hash == actual_hash


@pytest.mark.meta
def test_ndau_node(run_kub, ndau_node, ndau_node_exists):
    # see https://tendermint.readthedocs.io/en/master/getting-started.html
    if run_kub:
        env = {
            'PATH': os.environ['PATH']
        }
    else:
        env = {
            'TMHOME': ndau_node['tmhome'],
            'NDAUHOME': ndau_node['ndauhome'],
            'PATH': os.environ['PATH'],
        }        
    print(f'env: {env}')

    try:
        if run_kub:
            print(f'address: {ndau_node_exists["address"]}')

            curl_res = subp(f'curl -s http://{ndau_node_exists["address"]}:{ndau_node_exists["devnet0_rpc"]}/status')
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
def test_ndau_node_and_tool(ndau_node_and_tool):
    c = ndau_node_and_tool
#    pdb.set_trace()
    # ensure that the node is running and the tool is configured
    # to connect to it
    ret = subp(f'{c["tool"]["bin"]} info', env=c['env'], stderr=subprocess.STDOUT)
    print(f'ndautool ret = {ret}')


@pytest.mark.meta
@pytest.mark.skip(reason="flaky for as-yet undiagnosed reasons")
def test_ndau_node_two_validator_build(ndau_node_two_validator_build):
    """Ensure that all expected outputs exist for two validator build."""
    for pk in ('multinode', 'repo', 'scripts'):
        path = ndau_node_two_validator_build[pk]
        assert os.path.exists(path)
    output_scripts = glob(os.path.join(
        ndau_node_two_validator_build['scripts'],
        '*.sh'
    ))
    print("scripts generated:")
    for script in output_scripts:
        print(script)
    assert len(output_scripts) > 0


@pytest.mark.meta
@pytest.mark.skip(reason="flaky for as-yet undiagnosed reasons")
def test_ndau_node_two_validator(ndau_node_two_validator):
    """Ensure that both validators of the ndau node are up."""
    gen_nodes = ndau_node_two_validator['gen_nodes']
    for address in gen_nodes('2 --rpc-address').splitlines():
        subp(f'curl -s {address}/status')

@pytest.mark.meta
@pytest.mark.skip(reason="flaky for as-yet undiagnosed reasons")
def test_two_ndau_nodes_and_tool(two_ndau_nodes_and_tool):
    """Ensure that ndau tool setup worked with two nodes."""
    ndau = two_ndau_nodes_and_tool['ndau']
    ndau_path = ndau('conf-path')
    print('ndau path:', ndau_path)
    assert ndau_path.startswith(
        two_ndau_nodes_and_tool['node']['multinode']
    )
