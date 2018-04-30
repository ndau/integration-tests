# Integration Tests

Testing the chaosnode system in its entirety is relatively complicated, because it is a system of many interlocking parts:

- The heart is the node itself, [`chaos-go`](https://us-east-1.console.aws.amazon.com/codecommit/home?region=us-east-1#/repository/chaos-go/browse/HEAD/--/). This is at simplest a docker-compose service orchestrating (currently) three separate executables, though it also includes a tool with which a many-node configuration can be generated for test purposes.

- The primary interface with `chaos-go` is the [`chaos`](https://us-east-1.console.aws.amazon.com/codecommit/home?region=us-east-1#/repository/chaostool/browse/HEAD/--/) command, which is both a CLI application and a go library (`tool`) with which to interface with the chaos chain.

- There is a separate tool [`ndwhitelist`](https://us-east-1.console.aws.amazon.com/codecommit/home?region=us-east-1#/repository/whitelist/browse/HEAD/--/) which node operators may use to manage their whitelists for System Change Proposals. Without using this tool, all proposed SCPs will be rejected.

These tools are intended for different audiences and will likely be running on separte machines in production. This makes testing their interactions in a realistic way a non-trivial proposition.

## Testing Strategy

This repository contains a `Dockerfile` which when built produces a container which contains `chaos-go`, `chaos`, `ndwhitelist`, their associated tools and utilities, and the actual test scripts. Tests are executed when the container is run.

Tests are written in Python using [pytest](https://docs.pytest.org/en/latest/) and [hypothesis](https://hypothesis.readthedocs.io/en/latest/).

## Tests

### Single validator node

- [X] `chaostool` can connect to `chaos-go` and get status
- [X] `chaostool` can set a value and get it back later
- [ ] `chaostool` can remove a value
- [ ] `chaostool` can list all namespaces
- [ ] `chaostool` can dump all k-v pairs from a given namespace
- [ ] `chaostool` can set a value, and a different instance of `chaostool` can retrieve it
- [ ] `chaostool` can set a value, and a different instance of `chaostool` cannot overwrite it (i.e. namespaces work)
- [ ] `chaostool` can list the history of a value
- [ ] `chaostool` can send a non-whitelisted SCP but it it not accepted
- [ ] `ndwhitelist` can whitelist a SCP
- [ ] `chaostool` can send a whitelisted SCP and it is accepted

### Two validator nodes

Two validator nodes must pass all single validator node tests, plus the following:

- [ ] `chaostool` can send Globally Trusted Validator Change transactions and see those updates reflected in the consensus
- [ ] When node power is equal, and one node has whitelisted a SCP but the other has not, a transaction setting that SCP is not accepted
- [ ] When one node has >2/3 of the voting power, and that node has whitelisted a SCP but the other has not, a transaction setting that SCP is accepted
- [ ] `chaostool` can set a value in on one node and retrieve it from the other node

### Four validator nodes and six verifier nodes

- [ ] a verifier can have voting power added and become a validator
- [ ] a validator can have its voting power rescinded and become a verifier

### Dynamic nodes

- [ ] a new node can join a running network
- [ ] a node dynamically added to a network can have voting power granted
