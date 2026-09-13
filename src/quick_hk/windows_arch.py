"""Package architecture follows the running interpreter, including emulation."""
import struct
import sysconfig


def package_architecture() -> str:
    platform = sysconfig.get_platform().lower().replace('_', '-')
    if platform == 'win-arm64':
        return 'arm64'
    if platform == 'win-amd64':
        return 'x64'
    if platform == 'win32' and struct.calcsize('P') == 4:
        return 'x86'
    raise RuntimeError(f'Expected a Windows x86, x64 or ARM64 Python interpreter, got {platform}')
