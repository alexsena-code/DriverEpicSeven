"""Shared calibrated reading identity for the supported Epic Seven clients."""

SUPPORTED_PROCESS_NAMES = ('EpicSeven.exe', 'EpicSeven_Steam.exe')
REFERENCE_CLIENT_SIZE = (1212, 682)


def is_supported_process(name):
    return isinstance(name, str) and name.casefold() in {
        process.casefold() for process in SUPPORTED_PROCESS_NAMES
    }


def supports_reading(observation):
    window = observation.get('window', {})
    return (is_supported_process(window.get('process_name'))
            and window.get('client_size') == list(REFERENCE_CLIENT_SIZE))
