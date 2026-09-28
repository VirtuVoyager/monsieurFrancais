from dataclasses import dataclass
from enum import StrEnum

CHECK_PASS_MARK = 0.8


class Status(StrEnum):
    LOCKED = "locked"
    OPEN = "open"
    COVERED = "covered"
    PLACED = "placed"


DONE = (Status.COVERED, Status.PLACED)


@dataclass(frozen=True)
class ModuleFacts:
    module_id: str
    level: str
    lessons_total: int
    lessons_done: int
    check_score: float | None
    placed: bool = False

    @property
    def lessons_complete(self) -> bool:
        return self.lessons_done >= self.lessons_total


@dataclass(frozen=True)
class Coverage:
    covered: int
    total: int
    by_level: dict[str, tuple[int, int]]

    @property
    def percent(self) -> float:
        return round(100 * self.covered / self.total, 1) if self.total else 0.0


def statuses(ordered: list[ModuleFacts]) -> dict[str, Status]:
    """A module opens once the one before it is covered or placed."""
    result: dict[str, Status] = {}
    previous_done = True
    for facts in ordered:
        if facts.placed:
            status = Status.PLACED
        elif facts.lessons_complete and (facts.check_score or 0) >= CHECK_PASS_MARK:
            status = Status.COVERED
        else:
            status = Status.OPEN if previous_done else Status.LOCKED
        result[facts.module_id] = status
        previous_done = status in DONE
    return result


def coverage(ordered: list[ModuleFacts], status_by_id: dict[str, Status]) -> Coverage:
    by_level: dict[str, tuple[int, int]] = {}
    for facts in ordered:
        done, total = by_level.get(facts.level, (0, 0))
        by_level[facts.level] = (done + (status_by_id[facts.module_id] in DONE), total + 1)
    covered = sum(done for done, _ in by_level.values())
    return Coverage(covered=covered, total=len(ordered), by_level=by_level)
