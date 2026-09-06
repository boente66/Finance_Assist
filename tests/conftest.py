"""Blindagem global para a suíte nunca abrir o banco do usuário."""

import os
import tempfile


_TEST_DATA = tempfile.TemporaryDirectory(prefix="finance-assist-pytest-")
os.environ["FINANCE_ASSIST_ENV"] = "test"
os.environ["FINANCE_ASSIST_DATA_DIR"] = _TEST_DATA.name
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def pytest_sessionfinish(session, exitstatus):
    _TEST_DATA.cleanup()
