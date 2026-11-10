import re
import string

from tests.test_api import client, login  # first: it points the app at a test database

from app import ai, i18n
from app.engine.responses import Context, build

HI = {"Accept-Language": "hi"}
HINDI = re.compile(r"[ऀ-ॿ]")


def fields(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def test_every_message_has_hindi_with_the_same_blanks():
    for key, entry in i18n.MESSAGES.items():
        assert HINDI.search(entry["hi"]), key
        assert fields(entry["en"]) == fields(entry["hi"]), key


def test_language_header_picks_hindi():
    assert i18n.language("hi") == "hi"
    assert i18n.language("hi-IN,en;q=0.8") == "hi"
    assert i18n.language("en-IN,hi;q=0.5") == "en"


def test_response_in_hindi_keeps_the_pictures():
    r = build(Context(prompt="What is 10 + 10?", answer="20", response="15", correct=False, wrong_in_a_row=1, lang="hi"))
    assert r["headline"] == i18n.t("hi", "resp.not_yet")
    assert r["blocks"][0]["text"] == i18n.t("hi", "mistake.less", n=5)
    assert HINDI.search(r["why"]) and HINDI.search(r["script"])
    tens = build(Context(prompt="34 + 25", answer="59", response="49", correct=False, wrong_in_a_row=1, support=["screen_reader"], lang="hi"))
    assert "3 दहाई और 4 इकाई" in tens["script"]


def test_api_speaks_hindi_when_asked():
    r = client.post("/auth/login", json={"email": "anu@demo.syniq", "password": "nope"}, headers=HI)
    assert r.json()["detail"] == i18n.t("hi", "err.wrong_login")
    anu = login("anu@demo.syniq")
    assert client.put("/me/settings", json={"ui_language": "hi"}, headers=anu).status_code == 200
    assert client.put("/me/settings", json={"ui_language": "fr"}, headers=anu).status_code == 400
    client.put("/me/settings", json={"ui_language": "en"}, headers=anu)


def test_ai_tutor_is_told_to_reply_in_hindi():
    assert "Hindi" in ai.LANGUAGE_LINE["hi"] and "Devanagari" in ai.LANGUAGE_LINE["hi"]
