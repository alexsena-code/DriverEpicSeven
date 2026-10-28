from types import SimpleNamespace

import pytest

from driver_epic_seven.cli import parser
from driver_epic_seven.runtime import Runtime


def test_navigation_keeps_short_default_and_explicit_calibration_duration():
    assert parser().parse_args(['key', 'escape']).duration_ms == 100
    args = parser().parse_args(['key', 'escape', '--duration-ms', '5000', '--observation', 'current.json'])
    assert args.duration_ms == 5000


@pytest.mark.parametrize('key,duration,observation', [
    ('escape', 5000, None), ('hero', 5000, 'current.json'),
    ('escape', 5001, 'current.json'), ('escape', 0, 'current.json'),
])
def test_long_key_rejects_blind_or_out_of_scope_gestures_before_observation(key, duration, observation):
    with pytest.raises(ValueError, match='Tecla longa exige'):
        Runtime.primitive(SimpleNamespace(), 'key', key=key, key_duration_ms=duration, observation=observation)
