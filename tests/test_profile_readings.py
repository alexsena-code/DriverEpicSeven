"""One calibrated reading identity accepts either supported game process."""
import pytest

from driver_epic_seven.profile import (
    REFERENCE_CLIENT_SIZE, SUPPORTED_PROCESS_NAMES, is_supported_process, supports_reading,
)


@pytest.mark.parametrize('process', SUPPORTED_PROCESS_NAMES)
def test_shared_read_guard_accepts_both_processes_with_exact_calibrated_size(process):
    assert is_supported_process(process.swapcase())
    assert supports_reading({'window':{'process_name':process,'client_size':list(REFERENCE_CLIENT_SIZE)}})


@pytest.mark.parametrize('process', ['Other.exe','EpicSeven.exe.bak',' EpicSeven.exe',None])
def test_shared_read_guard_rejects_unrelated_or_missing_process(process):
    assert not is_supported_process(process)
    assert not supports_reading({'window':{'process_name':process,'client_size':[1212,682]}})


@pytest.mark.parametrize('size', [[1280,720],[1212,681],None])
def test_shared_read_guard_keeps_exact_size(size):
    assert not supports_reading({'window':{'process_name':'EpicSeven_Steam.exe','client_size':size}})
