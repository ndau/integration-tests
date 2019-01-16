"""
Define pytest fixtures.

These fixtures configure and run the chaos chain tools.
"""
import os
import os.path
import subprocess
import time
import tempfile
from tempfile import NamedTemporaryFile, TemporaryDirectory
import pdb
import shutil

import pytest
from src.util.conf import load
from src.util.repo import go_repo, within
from src.util.subp import subp
import src.util.constants
from pathlib import Path


def pytest_addoption(parser):
    """See https://docs.pytest.org/en/latest/example/simple.html."""
    parser.addoption("--chaos-go-label", action="store", default="master",
                     help="Label to use for chaos-go")
    parser.addoption("--chaostool-label", action="store", default="master",
                     help="Label to use for chaostool")
    parser.addoption("--whitelist-label", action="store", default="master",
                     help="Label to use for whitelist")
    parser.addoption("--ndau-go-label", action="store", default="master",
                     help="Label to use for ndau-go")
    parser.addoption("--ndautool-label", action="store", default="master",
                     help="Label to use for ndautool")
    parser.addoption("--runslow", action="store_true",
                     default=False, help="run slow tests")
    parser.addoption("--skipmeta", action="store_true",
                     default=False, help="skip meta tests")
    parser.addoption("--keeptemp", action="store_true",
                     default=False, help="keep temporary files for debugging failures")
    parser.addoption("--net", action="store",
                     default="devnet", help="which node net to use, e.g. devnet or localnet")


@pytest.fixture(scope='session')
def keeptemp(request):
    return request.config.getoption("--keeptemp")


@pytest.fixture(scope='session')
def use_kub(request):
    return request.config.getoption("--net") != "localnet"


@pytest.fixture(scope='session')
def node_net(request):
    return request.config.getoption("--net")


def pytest_collection_modifyitems(config, items):
    """Pytest func to adjust which tests are run."""
    if not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
    if config.getoption("--skipmeta"):
        skip_meta = pytest.mark.skip(
            reason="skipped due to --skipmeta option")
        for item in items:
            if "meta" in item.keywords:
                item.add_marker(skip_meta)


@pytest.fixture(autouse=True, scope='session')
def setup_teardown(chaos_go_repo, chaostool_repo, whitelist_repo, ndau_go_repo, ndautool_repo):
    # Setup...

    yield

    # Teardown...

    # Wipe temp .kube directories after all tests complete.
    for repo in (chaos_go_repo, chaostool_repo, whitelist_repo, ndau_go_repo, ndautool_repo):
        with within(repo):
            run_localenv('rm -rf .kube')


@pytest.fixture(scope='session')
def get_ndauhome_dir(use_kub, keeptemp):
    if use_kub:
        ndauhome_dir = tempfile.mkdtemp(prefix='ndauhome-', dir='/tmp')
    else:
        # Use the local ndau home directory that's already there, set up by the localnet.
        ndauhome_dir = os.path.expanduser('~/.localnet/data/ndau-0')
        # Make sure it's really there.  If it isn't, the user hasn't set up a local server.
        assert os.path.isdir(ndauhome_dir)
    yield ndauhome_dir
    if use_kub and not keeptemp:
        shutil.rmtree(ndauhome_dir, True)


@pytest.fixture(scope='session')
def get_chaos_tmhome_dir(use_kub, keeptemp):
    if use_kub:
        tmhome_dir = tempfile.mkdtemp(prefix='tmhome-', dir='/tmp')
    else:
        # Use the local tm home directory that's already there, set up by the localnet.
        tmhome_dir = os.path.expanduser('~/.localnet/data/tendermint-chaos-0')
        # Make sure it's really there.  If it isn't, the user hasn't set up a local server.
        assert os.path.isdir(tmhome_dir)
    yield tmhome_dir
    if use_kub and not keeptemp:
        shutil.rmtree(tmhome_dir, True)


