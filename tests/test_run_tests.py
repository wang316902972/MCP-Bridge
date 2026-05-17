from types import SimpleNamespace

import pytest

from tests import run_tests

pytestmark = pytest.mark.unit


def test_fast_marker_is_passed_as_separate_pytest_arguments(monkeypatch):
    captured = {}

    def fake_run(cmd):
        captured["cmd"] = cmd
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(run_tests.subprocess, "run", fake_run)
    monkeypatch.setattr(run_tests.sys, "argv", ["run_tests.py", "--fast"])

    assert run_tests.main() == 0

    assert captured["cmd"][-2:] == ["-m", "not external"]
    assert "-m not external" not in captured["cmd"]
