from __future__ import annotations

import json
from pathlib import Path

import pytest

from gitbook_translator.worker.models import (
    ClaimResponse,
    CompleteRequest,
    RegisterRequest,
    UpdatesRequest,
)


CONTRACT_DIR = Path(__file__).parents[2] / "contracts" / "worker-api-v1"

CONTRACT_MODELS = {
    "register": RegisterRequest,
    "claim": ClaimResponse,
    "updates": UpdatesRequest,
    "complete": CompleteRequest,
}


@pytest.mark.parametrize("name", ["register", "claim", "updates", "complete"])
def test_contract_fixture_parses_with_python_models(name):
    payload = json.loads((CONTRACT_DIR / f"{name}.json").read_text())

    CONTRACT_MODELS[name].model_validate(payload)