@pytest.fixture(scope='session')
def get_ndau_tmhome_dir(use_kub, keeptemp):
    if use_kub:
        tmhome_dir = tempfile.mkdtemp(prefix='tmhome-', dir='/tmp')
    else:
        # Use the local tm home directory that's already there, set up by the localnet.
        tmhome_dir = os.path.expanduser('~/.localnet/data/tendermint-ndau-0')
        # Make sure it's really there.  If it isn't, the user hasn't set up a local server.
        assert os.path.isdir(tmhome_dir)
    yield tmhome_dir
    if use_kub and not keeptemp:
        shutil.rmtree(tmhome_dir, True)


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
def ndau_go_repo(request):
    """Return the path at which ndau-go is available."""
    label = request.config.getoption('--ndau-go-label')
    conf = load(ndau_go_label=label)['ndau-go']
    with go_repo(conf['repo'], conf['logical'], conf['label']) as path:
        yield path


@pytest.fixture(scope='session')
def ndautool_repo(request):
    """Return the path at which ndautool is available."""
    label = request.config.getoption('--ndautool-label')
    conf = load(ndautool_label=label)['ndautool']
    with go_repo(conf['repo'], conf['logical'], conf['label']) as path:
        yield path


@pytest.fixture(scope='session')
def chaos_node_build(chaos_go_repo, get_ndauhome_dir, get_chaos_tmhome_dir):
    """
    Build a single chaos node.

    Because chaos nodes are stateful, we need to init/run/reset them for
    every test to ensure that the tests each have clean slates. However,
    we only need to actually build the project once per test session.

    That's what this fixture does.
    """
    ndauhome = get_ndauhome_dir
    tmhome = get_chaos_tmhome_dir
    print(f'build ndauhome: {ndauhome}')
    print(f'build tmhome: {tmhome}')
    with within(chaos_go_repo):            
        yield {
            'repo': chaos_go_repo,
            'ndauhome': ndauhome,
            'tmhome': tmhome,
        }


@pytest.fixture
def chaos_node_exists(use_kub, node_net):
    """
    Check if we can communicate with chaos node.

    Because chaos nodes are stateful, we need to init/run/reset them for
    every test. This fixture accomplishes that.
    """
    def run_cmd(cmd, **kwargs):
        print(f'cmd: {cmd}')
        try:
            foo = subp(
                cmd,
                env={'KUBECONFIG': os.environ['KUBECONFIG'], 'PATH': os.environ['PATH']},
                stderr=subprocess.STDOUT,
                **kwargs,
            )
            return foo
        except subprocess.CalledProcessError as e:
            print('--STDOUT--')
            print(e.stdout)
            print('--RETURN CODE--')
            print(e.returncode)

            raise

    print("chaos node exists")
    if use_kub:
        address = run_cmd('kubectl get nodes -o jsonpath=\'{.items[*].status.addresses[?(@.type=="ExternalIP")].address}\' | tr " " "\n" | head -n 1 | tr -d "[:space:]"')
        nodenet0_rpc = run_cmd('kubectl get service --namespace default -o jsonpath=\'{.spec.ports[?(@.name=="rpc")].nodePort}\' ' + node_net + '-0-nodegroup-chaos-tendermint-service')
        nodenet1_rpc = run_cmd('kubectl get service --namespace default -o jsonpath=\'{.spec.ports[?(@.name=="rpc")].nodePort}\' ' + node_net + '-1-nodegroup-chaos-tendermint-service')
    else:
        address = 'localhost'
        nodenet0_rpc = str(src.util.constants.LOCALNET0_CHAOS_RPC)
        nodenet1_rpc = str(src.util.constants.LOCALNET1_CHAOS_RPC)
    print(f'address: {address}')
    print(f'nodenet0_rpc: {nodenet0_rpc}')
    print(f'nodenet1_rpc: {nodenet1_rpc}')
    nodenet0_res = run_cmd(f'curl -s http://{address}:{nodenet0_rpc}/status')
    nodenet1_res = run_cmd(f'curl -s http://{address}:{nodenet1_rpc}/status')
    print(f'nodenet0_res: {nodenet0_res}')
    print(f'nodenet1_res: {nodenet1_res}')
    yield {
        'address': address,
        'nodenet0_rpc': nodenet0_rpc,
        'nodenet1_rpc': nodenet1_rpc
    }


@pytest.fixture
def chaos_node(chaos_node_build):
    """Wrapper that yields chaos_node_build."""
    print("chaos_node fixture: yielding")
    yield chaos_node_build


