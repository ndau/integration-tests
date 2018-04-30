"""
Define pytest fixtures.

These fixtures configure and run the chaos chain tools.
"""
import os
import subprocess
import time
from tempfile import NamedTemporaryFile, TemporaryDirectory

import pytest
from src.conf import load
from src.repo import go_repo, within
from src.subp import subp


def pytest_addoption(parser):
    """See https://docs.pytest.org/en/latest/example/simple.html."""
    parser.addoption("--chaos-go-label", action="store", default="master",
                     help="Label to use for chaos-go")
    parser.addoption("--chaostool-label", action="store", default="master",
                     help="Label to use for chaostool")
    parser.addoption("--whitelist-label", action="store", default="master",
                     help="Label to use for whitelist")
    parser.addoption("--runslow", action="store_true",
                     default=False, help="run slow tests")
    parser.addoption("--skipmeta", action="store_true",
                     default=False, help="skip meta tests")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
    if config.getoption("--skipmeta"):
        skip_meta = pytest.mark.skip(
            reason="--skipmeta used; this test is meta")
        for item in items:
            if "meta" in item.keywords:
                item.add_marker(skip_meta)


@pytest.fixture(scope='session')
def chaos_go_repo(request):
    """Return the path at which chaos-go is available."""
    label = request.config.getoption('--chaos-go-label')
    conf = load(chaos_go_label=label)['chaos-go']
    with go_repo(conf['repo'], conf['logical'], conf['label']) as path:
        yield path


@pytest.fixture(scope='session')
def chaostool_repo(request):
    """Return the path at which chaostool is available."""
    label = request.config.getoption('--chaostool-label')
    conf = load(chaostool_label=label)['chaostool']
    with go_repo(conf['repo'], conf['logical'], conf['label']) as path:
        yield path


@pytest.fixture(scope='session')
def whitelist_repo(request):
    """Return the path at which whitelist is available."""
    label = request.config.getoption('--whitelist-label')
    conf = load(whitelist_label=label)['whitelist']
    with go_repo(conf['repo'], conf['logical'], conf['label']) as path:
        yield path


@pytest.fixture(scope='session')
def chaos_node_build(chaos_go_repo):
    """
    Build a single chaos node.

    Because chaos nodes are stateful, we need to init/run/reset them for
    every test to ensure that the tests each have clean slates. However,
    we only need to actually build the project once per test session.

    That's what this fixture does.
    """
    build_script = os.path.join(chaos_go_repo, 'bin', 'build.sh')
    try:
        with TemporaryDirectory(prefix='ndauhome-', dir='/tmp') as ndauhome, TemporaryDirectory(prefix='tmhome-', dir='/tmp') as tmhome, within(chaos_go_repo):  # noqa: E501
            try:
                subp(
                    build_script,
                    env={'NDAUHOME': ndauhome, 'TMHOME': tmhome},
                    stderr=subprocess.STDOUT,
                )
            except Exception as e:
                print(e.stdout)
                raise
            yield {
                'repo': chaos_go_repo,
                'ndauhome': ndauhome,
                'tmhome': tmhome,
            }
    except FileNotFoundError:
        # we expect a FileNotFoundError here: the current behavior of reset.sh
        # is to delete $TMHOME and $NDAUHOME. That's fine, though it confuses
        # TemporaryDirectory, which expects to need to clean up after itself.
        # We therefore catch this exception and do nothing about it.
        pass


@pytest.fixture
def chaos_node(chaos_node_build):
    """
    Initialize and run a chaos node for this test.

    Because chaos nodes are stateful, we need to init/run/reset them for
    every test. This fixture accomplishes that.
    """
    def run_cmd(cmd, **kwargs):
        try:
            return subp(
                cmd,
                env=dict(
                    NDAUHOME=chaos_node_build['ndauhome'],
                    TMHOME=chaos_node_build['tmhome'],
                    PATH=os.environ['PATH']
                ),
                stderr=subprocess.STDOUT,
                cwd=chaos_node_build['repo'],
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            print('--STDOUT--')
            print(e.stdout)
            print('--RETURN CODE--')
            print(e.returncode)

            raise

    print("chaos_node fixture: running init.sh")
    run_cmd(os.path.join('bin', 'init.sh'))
    print("chaos_node fixture: init.sh finished")

    print("chaos_node fixture: running run.sh")
    # subprocess.run always synchronously waits for the subprocess to terminate
    # that isn't acceptable here, so we fall back to a raw Popen call
    run_script = subprocess.Popen(
        [os.path.join(chaos_node_build['repo'], 'bin', 'run.sh')],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=chaos_node_build['repo'],
        encoding='utf8',
        env=dict(
            NDAUHOME=chaos_node_build['ndauhome'],
            TMHOME=chaos_node_build['tmhome'],
            PATH=os.environ['PATH']
        ),
    )
    # starting tendermint takes a few seconds before it's ready to receive
    # incoming connections
    time.sleep(5)
    run_status = run_script.poll()
    if run_status is not None:
        raise Exception(
            f"run.sh exited unexpectedly with code {run_status}"
        )
    print("chaos_node fixture: run.sh running")

    print("chaos_node fixture: yielding")
    try:
        yield chaos_node_build
    finally:
        print("chaos_node fixture: running reset.sh")
        run_cmd(os.path.join('bin', 'reset.sh'))
        print("chaos_node fixture: reset.sh finished")

        if run_script.poll() is None:
            run_script.terminate()


def run_localenv(cmd):
    """Run a command in the local environment."""
    try:
        return subp(
            cmd,
            stderr=subprocess.STDOUT,
            env=os.environ,
        )
    except subprocess.CalledProcessError as e:
        print(e.stdout)
        raise


@pytest.fixture(scope='session')
def chaostool_build(chaostool_repo):
    """
    Build the chaos tool.

    Note that this doesn't perform any configuration;
    it just builds the binary.
    """
    with within(chaostool_repo):
        run_localenv('glide install')
        with NamedTemporaryFile(prefix='chaostool-', dir='/tmp') as bin_fp:
            run_localenv(f'go build -o {bin_fp.name} ./cmd/chaos')
            yield {
                'repo': chaostool_repo,
                'bin': bin_fp.name,
            }


@pytest.fixture(scope='session')
def whitelist_build(whitelist_repo):
    """
    Build the ndwhitelist binary.

    Note that this doesn't perform any configuration,
    it just builds the binary.
    """
    with within(whitelist_repo):
        run_localenv('dep ensure')
        with NamedTemporaryFile(prefix='whitelist-', dir='/tmp') as bin_fp:
            run_localenv(f'go build -o {bin_fp.name} ./cmd/ndwhitelist')
            yield {
                'repo': whitelist_repo,
                'bin': bin_fp.name,
            }


@pytest.fixture
def chaos_node_and_tool(chaos_node, chaostool_build):
    """
    Run a chaos node, and configure the chaos tool to connect to it.

    This necessarily includes the chaos node; depend only on this fixture,
    not on this plus chaos_node.
    """
    env = {
        'TMHOME': chaos_node['tmhome'],
        'NDAUHOME': chaos_node['ndauhome'],
        'PATH': os.environ['PATH'],
    }

    with within(chaos_node['repo']):
        address = subp(
            'docker-compose port tendermint 46657',
            env=env,
            stderr=subprocess.STDOUT,
        )

    if '://' not in address:
        address = 'http://' + address

    subp(
        f'{chaostool_build["bin"]} conf {address}',
        env=env,
    )

    return {
        'node': chaos_node,
        'tool': chaostool_build,
        'env': env,
    }
