#!/usr/bin/env python3

"""
Utility for printing the git hashes of the repos and branches defined
in the conf.toml file.
"""

from src.util.conf import load
from src.util.repo import go_repo
from src.util.subp import subp


def hashes(conf):
    for name, settings in conf.items():
        with go_repo(settings["repo"], settings["logical"], settings["label"]):
            hash = subp("git rev-parse --short HEAD")
            print(f'Hash of {name} at {settings["label"]}: {hash}')


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--chaos-go-label", default="master", help="Label to check out for chaos-go"
    )
    parser.add_argument(
        "--chaostool-label", default="master", help="Label to check out for chaostool"
    )

    args = parser.parse_args()
    conf = load(
        chaos_go_label=args.chaos_go_label,
        chaostool_label=args.chaostool_label,
    )
    hashes(conf)
