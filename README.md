# Integration Tests

Testing the chaosnode system in its entirety is relatively complicated, because it is a system of many interlocking parts:

- The heart is the node itself, [`chaos-go`](https://us-east-1.console.aws.amazon.com/codecommit/home?region=us-east-1#/repository/chaos-go/browse/HEAD/--/). This is at simplest a docker-compose service orchestrating (currently) three separate executables, though it also includes a tool with which a many-node configuration can be generated for test purposes.

- The primary interface with `chaos-go` is the [`chaos`](https://us-east-1.console.aws.amazon.com/codecommit/home?region=us-east-1#/repository/chaostool/browse/HEAD/--/) command, which is both a CLI application and a go library (`tool`) with which to interface with the chaos chain.

These tools are intended for different audiences and will likely be running on separte machines in production. This makes testing their interactions in a realistic way a non-trivial proposition.

## Getting Started

1. Install [python3.6 or later](https://www.python.org/downloads/)
1. Install `pipenv`: `pip3 install pipenv`
1. Install `pytest`: `pip3 install pytest`
1. Install `toml`: `pip3 install toml`
1. Set up Kubernetes tools
    1. Install `kubectl`: `brew install kubernetes-cli`
    1. Create the directory `~/.kube`
    1. Get the `deploy_security` tarball from Oneiro's 1password account
        1. Extract it into a temp directory
        1. Copy the files from `kubectl/*` into `~/.kube`
    1. Put the following line in `~/.kube/dev.yaml`, after the existing `- context` sections, and before the `users:` line:
       - `current-context: dev.cluster.ndau.tech`
    1. Add `export KUBECONFIG=~/.kube/dev.yaml` to your `.bash_profile` and restart your Terminal
    1. Test the Kubernetes tools install by running `kubectl get nodes`
1. Clone this repo into `~/go/src/github.com/oneiro-ndev` so that it is next to the `chaos` and `ndau` repos
1. `cd` into the repo root
1. Install dependencies: `pipenv sync`
1. Load the environment: `pipenv shell`

## Running the tests

Tests are handled via the `pytest` unit-testing tool. To run the entire test suite, simply execute the `pytest -v` command from the repo root; it'll take care of everything else. If you'd like the testing to stop at failure X, run the command `pytest -v --maxfail=X`.  If you'd like to run a particular test, run the command `pytest test_mod.py::test_func`.  There are several command-line flags available:

- `--chaos-go-label` and `--chaostool-label` set the label of the specified repository to build and test. A label can be anything that git accepts as a label: a short hash, full hash, branch name, and tag are all valid options. All of these default to `master`.
- `--runslow` if set runs tests which have been marked as slow. None of these tests are particularly speedy due to the heavy fixtures in play, but some are particularly poky.
- `--skipmeta` if set skips metatests. Metatests are tests which verify that the fixtures in use to fetch and build the various dependencies are all working properly.
- `--keeptemp` if set keeps temp files and directories around to help debug test failures.  Normally all files and directories created during testing will be removed at the end of the tests.  Temporary files will normally be named in the form of /tmp/XXXXXX_YYYYYYYY, where X's are the tool or component name, and Y's are a randomly generated string.
- `--net={devnet|testnet|localnet|...}` instructs the integration tests to run against a remotely running Kubernetes deploy (e.g. `--net=devnet`) vs locally running nodes (`--net=localnet`).  Kubernetes on devnet is the default.  Our integration tests never "build and run" nodes.  Rather, they run tests against already-running nodes.  See documentation in the [commands](https://github.com/oneiro-ndev/commands) repo for how to set up, build and run local nodes.  See the [automation](https://github.com/oneiro-ndev/automation) repo for information regarding Kubernetes setup and deploy.

## Testing Strategy

Tests are written in Python using [pytest](https://docs.pytest.org/en/latest/) and [hypothesis](https://hypothesis.readthedocs.io/en/latest/).

## Tests

### Single validator node

- [X] `chaostool` can connect to `chaos-go` and get status
- [X] `chaostool` can set a value and get it back later
- [X] `chaostool` can remove a value
- [X] `chaostool` can list all namespaces
- [X] `chaostool` can dump all k-v pairs from a given namespace
- [X] `chaostool` can set a value, and a different instance of `chaostool` can retrieve it
- [X] `chaostool` can set a value, and a different instance of `chaostool` cannot overwrite it (i.e. namespaces work)
- [X] `chaostool` can list the history of a value

### Dynamic nodes

- [ ] a new node can join a running network
- [ ] a node dynamically added to a network can have voting power granted
