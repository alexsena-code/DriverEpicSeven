"""Read-only extraction checks against saved CSBs, never a game connection."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('csb_inspector', ROOT / 'tools/inspect_csb_layout.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
CSB = module.CSB


def fixture(name):
    p = ROOT / 'assets/local/extraction-audit/raw' / (name + '.csb')
    if not p.exists():
        pytest.skip('Private CSB audit fixtures are not installed.')
    return p.read_bytes()


@pytest.mark.parametrize('data', [b'', b'\0' * 7, b'\0' * 8, b'\xff' * 16])
def test_invalid_binary_is_rejected(data):
    with pytest.raises(ValueError):
        CSB(data).nodes()


def test_checkbox_resources_and_composed_tint_are_preserved():
    result = CSB(fixture('chat_filter')).nodes()
    boxes = [n for n in result['nodes'] if n['class'] == 'CheckBox']
    assert len(boxes) == 8
    for n in boxes:
        options = n['declared_options']
        assert options['resources']['background']['path'] == 'img/cm_checkbg.png'
        assert options['resources']['checkmark']['path'] == 'img/cm_checkicon2.png'
        # Absent serialized state uses a schema default, never account state.
        assert not options['selected_field_present'] and options['selected']
    backdrop = next(n for n in result['nodes'] if n['name'] == 'select_all')
    assert backdrop['declared_color_argb'] == [255, 29, 66, 25]
    assert backdrop['declared_options']['scale9']['enabled']
    assert backdrop['declared_options']['resources']['image']['path'] == 'img/_btn_small_white.png'
    assert 'never runtime' in result['scope']


def test_widget_base_is_not_misread_as_nested_options():
    result = CSB(fixture('option_key')).nodes()
    widgets = [n for n in result['nodes'] if n['class'] == 'Widget']
    assert len(result['nodes']) == 11 and len(widgets) == 2
    assert {n['name'] for n in widgets} == {'n_option_alt', 'n_option_key'}
    assert all(n['class_options_supported'] for n in widgets)


def test_menu_animation_ranges_have_no_invented_wall_clock_time():
    result = CSB(fixture('quick_menu_renew')).nodes()
    assert len(result['nodes']) == 203
    assert len(result['action']['timelines']) == 14
    slide = next(a for a in result['animations'] if a['name'] == 'slide_in')
    assert slide == {'name': 'slide_in', 'start_frame': 1, 'end_frame': 11}
    assert any(t['property'] == 'Alpha' for t in result['action']['timelines'])
    assert any(t['property'] == 'VisibleForFrame' for t in result['action']['timelines'])


def test_truncated_real_layout_is_not_partially_accepted():
    raw = fixture('quick_menu_renew')
    with pytest.raises(ValueError):
        CSB(raw[:len(raw) // 2]).nodes()


def test_unparsed_classes_stay_explicit_instead_of_disappearing():
    path = ROOT / 'assets/local/full-pack/files/wnd/inbattle_order.csb'
    if not path.exists():
        pytest.skip('Private full extraction fixture is not installed.')
    result = CSB(path.read_bytes()).nodes()
    custom = next(n for n in result['nodes'] if n['class'] == 'ClippingNode')
    assert not custom['class_options_supported']
    assert custom['declared_options'] is None
    assert custom['parent_index'] is not None


def test_unresolved_frame_duration_words_do_not_become_known_times():
    path = ROOT / 'assets/local/full-pack/files/story_layouts/vva5aa_battle.csb'
    if not path.exists():
        pytest.skip('Private full extraction fixture is not installed.')
    result = CSB(path.read_bytes()).nodes()
    timeline = next(t for t in result['action']['timelines'] if t['property'] == 'FrameDuration')
    assert timeline['frame_count'] is None
    assert timeline['declared_vector_count'] == 1
    assert timeline['raw_uint32_values'] == [516]
    assert 'unresolved' in timeline['encoding']