@pytest.fixture(scope='session')
def ndau_node_build(ndau_go_repo, get_ndauhome_dir, get_ndau_tmhome_dir):
    """
    Build a single ndau node.

    Because ndau nodes are stateful, we need to init/run/reset them for
    every test to ensure that the tests each have clean slates. However,
    we only need to actually build the project once per test session.

    That's what this fixture does.
    """
    ndauhome = get_ndauhome_dir
    tmhome = get_ndau_tmhome_dir
    print(f'build ndauhome: {ndauhome}')
    print(f'build tmhome: {tmhome}')
    with within(ndau_go_repo):            
        yield {
            'repo': ndau_go_repo,
            'ndauhome': ndauhome,
            'tmhome': tmhome,
        }


@pytest.fixture
def ndau_node_exists(use_kub, node_net):
    """
    Check if we can communicate with ndau node.

    Because ndau nodes are stateful, we need to init/run/reset them for
    every test. This fixture accomplishes that.
    """
    def run_cmd(cmd, **kwargs):
        print(f'cmd: {cmd}')
        try:
            foo = subp(
                cmd,
                env={'KUBECONFIG': os.environ['KUBECONFIG'], 'PATH': os.environ['PATH']},
                stderr=subprocess.STDOUT,
                **kwargs,
            )
            return foo
        except subprocess.CalledProcessError as e:
            print('--STDOUT--')
            print(e.stdout)
            print('--RETURN CODE--')
            print(e.returncode)

            raise

    print("ndau node exists")
    if use_kub:
        address = run_cmd('kubectl get nodes -o jsonpath=\'{.items[*].status.addresses[?(@.type=="ExternalIP")].address}\' | tr " " "\n" | head -n 1 | tr -d "[:space:]"')
        nodenet0_rpc = run_cmd('kubectl get service --namespace default -o jsonpath=\'{.spec.ports[?(@.name=="rpc")].nodePort}\' ' + node_net + '-0-nodegroup-ndau-tendermint-service')
        nodenet1_rpc = run_cmd('kubectl get service --namespace default -o jsonpath=\'{.spec.ports[?(@.name=="rpc")].nodePort}\' ' + node_net + '-1-nodegroup-ndau-tendermint-service')
    else:
        address = 'localhost'
        nodenet0_rpc = str(src.util.constants.LOCALNET0_NDAU_RPC)
        nodenet1_rpc = str(src.util.constants.LOCALNET1_NDAU_RPC)
    print(f'address: {address}')
    print(f'nodenet0_rpc: {nodenet0_rpc}')
    print(f'nodenet1_rpc: {nodenet1_rpc}')
    nodenet0_res = run_cmd(f'curl -s http://{address}:{nodenet0_rpc}/status')
    nodenet1_res = run_cmd(f'curl -s http://{address}:{nodenet1_rpc}/status')
    print(f'nodenet0_res: {nodenet0_res}')
    print(f'nodenet1_res: {nodenet1_res}')
    yield {
        'address': address,
        'nodenet0_rpc': nodenet0_rpc,
        'nodenet1_rpc': nodenet1_rpc
    }


@pytest.fixture
def ndau_node(ndau_node_build):
    """Wrapper that yields ndau_node_build."""
    print("ndau_node fixture: yielding")
    yield ndau_node_build


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
def chaostool_build(keeptemp, chaostool_repo):
    """
    Build the chaos tool.

    Note that this doesn't perform any configuration;
    it just builds the binary.
    """
    with within(chaostool_repo):
        run_localenv('dep ensure')
        with NamedTemporaryFile(prefix='chaostool-', dir='/tmp', delete=not keeptemp) as bin_fp:
            run_localenv(f'go build -o {bin_fp.name} ./cmd/chaos')
            yield {
                'repo': chaostool_repo,
                'bin': bin_fp.name,
            }


@pytest.fixture(scope='session')
def whitelist_build(keeptemp, whitelist_repo):
    """
    Build the ndwhitelist binary.

    Note that this doesn't perform any configuration,
    it just builds the binary.
    """
    with within(whitelist_repo):
        run_localenv('dep ensure')
        with NamedTemporaryFile(prefix='whitelist-', dir='/tmp', delete=not keeptemp) as bin_fp:
            run_localenv(f'go build -o {bin_fp.name} ./cmd/ndwhitelist')
            yield {
                'repo': whitelist_repo,
                'bin': bin_fp.name,
            }


