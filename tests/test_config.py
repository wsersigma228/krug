import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("secret", [None, "change-me"])
def test_config_rejects_missing_or_default_secret(secret):
    env = {key: value for key, value in os.environ.items() if key != "SECRET_KEY"}
    env["PYTHON_DOTENV_DISABLED"] = "1"
    if secret is not None:
        env["SECRET_KEY"] = secret
    result = subprocess.run([sys.executable, "-c", "import backend.config"], env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Set a non-default SECRET_KEY" in result.stderr
