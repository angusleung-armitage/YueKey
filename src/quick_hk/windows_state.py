"""Platform-independent Windows gesture and result guards. SPDX-License-Identifier: MIT."""
from dataclasses import dataclass


class DoubleControl:
    def __init__(self, key: int = 0xA2):
        self.key = key
        self.down_at = None
        self.up_at = None
        self.repeated = False

    def reset(self):
        self.down_at = self.up_at = None
        self.repeated = False

    def feed(self, key: int, down: bool, timestamp: float) -> bool:
        if key != self.key:
            self.reset()
            return False
        if down:
            if self.down_at is not None:  # autorepeat / held Ctrl
                self.repeated = True
            else:
                self.down_at = timestamp
            return False
        if self.repeated or self.down_at is None or not 0 <= timestamp - self.down_at <= 0.25:
            self.reset()
            return False
        self.down_at = None
        if self.up_at is not None and 0 <= timestamp - self.up_at <= 0.4:
            self.reset()
            return True
        self.up_at = timestamp
        return False


@dataclass(frozen=True)
class Target:
    window: int
    process: int
    runtime_id: tuple[int, ...]
    activity: int


@dataclass
class Request:
    identifier: str
    target: Target
    state: str = 'recording'
    consumed: bool = False

    def consume(self, identifier: str, target: Target | None) -> bool:
        if self.consumed or self.state != 'finishing' or identifier != self.identifier or target != self.target:
            return False
        self.consumed = True
        return True


def editable(*, control_type, password, focused, enabled) -> bool:
    # Unknown properties fail closed; Edit and Document are the only supported types.
    return (control_type in (50004, 50030) and password is False
            and focused is True and enabled is True)
