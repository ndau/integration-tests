import toml


def load(*, chaos_go_label=None, chaostool_label=None, whitelist_label=None):
    """
    Load configuration data.

    First load values from conf.toml, and then override certain of them.
    The expected use case is to optionally override certain values from the
    command line.
    """
    with open('conf.toml', 'rt') as conf_fp:
        conf = toml.load(conf_fp)
    locs = locals()
    for repo in ('chaos_go', 'chaostool', 'whitelist'):
        label = repo + '_label'
        if locs[label] is not None:
            conf[repo.replace('_', '-')]['label'] = locs[label]
    return conf
