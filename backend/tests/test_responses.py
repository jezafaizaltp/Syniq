from app.engine.responses import Context, build, diagnose, parse_arithmetic, tap_choices
from tests.test_api import client, login


def wrong(prompt, answer, response, n=1, **kw):
    return build(Context(prompt=prompt, answer=answer, response=response, correct=False, wrong_in_a_row=n, **kw))


# --- Pure engine ----------------------------------------------------------------------

def test_parses_only_sums_that_match_the_answer():
    assert parse_arithmetic("What is 10 + 10?", "20").result == 20
    assert parse_arithmetic("What is 24 ÷ 6?", "4").op == "÷"
    assert parse_arithmetic("Expand (x + 2)(x + 3).", "x² + 5x + 6") is None
    assert parse_arithmetic("If a + b = 7 and ab = 10, what is a² + b²?", "29") is None


def test_ten_plus_ten_answered_fifteen_shows_both_pictures():
    r = wrong("What is 10 + 10?", "20", "15")
    assert r["mode"] == "count_it_out"
    rows = next(b for b in r["blocks"] if b["type"] == "visual")["rows"]
    assert rows[0]["symbols"] == "⭐" * 10 + " + " + "⭐" * 5 + " = 15"
    assert rows[1]["symbols"] == "⭐" * 10 + " + " + "⭐" * 10 + " = 20"


def test_mistakes_are_named():
    s = parse_arithmetic("6 × 4", "24")
    assert diagnose(s, 10)[0] == "added_instead"
    assert diagnose(parse_arithmetic("15 − 6", "9"), 21)[0] == "added_instead"
    assert diagnose(parse_arithmetic("8 + 7", "15"), 14)[0] == "counting_slip"
    assert diagnose(parse_arithmetic("37 + 25", "62"), 52)[0] == "tens_slip"


def test_answer_modes_escalate_and_then_suggest_tutor():
    modes = [wrong("What is 10 + 10?", "20", "15", n=n, tutor_available=True) for n in (1, 2, 3, 4)]
    assert [m["mode"] for m in modes] == ["count_it_out", "step_by_step", "real_life", "try_similar"]
    assert not modes[2]["suggest_tutor"] and modes[3]["suggest_tutor"]
    challenge = next(b for b in modes[3]["blocks"] if b["type"] == "challenge")
    assert challenge == {"type": "challenge", "prompt": "What is 5 + 5?", "answer": "10"}


def test_algebra_uses_teacher_content_when_no_picture_is_possible():
    r = wrong("Expand (x + 3)².", "x² + 6x + 9", "x² + 9", solution="x² + 2(x)(3) + 3² = x² + 6x + 9",
              misconception_tip="Squaring a sum also has a middle term.")
    assert r["mode"] == "step_by_step"
    assert r["blocks"][0]["text"].startswith("Squaring a sum")
    assert r["blocks"][1]["steps"][0] == "x² + 2(x)(3) + 3²"


def test_screen_reader_gets_words_not_pictures():
    r = wrong("What is 10 + 10?", "20", "15", support=["screen_reader"])
    assert all(b["type"] != "visual" for b in r["blocks"])
    assert "10 stars plus 10 stars makes 20" in r["script"]
    assert r["speak"] and not r["show_pictures"]


def test_visual_first_never_relies_on_sound():
    r = wrong("What is 10 + 10?", "20", "15", support=["visual_first", "easy_read"])
    assert not r["speak"]
    assert any(b["type"] == "visual" for b in r["blocks"])


def test_easy_read_splits_sentences_and_focus_adds_quick_challenge():
    r = wrong("6 × 4", "24", "10", support=["easy_read", "focus"])
    assert r["blocks"][0] == {"type": "steps", "steps": ["It looks like you added instead of multiplying."], "plain": True}
    assert r["one_at_a_time"]
    assert r["blocks"][-1]["type"] == "challenge"


def test_small_steps_goes_to_a_smaller_question_sooner():
    r = wrong("What is 37 + 25?", "62", "52", n=2, support=["small_steps"])
    assert r["mode"] == "try_similar"


def test_tap_choices_include_the_answer_and_likely_mistakes():
    choices = tap_choices(parse_arithmetic("6 × 4", "24"), "24", seed=3)
    assert len(choices) == 4 and "24" in choices and "10" in choices
    assert set(tap_choices(None, "29", seed=0, likely_wrong=["49", "39"])) == {"29", "30", "39", "49"}


# --- Through the API --------------------------------------------------------------------

def warmup(headers):
    subjects = client.get("/subjects", headers=headers).json()
    math = next(s for s in subjects if s["code"] == "math")
    chapters = client.get(f"/subjects/{math['id']}/chapters", headers=headers).json()
    return next(c["id"] for c in chapters if c["title"].startswith("Demo: Number sense"))


def test_support_modes_validated():
    rahul = login("rahul@demo.syniq")
    assert client.put("/me/settings", json={"support_modes": ["mind_reading"]}, headers=rahul).status_code == 400
    assert client.put("/me/settings", json={"support_modes": [{"x": 1}]}, headers=rahul).status_code == 400


def test_wrong_answer_gets_a_logged_adaptive_response_and_tap_choices():
    rahul = login("rahul@demo.syniq")
    client.put("/me/settings", json={"support_modes": ["tap_to_answer"]}, headers=rahul)
    chapter = warmup(rahul)
    step = None
    for _ in range(6):  # skip past the opening explanation
        step = client.post("/learn/next", json={"chapter_id": chapter}, headers=rahul).json()
        if step.get("item"):
            break
    item = step["item"]
    assert len(item["choices"]) == 4

    r = client.post("/learn/attempts", json={"item_id": item["id"], "response": "999"}, headers=rahul).json()
    assert r["correct"] is False
    assert r["response"]["mode"] in ("count_it_out", "step_by_step")
    assert r["response"]["blocks"]
    client.put("/me/settings", json={"support_modes": []}, headers=rahul)
