"""Small, testable ownership boundary for asynchronous dictation results."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    context: str
    generation: int
    window: int


@dataclass
class Session:
    request_id: str
    target: Target
    state: str = 'preparing'
    consumed: bool = False

    def accepts(self, request_id: str, target: Target) -> bool:
        return (not self.consumed and self.state == 'finishing'
                and request_id == self.request_id and target == self.target)

    def consume(self, request_id: str, target: Target) -> bool:
        if not self.accepts(request_id, target):
            return False
        self.consumed = True
        return True
