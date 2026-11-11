"""Login credentials for the API.

Kept in config/auth_config.yaml (not committed). If it doesn't exist, one is created
with a default account so a fresh checkout can be tried; change that password before
anyone else uses it.
"""

import os
from pathlib import Path

import yaml

# ABA_AUTH_CONFIG points a test or demo at a different file
AUTH_CONFIG_PATH = Path(os.environ.get("ABA_AUTH_CONFIG") or Path(__file__).parent / "config" / "auth_config.yaml")


def load_auth_config() -> dict:
    if AUTH_CONFIG_PATH.exists():
        with open(AUTH_CONFIG_PATH) as f:
            return yaml.safe_load(f)

    import bcrypt

    config = {
        "credentials": {
            "usernames": {
                "bcba_reviewer": {
                    "name": "BCBA Reviewer",
                    "password": bcrypt.hashpw("changeme".encode(), bcrypt.gensalt()).decode(),
                }
            }
        },
        "cookie": {
            "name": "aba_auth_agent",
            "key": "aba_auth_agent_signature_key",
            "expiry_days": 7,
        },
    }
    AUTH_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUTH_CONFIG_PATH, "w") as f:
        yaml.dump(config, f)
    return config
