"""Stable microphone choices across PortAudio device reordering. SPDX-License-Identifier: MIT."""
import json


def microphones(sd=None) -> list[tuple[str, str]]:
    if sd is None:
        import sounddevice as sd
    hosts = sd.query_hostapis()
    result = [('default', '系統預設 · System default')]
    for device in sd.query_devices():
        if device['max_input_channels'] > 0:
            host, name = hosts[device['hostapi']]['name'], device['name']
            value = json.dumps([host, name], ensure_ascii=False)
            if not any(item[0] == value for item in result):
                result.append((value, f'{name} · {host}'))
    return result


def resolve_microphone(value: str, sd):
    if value == 'default':
        return None
    if value.isdecimal():  # Existing manually configured numeric IDs.
        return int(value)
    try:
        host, name = json.loads(value)
    except (ValueError, TypeError) as error:
        raise ValueError('Choose a microphone again in YueKey settings.') from error
    hosts = sd.query_hostapis()
    matches = [index for index, device in enumerate(sd.query_devices())
               if device['max_input_channels'] > 0 and device['name'] == name
               and hosts[device['hostapi']]['name'] == host]
    if len(matches) != 1:
        raise ValueError('The selected microphone is missing or ambiguous. Choose it again in YueKey settings.')
    return matches[0]


def input_parameters(value: str, sd) -> dict:
    device = resolve_microphone(value, sd)
    info = sd.query_devices(device, 'input')
    host = sd.query_hostapis()[info['hostapi']]['name']
    parameters = {'device': device}
    if host == 'Windows WASAPI':
        # Shared-mode devices commonly use 44.1/48 kHz. Let Windows convert
        # channels and sample rate to the recognizer's mono 16 kHz PCM stream.
        parameters['extra_settings'] = sd.WasapiSettings(auto_convert=True)
    return parameters
