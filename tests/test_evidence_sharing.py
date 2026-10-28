from unittest.mock import Mock

import pytest

from driver_epic_seven.evidence import replace_evidence


def test_transient_reader_lock_retries_only_rename(monkeypatch):
    monkeypatch.setattr('driver_epic_seven.evidence.time.sleep', lambda _: None)
    temporary = Mock()
    temporary.replace.side_effect = [PermissionError('reader'), None]
    replace_evidence(temporary, 'target')
    assert temporary.replace.call_count == 2


def test_persistent_permission_error_remains_visible_and_bounded(monkeypatch):
    monkeypatch.setattr('driver_epic_seven.evidence.time.sleep', lambda _: None)
    temporary = Mock()
    temporary.replace.side_effect = PermissionError('denied')
    with pytest.raises(PermissionError):
        replace_evidence(temporary, 'target')
    assert temporary.replace.call_count == 11
