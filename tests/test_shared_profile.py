from types import SimpleNamespace

import pytest

from driver_epic_seven.config import ROOT,load_config
from driver_epic_seven.windows import Windows


@pytest.mark.parametrize('process',['EpicSeven.exe','EpicSeven_Steam.exe'])
def test_same_configuration_discovers_either_supported_executable(monkeypatch,process):
    from maa.toolkit import Toolkit
    window=SimpleNamespace(window_name='Epic Seven',class_name='GLFW30',hwnd=11)
    monkeypatch.setattr(Toolkit,'find_desktop_windows',lambda:[window])
    api=Windows.__new__(Windows)
    api.inspect=lambda hwnd:{'hwnd':hwnd,'process_name':process}
    config=load_config()
    assert api.discover(config['target'])['process_name']==process
    assert config['resource_dir']==ROOT/'resources/epic-seven'
    assert config['vision_file']==config['resource_dir']/'vision.json'


def test_unrelated_process_does_not_become_a_supported_window(monkeypatch):
    from maa.toolkit import Toolkit
    monkeypatch.setattr(Toolkit,'find_desktop_windows',lambda:[SimpleNamespace(window_name='Epic Seven',class_name='GLFW30',hwnd=11)])
    api=Windows.__new__(Windows);api.inspect=lambda hwnd:{'hwnd':hwnd,'process_name':'Other.exe'}
    with pytest.raises(RuntimeError):api.discover(load_config()['target'])
