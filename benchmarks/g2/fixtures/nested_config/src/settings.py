from .merge import deep_merge

SCHEMA = {
    "network": {"timeout", "retries"},
    "logging": {"level"},
    "features": {"safe_mode", "plugins"},
}

def configure(base, env, cli):
    """Apply two priority layers (base < env < cli)."""
    interim = deep_merge(base, env)
    selected = {key: val for key, val in cli.items() if val}
    return deep_merge(interim, selected)
