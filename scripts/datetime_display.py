"""Shared display datetime formatters (Asia/Ho_Chi_Minh). Storage stays ISO."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

VN_TZ = timezone(timedelta(hours=7))

DATE_FMT = "%d-%m-%Y"
DATETIME_FMT = "%H:%M:%S %d-%m-%Y"


def format_display_date(dt: datetime) -> str:
    return dt.astimezone(VN_TZ).strftime(DATE_FMT)


def format_display_datetime(dt: datetime) -> str:
    return dt.astimezone(VN_TZ).strftime(DATETIME_FMT)


def now_display_datetime() -> str:
    return format_display_datetime(datetime.now(VN_TZ))