@pytest.fixture(scope='session')
def ndautool_build(keeptemp, ndautool_repo):
    """
    Build the ndau tool.

    Note that this doesn't perform any configuration;
    it just builds the binary.
    """
    with within(ndautool_repo):
        run_localenv('dep ensure')
        with NamedTemporaryFile(prefix='ndautool-', dir='/tmp', delete=not keeptemp) as bin_fp:
            run_localenv(f'go build -o {bin_fp.name} ./cmd/ndau')
            yield {
                'repo': ndautool_repo,
                'bin': bin_fp.name,
            }


@pytest.fixture
def chaos_node_and_tool(chaos_node, chaostool_build, chaos_node_exists):
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

    # Localnet already has the conf set up.
    if use_kub:
        address = 'http://' + chaos_node_exists['address'] + ':' + chaos_node_exists['nodenet0_rpc']
        subp(
            f'{chaostool_build["bin"]} conf {address}',
            env=env,
        )

    return {
        'node': chaos_node,
        'tool': chaostool_build,
        'env': env,
    }


@pytest.fixture
def ndau_node_and_tool(ndau_node, ndautool_build, ndau_node_exists):
    """
    Run a ndau node, and configure the ndau tool to connect to it.

    This necessarily includes the ndau node; depend only on this fixture,
    not on this plus ndau_node.
    """
    env = {
        'TMHOME': ndau_node['tmhome'],
        'NDAUHOME': ndau_node['ndauhome'],
        'PATH': os.environ['PATH'],
    }

    # Localnet already has the conf set up.
    if use_kub:
        address = 'http://' + ndau_node_exists['address'] + ':' + ndau_node_exists['nodenet0_rpc']
        subp(
            f'{ndautool_build["bin"]} conf {address}',
            env=env,
        )

    return {
        'node': ndau_node,
        'tool': ndautool_build,
        'env': env,
    }


@pytest.fixture
def chaos_node_two_validator_build(chaos_go_repo):
    """
    Build a network containing two chaos nodes.

    Because chaos nodes are stateful, we need to init/run/reset them for
    every test to ensure that the tests each have clean slates. However,
    we only need to actually build the project once per test session.

    That's what this fixture does.
    """
    pypath = os.path.join(chaos_go_repo, 'py')

    def gen_nodes(cmd, **kwargs):
        try:
            return subp(
                # JSG run pipenv install to import modules needed by gen_nodes.py
                f'pipenv install; pipenv run ./gen_nodes.py {cmd}',
                stderr=subprocess.STDOUT,
                env={
                    'LC_ALL': 'en_US.UTF-8',
                    'LANG': 'en_US.UTF-8',
                    'PATH': os.environ['PATH'],
                },
                cwd=pypath,
            )
        except Exception as e:
            print(e.stdout)
            raise

    with TemporaryDirectory(prefix='multinode-', dir='/tmp') as mnhome:
        script_dir = os.path.join(mnhome, 'scripts')
        gen_nodes(f'2 --home {mnhome} --output {script_dir}')
        yield {
            'repo': chaos_go_repo,
            'multinode': mnhome,
            'scripts': script_dir,
            'gen_nodes': gen_nodes,
        }


