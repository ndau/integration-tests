# Integration Tests

Testing the chaosnode system in its entirety is relatively complicated, because it is a system of many interlocking parts:

- The heart is the node itself, [`chaos-go`](https://us-east-1.console.aws.amazon.com/codecommit/home?region=us-east-1#/repository/chaos-go/browse/HEAD/--/). This is at simplest a docker-compose service orchestrating (currently) three separate executables, though it also includes a tool with which a many-node configuration can be generated for test purposes.

- The primary interface with `chaos-go` is the [`chaos`](https://us-east-1.console.aws.amazon.com/codecommit/home?region=us-east-1#/repository/chaostool/browse/HEAD/--/) command, which is both a CLI application and a go library (`tool`) with which to interface with the chaos chain.

- There is a separate tool [`ndwhitelist`](https://us-east-1.console.aws.amazon.com/codecommit/home?region=us-east-1#/repository/whitelist/browse/HEAD/--/) which node operators may use to manage their whitelists for System Change Proposals. Without using this tool, all proposed SCPs will be rejected.

These tools are intended for different audiences and will likely be running on separte machines in production. This makes testing their interactions in a realistic way a non-trivial proposition.

## Getting Started

1. Install [python3.6 or later](https://www.python.org/downloads/)
1. Install `pipenv`: `pip3 install pipenv`
1. Install `pytest`: `pip3 install pytest`
1. Install `toml`: `pip3 install toml`
1. Clone this repo into `~/go/src/github.com/oneiro-ndev` so that it is next to the `chaos` and `ndau` repos
1. `cd` into the repo root
1. Install dependencies: `pipenv sync`
1. Load the environment: `pipenv shell`

## Running the tests

Tests are handled via the `pytest` unit-testing tool. To run the entire test suite, simply execute the `pytest -v` command from the repo root; it'll take care of everything else. If you'd like the testing to stop at failure X, run the command `pytest -v --maxfail=X`.  If you'd like to run a particular test, run the command `pytest test_mod.py::test_func`.  There are several command-line flags available:

- `--chaos-go-label`, `--chaostool-label`, `--whitelist-label` set the label of the specified repository to build and test. A label can be anything that git accepts as a label: a short hash, full hash, branch name, and tag are all valid options. All of these default to `master`.
- `--runslow` if set runs tests which have been marked as slow. None of these tests are particularly speedy due to the heavy fixtures in play, but some are particularly poky.
- `--skipmeta` if set skips metatests. Metatests are tests which verify that the fixtures in use to fetch and build the various dependencies are all working properly.
- `--keeptemp` if set keeps temp files and directories around to help debug test failures.  Normally all files and directories created during testing will be removed at the end of the tests.  Temporary files will normally be named in the form of /tmp/XXXXXX_YYYYYYYY, where X's are the tool or component name, and Y's are a randomly generated string.

- `--run_kub` Instead of building chaosnode and running locally, tries to connect to existing Kubernetes instance of chaosnode in devnet and runs tests with local docker built chaostool.

## Testing Strategy

This repository contains a `Dockerfile` which when built produces a container which contains `chaos-go`, `chaos`, `ndwhitelist`, their associated tools and utilities, and the actual test scripts. Tests are executed when the container is run.

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
- [X] `chaostool` can send a non-whitelisted SCP but it it not accepted
- [X] `ndwhitelist` can whitelist a SCP
- [X] `chaostool` can send a whitelisted SCP and it is accepted

### Two validator nodes


- [*] Two validator nodes pass all single validator node tests
- [X] When node power is equal, and one node has whitelisted a SCP but the other has not, a transaction setting that SCP is not accepted
- [ ] `chaostool` can send Globally Trusted Validator Change transactions and see those updates reflected in the consensus
- [ ] When one node has >2/3 of the voting power, and that node has whitelisted a SCP but the other has not, a transaction setting that SCP is accepted
- [ ] `chaostool` can set a value in on one node and retrieve it from the other node

[*]: Some tests currently skipped because test implementation incomplete.

### Four validator nodes and six verifier nodes

- [ ] a verifier can have voting power added and become a validator
- [ ] a validator can have its voting power rescinded and become a verifier

### Dynamic nodes

- [ ] a new node can join a running network
- [ ] a node dynamically added to a network can have voting power granted
