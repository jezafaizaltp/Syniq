import re
import string

from tests.test_api import client, login, math_chapter_id  # first: it points the app at a test database
from tests.test_tutor_and_content import FakeClaude, ask

from app import ai, i18n
from app.db import SessionLocal
from app.engine.responses import Context, build
from app.models import User

ML = {"Accept-Language": "ml"}
MALAYALAM = re.compile(r"[ഀ-ൿ]")


def fields(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def test_every_message_has_malayalam_with_the_same_blanks():
    for key, entry in i18n.MESSAGES.items():
        assert set(entry) == {"en", "ml"}, key
        assert MALAYALAM.search(entry["ml"]), key
        assert fields(entry["en"]) == fields(entry["ml"]), key


def test_language_header():
    assert i18n.language("ml") == "ml"
    assert i18n.language("ml-IN,en;q=0.8") == "ml"
    assert i18n.language("en-IN") == "en"
    assert i18n.language(None) == "en"


def test_response_in_malayalam_keeps_the_pictures():
    r = build(Context(prompt="What is 10 + 10?", answer="20", response="15", correct=False, wrong_in_a_row=1, lang="ml"))
    assert r["headline"] == i18n.t("ml", "resp.not_yet")
    assert r["blocks"][0]["text"] == i18n.t("ml", "mistake.less", n=5)
    visual = r["blocks"][1]
    assert visual["rows"][1]["symbols"] == "⭐" * 10 + " + " + "⭐" * 10 + " = 20"
    assert visual["rows"][1]["alt"] == "10 നക്ഷത്രങ്ങൾ, കൂടെ 10 നക്ഷത്രങ്ങൾ, ആകെ 20"
    assert MALAYALAM.search(r["why"]) and MALAYALAM.search(r["script"])

    tens = build(Context(prompt="34 + 25", answer="59", response="49", correct=False, wrong_in_a_row=1, support=["screen_reader"], lang="ml"))
    assert "3 പത്തും 4 ഒന്നും" in tens["script"]


def test_api_speaks_malayalam_when_asked():
    r = client.post("/auth/login", json={"email": "anu@demo.syniq", "password": "nope"}, headers=ML)
    assert r.json()["detail"] == i18n.t("ml", "err.wrong_login")

    anu = login("anu@demo.syniq")
    r = client.post("/me/password", json={"current": "wrong", "new": "long-enough"}, headers={**anu, **ML})
    assert r.json()["detail"] == i18n.t("ml", "err.current_password")

    step = client.post("/learn/next", json={"chapter_id": math_chapter_id(anu)}, headers={**anu, **ML}).json()
    assert MALAYALAM.search(step["reason"])
    english = client.post("/learn/next", json={"chapter_id": math_chapter_id(anu)}, headers=anu).json()
    assert not MALAYALAM.search(english["reason"])


def test_language_setting_is_checked():
    anu = login("anu@demo.syniq")
    assert client.put("/me/settings", json={"ui_language": "ml"}, headers=anu).json()["ui_language"] == "ml"
    assert client.put("/me/settings", json={"ui_language": "fr"}, headers=anu).status_code == 400
    client.put("/me/settings", json={"ui_language": "en"}, headers=anu)


def test_noticed_reasons_shown_in_the_readers_language():
    reason = i18n.t("en", "noticed.focus.breaks")
    with SessionLocal() as db:
        f = db.query(User).filter_by(email="fathima@demo.syniq").one()
        before = f.settings
        f.settings = {**(f.settings or {}), "auto_support": {"focus": {"reason": reason, "since": "2026-10-29T10:00:00"}}}
        db.commit()
    try:
        fathima = login("fathima@demo.syniq")
        shown = client.get("/me", headers={**fathima, **ML}).json()["settings"]["auto_support"]["focus"]["reason"]
        assert shown == i18n.t("ml", "noticed.focus.breaks")
        assert client.get("/me", headers=fathima).json()["settings"]["auto_support"]["focus"]["reason"] == reason

        parent = login("parent@demo.syniq")
        kids = client.get("/guardian/children", headers={**parent, **ML}).json()
        noticed = next(k for k in kids if k["name"].startswith("Fathima"))["noticed"]
        assert noticed[0]["reason"] == i18n.t("ml", "noticed.focus.breaks")
    finally:
        with SessionLocal() as db:
            f = db.query(User).filter_by(email="fathima@demo.syniq").one()
            f.settings = before
            db.commit()


def test_tutor_in_malayalam():
    f = FakeClaude(text="നല്ല ചോദ്യം.")
    ai.set_client(f)
    try:
        anu = login("anu@demo.syniq")
        r = client.post("/tutor", json={"concept_id": _concept(anu), "history": [{"role": "student", "text": "2ab എവിടെ നിന്ന് വരുന്നു?"}]},
                        headers={**anu, **ML})
        assert r.json()["reply"] == "നല്ല ചോദ്യം."
        assert "simple Malayalam" in f.calls[0]["system"]

        # Distress in Malayalam gets the helpline reply in Malayalam, without calling Claude.
        r = client.post("/tutor", json={"concept_id": _concept(anu), "history": [{"role": "student", "text": "എനിക്ക് മരിക്കണം"}]},
                        headers={**anu, **ML})
        assert r.json()["reply"] == i18n.t("ml", "tutor.distress") and "14416" in r.json()["reply"]
        assert len(f.calls) == 1
        assert "14416" in ask(anu, "I want to hurt myself").json()["reply"]
    finally:
        ai.set_client(None)


def _concept(headers):
    chapter = client.get(f"/chapters/{math_chapter_id(headers)}", headers=headers).json()
    return chapter["concepts"][1]["id"]
