import calendar
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class MonthWindow:
    key: str
    start: datetime
    end: datetime

    def fraction_elapsed(self, now: datetime) -> float:
        return min(max((now - self.start) / (self.end - self.start), 0.0), 1.0)


def month_window(now: datetime, tz: str) -> MonthWindow:
    """Budget months are calendar months in the learner's timezone, not Azure billing periods."""
    local = now.astimezone(ZoneInfo(tz))
    start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    days = calendar.monthrange(start.year, start.month)[1]
    end = (start + timedelta(days=days)).replace(day=1)
    return MonthWindow(key=f"{start:%Y-%m}", start=start, end=end)
