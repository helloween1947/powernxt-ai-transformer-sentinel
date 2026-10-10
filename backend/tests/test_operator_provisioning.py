"""Issuance cleans up a new token on commit failure without overwriting files."""
from contextlib import contextmanager
from unittest.mock import Mock
import sys

import pytest

from backend.app import operators


def test_failed_commit_removes_unactivated_credential(tmp_path, monkeypatch):
    credential = tmp_path / 'private-token'
    db = Mock()
    db.scalar.return_value = None
    db.commit.side_effect = RuntimeError('simulated commit failure')
    @contextmanager
    def begin():
        yield db
    monkeypatch.setattr(operators.SessionLocal, 'begin', begin)
    monkeypatch.setattr(sys, 'argv', ['operators', 'issue', '--name', 'test', '--role', 'operator', '--token-file', str(credential)])
    with pytest.raises(RuntimeError, match='simulated commit failure'):
        operators.main()
    db.flush.assert_called_once()
    db.commit.assert_called_once()
    assert not credential.exists()


def test_existing_credential_is_never_overwritten(tmp_path, monkeypatch):
    credential = tmp_path / 'private-token'
    credential.write_text('existing private content')
    db = Mock()
    db.scalar.return_value = None
    @contextmanager
    def begin():
        yield db
    monkeypatch.setattr(operators.SessionLocal, 'begin', begin)
    monkeypatch.setattr(sys, 'argv', ['operators', 'issue', '--name', 'test', '--role', 'operator', '--token-file', str(credential)])
    with pytest.raises(FileExistsError):
        operators.main()
    assert credential.read_text() == 'existing private content'
    db.commit.assert_not_called()


def test_model_handover_openapi_declares_creation_and_retry():
    from backend.app.main import create_app
    operation = create_app().openapi()['paths']['/api/v1/assets/{asset_id}/model-handovers']['post']
    assert operation['responses']['201']['content']['application/json']['schema']['$ref'].endswith('/ControlResponse')
    assert operation['responses']['200']['content']['application/json']['schema']['$ref'].endswith('/ControlResponse')