@pytest.fixture
def chaos_node_two_validator(chaos_node_two_validator_build):
    """
    Initialize and run a two node chaos network for this test.

    Because chaos nodes are stateful, we need to init/run/reset them for
    every test. This fixture accomplishes that.
    """
    def run_cmd(cmd, **kwargs):
        try:
            return subp(
                cmd,
                stderr=subprocess.STDOUT,
                cwd=chaos_node_two_validator_build['repo'],
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            print('--STDOUT--')
            print(e.stdout)
            raise

    print("chaos_node_two_validator fixture: running run_many.sh")
    # subprocess.run always synchronously waits for the subprocess to terminate
    # that isn't acceptable here, so we fall back to a raw Popen call
    print(f'run_many command: {[os.path.join(chaos_node_two_validator_build["scripts"], "run_many.sh",)]}')
    run_script = subprocess.Popen(
        [os.path.join(
            chaos_node_two_validator_build['scripts'],
            'run_many.sh',
        )],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=chaos_node_two_validator_build['repo'],
        encoding='utf8',
    )

    # starting tendermint takes a few seconds before it's ready to receive
    # incoming connections. Therefore, just keep delaying until it succeeds,
    # up to one minute.
    address = chaos_node_two_validator_build['gen_nodes'](
        '2 --rpc-address | head -n 1'
    )
    upcheck_interval = 2
    for attempt in range(0, 60, upcheck_interval):
        run_status = run_script.poll()
        if run_status is not None:
            raise Exception(
                f"run_many.sh exited unexpectedly with code {run_status}"
            )
        print(f'Attempt to start chaos node @ {attempt}s:')
        try:
            run_cmd(f'curl -s {address}/status')
        except subprocess.CalledProcessError as e:
            pass
        else:
            break

        time.sleep(upcheck_interval)

    print("chaos_node_two_validator fixture: run_many.sh running")

    print("chaos_node_two_validator fixture: yielding")
    try:
        yield dict(
            **chaos_node_two_validator_build,
            run=run_cmd
        )
    finally:
        print("chaos_node_two_validator fixture: running stop_many.sh")
        run_cmd(os.path.join(
            chaos_node_two_validator_build['scripts'],
            'stop_many.sh',
        ))
        print("chaos_node_two_validator fixture: stop_many.sh finished")

        if run_script.poll() is None:
            run_script.terminate()


@pytest.fixture
def two_chaos_nodes_and_tool(chaos_node_two_validator, chaostool_build):
    """
    Run a pair of chaos nodes, and configure the chaos tool to connect to it.

    For simplicity, the 'chaos' function returned here is configured to connect
    only to the first node, but enough information is provided that it should
    be simple to write a subfixture connecting to a different node.
    """
    ndauhomes = chaos_node_two_validator['run'](
        f'find {chaos_node_two_validator["multinode"]}'
        ' -type d -name ndau -print'
    ).splitlines()

    env = {
        'PATH': os.environ['PATH'],
        'NDAUHOME': ndauhomes[0],
    }

    print('ndauhome:', env['NDAUHOME'])

    gen_nodes = chaos_node_two_validator['gen_nodes']
    address = gen_nodes('2 --rpc-address').splitlines()[0]

    if '://' not in address:
        address = 'http://' + address

    subp(
        f'{chaostool_build["bin"]} conf {address}',
        env=env,
    )

    def chaos(cmd, **kwargs):
        try:
            return subp(
                f'{chaostool_build["bin"]} {cmd}',
                env=env,
                stderr=subprocess.STDOUT,
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            print(e.stdout)
            raise

    return {
        'node': chaos_node_two_validator,
        'tool': chaostool_build,
        'env': env,
        'chaos': chaos,
    }


@pytest.fixture
def chaos(chaos_node_and_tool):
    """
    Fixture providing a chaos function.

    This function calls the chaos command in a configured environment.
    """
    def rf(cmd, **kwargs):
        try:
            return subp(
                f'{chaos_node_and_tool["tool"]["bin"]} {cmd}',
                env=chaos_node_and_tool["env"],
                stderr=subprocess.STDOUT,
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            print(e.stdout)
            raise
    return rf


@pytest.fixture
def ndau(ndau_node_and_tool):
    """
    Fixture providing a ndau function.

    This function calls the ndau command in a configured environment.
    """
    def rf(cmd, **kwargs):
        try:
            return subp(
                f'{ndau_node_and_tool["tool"]["bin"]} {cmd}',
                env=ndau_node_and_tool["env"],
                stderr=subprocess.STDOUT,
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            print(e.stdout)
            raise
    return rf


@pytest.fixture
def chaos_no_error(chaos_node_and_tool):
    """
    Fixture providing a chaos function.

    This function calls the chaos command in a configured environment.
    """
    def rf(cmd, **kwargs):
        try:
            return subp(
                f'{chaos_node_and_tool["tool"]["bin"]} {cmd}',
                env=chaos_node_and_tool["env"],
                stderr=subprocess.STDOUT,
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            # Don't raise.  Callers use this to process the error message.
            return e.stdout.rstrip('\n')

    return rf


@pytest.fixture
def ndau_no_error(ndau_node_and_tool):
    """
    Fixture providing a ndau function.

    This function calls the ndau command in a configured environment.
    """
    def rf(cmd, **kwargs):
        try:
            return subp(
                f'{ndau_node_and_tool["tool"]["bin"]} {cmd}',
                env=ndau_node_and_tool["env"],
                stderr=subprocess.STDOUT,
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            # Don't raise.  Callers use this to process the error message.
            return e.stdout.rstrip('\n')

    return rf


@pytest.fixture
def chaos_namespace_query(chaos_node_and_tool):
    """
    Similar to chaos('dump <ns>') that allows for a non-zero return value.
    """
    def rf(ns, **kwargs):
        try:
            return subp(
                f'{chaos_node_and_tool["tool"]["bin"]} dump {ns}',
                env=chaos_node_and_tool["env"],
                stderr=subprocess.STDOUT,
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            # Don't raise.  Callers use this to see if accounts exist.
            return e.stdout.rstrip('\n')

    return rf


@pytest.fixture
def ndau_account_query(ndau_node_and_tool):
    """
    Similar to ndau('account query <account_name>') that allows for a non-zero return value.
    """
    def rf(account_name, **kwargs):
        try:
            return subp(
                f'{ndau_node_and_tool["tool"]["bin"]} account query {account_name}',
                env=ndau_node_and_tool["env"],
                stderr=subprocess.STDOUT,
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            # Don't raise.  Callers use this to see if accounts exist.
            return e.stdout.rstrip('\n')

    return rf


@pytest.fixture
def set_pre_genesis_tx_fees(chaos):
    """Set up zero transaction fees for pre-genesis tests."""
    sys_ns = src.util.constants.SYSTEM_NAMESPACE
    key = 'TransactionFeeScript'
    zero_fee_script = 'oAAgiA=='
    chaos(f'set {sys_ns} -k {key} -v {zero_fee_script}')


@pytest.fixture
def set_post_genesis_tx_fees(chaos):
    """Set up non-zero transaction fees for post-genesis tests."""
    sys_ns = src.util.constants.SYSTEM_NAMESPACE
    key = 'TransactionFeeScript'
    one_napu_fee_script = 'oAAaiA=='
    chaos(f'set {sys_ns} -k {key} -v {one_napu_fee_script}')


@pytest.fixture(autouse=True)
def set_addresses_in_toml(use_kub, ndau):
    # When running on localnet, the rfe address is already present in the config.
    if not use_kub:
        return

    conf_path = ndau('conf-path')

    # If the entries are there already, we're done.
    f = open(conf_path, 'r')
    conf_lines = f.readlines()
    f.close()
    if any(src.util.constants.RFE_ADDRESS in line for line in conf_lines) and \
       any(src.util.constants.NNR_ADDRESS in line for line in conf_lines) and \
       any(src.util.constants.CVC_ADDRESS in line for line in conf_lines):
        return

    # Write addresses and keys into ndautool.toml file.
    f = open(conf_path, 'a')
    f.write('[rfe]\n')
    f.write(f'  address = "{src.util.constants.RFE_ADDRESS}"\n')
    f.write(f'  keys = ["{src.util.constants.RFE_KEY}"]\n')
    f.write('\n')
    f.write('[nnr]\n')
    f.write(f'  address = "{src.util.constants.NNR_ADDRESS}"\n')
    f.write(f'  keys = ["{src.util.constants.NNR_KEY}"]\n')
    f.write('[cvc]\n')
    f.write(f'  address = "{src.util.constants.CVC_ADDRESS}"\n')
    f.write(f'  keys = ["{src.util.constants.CVC_KEY}"]\n')
    f.close()

    # Make sure the addresses exist in ndautool.toml file.
    f = open(conf_path, 'r')
    conf_lines = f.readlines()
    f.close()
    assert any(src.util.constants.RFE_ADDRESS in line for line in conf_lines)
    assert any(src.util.constants.NNR_ADDRESS in line for line in conf_lines)
    assert any(src.util.constants.CVC_ADDRESS in line for line in conf_lines)
