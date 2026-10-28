from dataclasses import replace
from io import StringIO
import json

import pytest

from driver_epic_seven.application import Application
from driver_epic_seven.cli import parser, request_from_args, execute_live
from driver_epic_seven.contracts import Identity, Request, Status, ApplicationError
from driver_epic_seven.config import load_config
from test_agent_session import FakeRuntime, session


def test_contract_is_independent_and_copies_parameters():
    source = {'roi': [1, 2, 3, 4]}
    request = Request('read-screen', source, Identity('goal', 'plan', 'op', 'attempt'))
    source['roi'][0] = 99
    assert request.parameters['roi'][0] == 1
    with pytest.raises(TypeError):
        request.parameters['roi'] = None
    assert request.identity.as_dict()['plan_id'] == 'plan'
    with pytest.raises(ValueError):
        Identity('', 'plan', 'op', 'attempt')


def test_cli_and_jsonl_use_identical_application_and_guards(tmp_path, monkeypatch):
    seen = []
    original = Application.execute
    def call(self, request, runtime=None):
        seen.append(request)
        return original(self, request, runtime)
    monkeypatch.setattr(Application, 'execute', call)
    runtime = FakeRuntime(tmp_path/'cli'); runtime.config = {}
    cli = execute_live(parser().parse_args(['read-screen']), runtime)
    other = FakeRuntime(tmp_path/'jsonl')
    messages = session(other, [{'id': 'read', 'args': ['read-screen']}])
    assert seen[0].operation == seen[1].operation == 'read-screen'
    assert dict(seen[0].parameters) == dict(seen[1].parameters)
    assert runtime.calls == other.calls
    assert cli['execution']['status'] == Status.OBSERVED
    assert messages[1]['id'] == 'read'


def test_discovery_reads_existing_sources_without_runtime():
    config = load_config()
    result = Application(config).execute(Request('capabilities'))
    assert result['routines']['orbis_roundtrip']['status'] == 'validated'
    assert result['mapped_families_are_executors'] is False
    assert result['account_access'] is None
    assert result['read_only']


def test_request_rejected_and_identity_correlated_without_dispatch(tmp_path):
    runtime = FakeRuntime(tmp_path)
    messages = session(runtime, [
        {'id': 'bad', 'args': ['observe'], 'identity': {'plan_id': ''}},
        {'id': 'good', 'args': ['observe'], 'identity': Identity('g','p','o','a').as_dict()},
    ])
    assert not messages[1]['ok'] and messages[1]['id'] == 'bad'
    assert messages[2]['ok']
    artifact = json.loads(__import__('pathlib').Path(messages[2]['evidence']['response_file']).read_text())
    assert artifact['result']['execution']['identity'] == Identity('g','p','o','a').as_dict()
    assert len(runtime.calls) == 1


def test_disconnected_request_is_blocked():
    with pytest.raises(ApplicationError) as error:
        Application({}).execute(Request('observe'))
    assert error.value.status == Status.BLOCKED
