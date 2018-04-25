"""
Define pytest fixtures
"""
import pytest
from src.conf import load
from src.repo import go_repo, within


def pytest_addoption(parser):
    parser.addoption("--chaos-go-label", action="store", default="master",
                     help="Label to use for chaos-go")
    parser.addoption("--chaostool-label", action="store", default="master",
                     help="Label to use for chaostool")
    parser.addoption("--whitelist-label", action="store", default="master",
                     help="Label to use for whitelist")


@pytest.fixture(scope='module')
def chaos_go_repo(request):
    """Return a context manager within which chaos-go is available."""
    label = request.config.getoption('--chaos-go-label')
    conf = load(chaos_go_label=label)['chaos-go']
    return go_repo(conf['repo'], conf['logical'], conf['label'])


@pytest.fixture(scope='module')
def chaostool_repo(request):
    """Return a context manager within which chaostool is available."""
    label = request.config.getoption('--chaostool-label')
    conf = load(chaostool_label=label)['chaostool']
    return go_repo(conf['repo'], conf['logical'], conf['label'])


@pytest.fixture(scope='module')
def whitelist_repo(request):
    """Return a context manager within which whitelist is available."""
    label = request.config.getoption('--whitelist-label')
    conf = load(whitelist_label=label)['whitelist']
    return go_repo(conf['repo'], conf['logical'], conf['label'])
