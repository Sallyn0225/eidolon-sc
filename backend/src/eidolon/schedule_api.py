"""Schedules over HTTP (GLOSSARY.md「日程」), for users who agreed to the terms: the user's
week and the next once published at `/api/schedule`, the week's jobs drawn as first read;
saving jobs into a week at `/api/schedule/weeks/{week}`, the week named by its Monday's date;
the user's weeks gone, to look at, at `/api/schedule/weeks?from=YYYY-MM-DD&to=YYYY-MM-DD`, as
many as `PAST_AT_ONCE` at a time. All in the producer's time zone, their profile's, else
their device's (`X-Timezone`). What is saved cannot be changed or taken back: there is no
route to. While schedules are off, reading their week says so, and reading weeks gone and
saving are refused with 409 and `schedule_closed`."""

from datetime import date

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from eidolon.assembly import Backend
from eidolon.job_list import SLOTS
from eidolon.schedule import DAYS, Placement, ScheduleClosed, TooManyWeeks
from eidolon.sessions import DeviceTimezone, UserId


class PlacementInput(BaseModel):
    job_id: str
    day: int = Field(ge=0, lt=DAYS)
    """0 for Monday."""
    slot: int = Field(ge=0, lt=len(SLOTS))
    """The slot the job starts in, 0 for the morning."""


class SaveInput(BaseModel):
    placements: list[PlacementInput]
    """Those new in this saving, in the order to save them."""


def add_schedule_routes(app: FastAPI, backend: Backend) -> None:
    schedules = backend.schedules

    @app.exception_handler(ScheduleClosed)
    async def schedule_closed(_: Request, e: ScheduleClosed) -> JSONResponse:
        return JSONResponse({"detail": str(e), "schedule_closed": True}, status_code=409)

    @app.get("/api/schedule")
    async def read(user_id: UserId, device_timezone: DeviceTimezone = None) -> dict:
        """The user's week and the next once published, each with its jobs and what the user
        saved of it; or only that schedules are off."""
        view = await schedules.read(user_id, device_timezone)
        return view.shown() if view is not None else {"enabled": False}

    @app.get("/api/schedule/weeks")
    async def past(
        user_id: UserId,
        device_timezone: DeviceTimezone = None,
        first: date = Query(alias="from"),
        last: date = Query(alias="to"),
    ) -> dict:
        """The user's weeks gone from the one `from` is in to the one `to` is in, each with
        what they saved of it and the jobs of it they saved; at most `PAST_AT_ONCE`."""
        try:
            weeks = await schedules.past(user_id, first, last, device_timezone)
        except TooManyWeeks as e:
            raise HTTPException(400, str(e)) from None
        if weeks is None:
            raise ScheduleClosed()
        return {"weeks": [w.shown() for w in weeks]}

    @app.post("/api/schedule/weeks/{week}")
    async def save(
        week: str, body: SaveInput, user_id: UserId, device_timezone: DeviceTimezone = None
    ) -> dict:
        """Save what can be of the placements into the week: those saved, and those handed
        back, each with why."""
        try:
            monday = date.fromisoformat(week)
        except ValueError:
            raise HTTPException(404, "没有这一周") from None
        if monday.weekday() != 0 or monday.isoformat() != week:
            raise HTTPException(404, "没有这一周")
        placements = [Placement(p.job_id, p.day, p.slot) for p in body.placements]
        return (await schedules.save(user_id, monday, placements, device_timezone)).shown()
