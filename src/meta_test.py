"""
Test that the fixtures we build work properly.
"""

import os

import pytest
from src.repo import within
from src.subp import subp


@pytest.mark.meta
def test_chaos_go_repo(chaos_go_repo, request):
    requested_label = request.config.getoption('--chaos-go-label')
    assert os.path.exists(chaos_go_repo)
    with within(chaos_go_repo):
        actual_label = subp('git rev-parse --abbrev-ref HEAD')
        assert requested_label == actual_label


@pytest.mark.meta
def test_chaostool_repo(chaostool_repo, request):
    requested_label = request.config.getoption('--chaostool-label')
    assert os.path.exists(chaostool_repo)
    with within(chaostool_repo):
        actual_label = subp('git rev-parse --abbrev-ref HEAD')
        assert requested_label == actual_label


@pytest.mark.meta
def test_whitelist_repo(whitelist_repo, request):
    requested_label = request.config.getoption('--whitelist-label')
    assert os.path.exists(whitelist_repo)
    with within(whitelist_repo):
        actual_label = subp('git rev-parse --abbrev-ref HEAD')
        assert requested_label == actual_label
