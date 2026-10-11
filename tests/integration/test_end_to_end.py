import os

import pytest


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="Use make smoke or RUN_INTEGRATION=1")
def test_replay_reaches_real_storage_api_and_dashboard():
    from scripts.smoke_test import run_smoke

    assert run_smoke()["status"] == "passed"
