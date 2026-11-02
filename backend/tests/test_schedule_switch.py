"""The deployment's switch for schedules (GLOSSARY.md「日程」): `EIDOLON_SCHEDULE` in `.env`, on
unless set to 0, anything but 0 or 1 refused as the backend starts; the admin console's
「日程」card overrides it. Off, reading says only that, weeks gone are refused and nothing can
be saved; what was saved is kept, there again once it is back on."""

from dataclasses import replace

import pytest

from eidolon.config import Settings
from tests.conftest import ClientFactory
from tests.fakes import FakeClock, FakeIdentityProvider, FakeLLM
from tests.test_admin_users import ADMIN, admin_beside
from tests.test_schedule_saving import WEDNESDAY_AFTERNOON, WEEK, placed, publish, save
from tests.test_schedule_weeks import schedule

SCHEDULE = "/api/admin/config/schedule"


def test_unset_in_env_it_is_on(monkeypatch: pytest.MonkeyPatch):
    # 0, 1 and anything else are every switch's (`config._switch`), as test_exempting_keys has.
    monkeypatch.setenv("CHAT_LLM_BASE_URL", "https://llm.example.com/v1")
    monkeypatch.setenv("CHAT_LLM_API_KEY", "sk-deployer")
    monkeypatch.setenv("CHAT_LLM_MODEL", "deployer-model")
    monkeypatch.delenv("EIDOLON_SCHEDULE", raising=False)

    assert Settings.from_env().schedule is True


async def test_off_nothing_is_read_or_saved_and_the_admin_turning_it_on_brings_it_back(
    make_client: ClientFactory, settings: Settings, github: FakeIdentityProvider
):
    on = replace(settings, admins=frozenset({ADMIN}))
    client = make_client(FakeLLM(), settings=on, clock=FakeClock(WEDNESDAY_AFTERNOON))
    publish(settings.database_path, WEEK, ("lesson", 1, None), ("talk", 1, None))
    await save(client, WEEK, placed("lesson", 4, 0))

    async with admin_beside(client, github) as admin:
        described = (await admin.get("/api/admin/config")).json()["schedule"]
        turned_off = await admin.put(SCHEDULE, json={"enabled": False})
        read_off = await client.get("/api/schedule")
        saving_off = await save(client, WEEK, placed("talk", 5, 0))
        past_off = await client.get("/api/schedule/weeks", params={"from": WEEK, "to": WEEK})
        refused = await admin.put(SCHEDULE, json={"enabled": "no"})
        await admin.delete(SCHEDULE)
        read_on = await schedule(client)

    assert described == {
        "status": "env", "env": {"enabled": True}, "effective": {"enabled": True},
        "override": None, "failure": None,
    }
    assert turned_off.json()["schedule"]["override"] == {"enabled": False}
    assert read_off.json() == {"enabled": False}
    assert saving_off.status_code == 409
    assert saving_off.json() == {"detail": "日程暂时没有开放", "schedule_closed": True}
    assert (past_off.status_code, past_off.json()) == (409, saving_off.json())
    assert refused.status_code == 422
    assert read_on["this_week"]["placements"] == [placed("lesson", 4, 0)]
