"""Regression tests for the destructive GraphDB fixture boundary."""

import pytest

from oldap_api.test.conftest import resolve_test_repository


def test_test_repository_defaults_to_dedicated_name():
    assert resolve_test_repository(None) == "oldap-test"


@pytest.mark.parametrize("repository", ["oldap", " OLDAP "])
def test_live_local_repository_is_rejected(repository):
    with pytest.raises(pytest.UsageError, match="Refusing to run destructive"):
        resolve_test_repository(repository)


def test_explicit_disposable_repository_is_accepted():
    assert resolve_test_repository("oldap-api-ci") == "oldap-api-ci"
