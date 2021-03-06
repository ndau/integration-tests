#  ----- ---- --- -- -
#  Copyright 2020 The Axiom Foundation. All Rights Reserved.
# 
#  Licensed under the Apache License 2.0 (the "License").  You may not use
#  this file except in compliance with the License.  You can obtain a copy
#  in the file LICENSE in the source distribution or at
#  https://www.apache.org/licenses/LICENSE-2.0.txt
#  - -- --- ---- -----

import os

import toml
from src.util.repo import within
from src.util.subp import subp


def load(
    *,
    chaos_go_label=None,
    chaostool_label=None,
    ndau_go_label=None,
    ndautool_label=None,
):
    """
    Load configuration data.

    First load values from conf.toml, and then override certain of them.
    The expected use case is to optionally override certain values from the
    command line.
    """
    with within(os.path.dirname(os.path.abspath(__file__))):
        conf_path = os.path.join(subp("git rev-parse --show-toplevel"), "conf.toml")
    with open(conf_path, "rt") as conf_fp:
        conf = toml.load(conf_fp)
    locs = locals()
    for repo in ("chaos_go", "chaostool", "ndau_go", "ndautool"):
        label = repo + "_label"
        if locs[label] is not None:
            conf[repo.replace("_", "-")]["label"] = locs[label]
    return conf
