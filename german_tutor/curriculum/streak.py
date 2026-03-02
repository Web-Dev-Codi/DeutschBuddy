from __future__ import annotations

from datetime import date, datetime


def calculate_streak(last_session_date: datetime | None, current_streak: int) -> int:
    today = date.today()
    if last_session_date is None:
        return 1
    last_date = last_session_date.date()
    delta = (today - last_date).days
    if delta == 0:
        return current_streak  # already studied today
    elif delta == 1:
        return current_streak + 1  # consecutive day
    else:
        return 1  # streak broken, restart
