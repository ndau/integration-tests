"""
Test that the fixtures we build work properly.
"""

import os

import pytest
import requests
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
    response = requests.get(chaos_node['rpc_address'])
    response.raise_for_status()
    assert response.json().len() > 0
