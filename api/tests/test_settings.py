from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.domain.planning import exam_plan

TODAY = date(2026, 9, 28)


def test_plan_sets_booking_and_retake_dates() -> None:
    plan = exam_plan(date(2027, 2, 1), TODAY)

    assert plan.book_by == date(2026, 12, 7)
    assert plan.earliest_retake == date(2027, 3, 3)
    assert (plan.final_phase, plan.mock_every_days, plan.booking_overdue) == (False, 30, False)


def test_final_four_weeks_switch_to_weekly_mocks_and_flag_late_booking() -> None:
    plan = exam_plan(TODAY + timedelta(days=20), TODAY)

    assert (plan.final_phase, plan.mock_every_days, plan.booking_overdue) == (True, 7, True)


def test_settings_default_then_update_with_plan(client: TestClient) -> None:
    assert client.get("/settings").json()["plan"] is None

    exam = (date.today() + timedelta(days=120)).isoformat()
    body = client.put(
        "/settings",
        json={"exam_date": exam, "target_nclc": 7, "daily_minutes": 120, "accent_mix": "quebec"},
    ).json()

    assert body["settings"]["accent_mix"] == "quebec"
    assert body["plan"]["days_left"] == 120
    assert client.get("/settings").json() == body


def test_unknown_timezone_is_rejected(client: TestClient) -> None:
    assert client.put("/settings", json={"timezone": "Mars/Olympus"}).status_code == 422
