from types import SimpleNamespace

import pytest

from driver_epic_seven.prequel import finish_graph
from driver_epic_seven.runtime import Runtime


@pytest.mark.parametrize('identity', ['ijp001', 'ijp007', 'ijp008'])
@pytest.mark.parametrize('victory', [False, True])
def test_resume_graph_is_closed_and_cannot_start(identity, victory):
    graph = finish_graph(identity, victory)
    assert graph['Path.Campaign.Entry']['timeout'] == 600000
    assert all(edge in graph for node in graph.values() for edge in node.get('next', []))
    assert not any(name.endswith('.Start') for name in graph)


def test_rejected_job_fails_before_polling_native_status():
    class RejectedJob:
        job_id = 0

        @property
        def done(self):
            raise AssertionError('invalid jobs must never be polled')

    runtime = SimpleNamespace(evidence=SimpleNamespace(path='evidence'))
    with pytest.raises(RuntimeError, match='job_id inválido'):
        Runtime.wait(runtime, RejectedJob(), task=True)
