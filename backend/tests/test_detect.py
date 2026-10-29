from app.db import SessionLocal
from app.engine.detect import AttemptRecord, Signals, effective_support, notice
from app.models import Decision, Item, User
from tests.test_api import client, login
from tests.test_responses import warmup


def rec(correct, words=6, session=0, mistake=None, after=None):
    return AttemptRecord(correct=correct, prompt_words=words, session=session, mistake=mistake, after_mode=after)


def modes(findings):
    return {f.mode for f in findings}


# --- Pure rules -----------------------------------------------------------------------

def test_nothing_noticed_from_too_few_answers():
    few = [rec(False, mistake="counting_slip")] * 9
    assert notice(few, Signals(read_aloud_presses=10, break_presses=10), set(), set()) == []


def test_number_slips_point_to_small_steps():
    attempts = [rec(True)] * 8 + [rec(False, mistake="counting_slip"), rec(False, mistake="tens_slip"), rec(False, mistake="added_instead")]
    found = notice(attempts, Signals(), set(), set())
    assert modes(found) == {"small_steps"}
    assert "ADHD" not in found[0].reason and "dyscalculia" not in found[0].reason.lower()


def test_pictures_helping_more_than_words_points_to_small_steps():
    attempts = [rec(True)] * 6 + [rec(True, after="count_it_out"), rec(True, after="try_similar"),
                                   rec(False, after="step_by_step"), rec(False, after="real_life")]
    assert modes(notice(attempts, Signals(), set(), set())) == {"small_steps"}


def test_long_questions_harder_points_to_easy_read():
    attempts = [rec(True, words=6)] * 5 + [rec(False, words=20)] * 4 + [rec(True, words=20)]
    assert modes(notice(attempts, Signals(), set(), set())) == {"easy_read"}


def test_slipping_late_in_sessions_points_to_focus():
    session = [True, True, True, False, False, False]
    attempts = [rec(c, session=0) for c in session] + [rec(c, session=1) for c in session]
    assert modes(notice(attempts, Signals(), set(), set())) == {"focus"}


def test_button_presses_count_but_not_speed():
    attempts = [rec(True)] * 10
    assert modes(notice(attempts, Signals(read_aloud_presses=3, break_presses=3), set(), set())) == {"easy_read", "focus"}
    assert notice(attempts, Signals(), set(), set()) == []


def test_never_re_enables_a_mode_the_student_switched_off():
    attempts = [rec(True)] * 10
    assert notice(attempts, Signals(break_presses=5), set(), {"focus"}) == []
    assert notice(attempts, Signals(break_presses=5), {"focus"}, set()) == []


def test_effective_support():
    settings = {"support_modes": ["tap_to_answer", "focus"], "auto_support": {"focus": {}, "easy_read": {}}, "auto_off": ["easy_read"]}
    assert effective_support(settings) == ["tap_to_answer", "focus"]


# --- Through the API --------------------------------------------------------------------

def test_noticed_from_answers_announced_logged_and_can_be_switched_off():
    rahul = login("rahul@demo.syniq")
    client.put("/me/settings", json={"support_modes": [], "auto_off": []}, headers=rahul)
    chapter = warmup(rahul)
    adapted = []
    for _ in range(40):
        step = client.post("/learn/next", json={"chapter_id": chapter}, headers=rahul).json()
        item = step.get("item")
        if not item:
            continue
        # One more than the right answer every time: a counting slip.
        with SessionLocal() as db:
            right = int(db.get(Item, item["id"]).answer)
        r = client.post("/learn/attempts", json={"item_id": item["id"], "response": str(right + 1)}, headers=rahul).json()
        adapted += r["response"]["adapted"]
        if adapted:
            break
    assert [a["mode"] for a in adapted] == ["small_steps"]
    assert "Settings" in adapted[0]["message"]

    me = client.get("/me", headers=rahul).json()
    assert "small_steps" in me["settings"]["auto_support"]
    with SessionLocal() as db:
        uid = db.query(User).filter_by(email="rahul@demo.syniq").one().id
        assert db.query(Decision).filter_by(student_id=uid, rule_id="A_small_steps").count() == 1

    # The parent can see what was noticed and why.
    g = login("parent@demo.syniq")
    kid = next(k for k in client.get("/guardian/children", headers=g).json() if k["name"] == "Rahul")
    assert kid["noticed"][0]["mode"] == "small_steps" and kid["noticed"][0]["on"]

    # Switched off, it stays off.
    client.put("/me/settings", json={"auto_off": ["small_steps"]}, headers=rahul)
    item = None
    while not item:
        item = client.post("/learn/next", json={"chapter_id": chapter}, headers=rahul).json().get("item")
    r = client.post("/learn/attempts", json={"item_id": item["id"], "response": "0"}, headers=rahul).json()
    assert "small_steps" not in r["response"]["support"] and r["response"]["adapted"] == []


def test_sight_hearing_speech_are_chosen_not_noticed():
    rahul = login("rahul@demo.syniq")
    assert client.put("/me/settings", json={"support_modes": ["focus"]}, headers=rahul).status_code == 400
    assert client.put("/me/settings", json={"auto_off": ["screen_reader"]}, headers=rahul).status_code == 400

    g = login("parent@demo.syniq")
    kid = next(k for k in client.get("/guardian/children", headers=g).json() if k["name"] == "Rahul")
    r = client.put(f"/guardian/children/{kid['id']}/support", json={"modes": ["screen_reader"]}, headers=g)
    assert r.status_code == 200
    assert client.get("/me", headers=rahul).json()["settings"]["support_modes"] == ["screen_reader"]
    assert client.put(f"/guardian/children/{kid['id']}/support", json={"modes": ["focus"]}, headers=g).status_code == 400
    client.put(f"/guardian/children/{kid['id']}/support", json={"modes": []}, headers=g)


def test_help_buttons_logged_only_with_consent():
    rahul = login("rahul@demo.syniq")
    assert client.post("/learn/events", json={"kind": "read_aloud"}, headers=rahul).status_code == 200
    assert client.post("/learn/events", json={"kind": "time_on_page"}, headers=rahul).status_code == 422
