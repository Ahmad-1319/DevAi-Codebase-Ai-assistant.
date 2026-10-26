"""Smoke tests for application imports."""

import importlib


def test_application_entry_point_imports_without_starting_a_model() -> None:
    module = importlib.import_module("app.main")

    assert callable(module.main)
    assert callable(module.cli)
