"""
Test that the fixtures we build work properly.
"""

import os
import subprocess

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
def test_chaos_node(chaos_node):
    # see https://tendermint.readthedocs.io/en/master/getting-started.html
    env = {
        'TMHOME': chaos_node['tmhome'],
        'NDAUHOME': chaos_node['ndauhome'],
        'PATH': os.environ['PATH'],
    }
    print(f'env: {env}')

    try:
        address = subp(
            'docker-compose port tendermint 46657',
            env=env,
            stderr=subprocess.STDOUT,
        )
        print(f'address: {address}')

        subp(f'curl -s {address}/status')

    except subprocess.CalledProcessError as e:
        print('--STDOUT--')
        print(e.stdout)
        print('--RETURN CODE--')
        print(e.returncode)
        raise


@pytest.mark.meta
def test_chaos_node_and_tool(chaos_node_and_tool):
    c = chaos_node_and_tool
    # ensure that 'chaos conf' has already been run
    subp(f'{c["tool"]["bin"]} id list', env=c['env'])
    # ensure that the node is running and the tool is configured
    # to connect to it
    subp(f'{c["tool"]["bin"]} info', env=c['env'])


@pytest.mark.meta
def test_whitelist_build(whitelist_build):
    # ensure the binary exists and can run
    subp(f'{whitelist_build["bin"]} chaos path')
