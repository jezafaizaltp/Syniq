"""tools/fit_mastery.py finds the settings that predict answers best."""

import random

import tests.test_api  # noqa: F401  first: points the app at a fresh test database

from tools import fit_mastery as fm


def simulate(p: fm.Params, students=300, answers=12, seed=7):
    rng = random.Random(seed)
    seqs = []
    for _ in range(students):
        knows = rng.random() < p.p_init
        seq = []
        for _ in range(answers):
            right = rng.random() < (1 - p.slip if knows else p.guess_mcq)
            seq.append(fm.Answer(right, "mcq", 0))
            knows = knows or rng.random() < p.p_transit
        seqs.append(seq)
    return seqs


def test_true_settings_score_better_than_wrong_ones():
    true = fm.Params(0.3, 0.12, 0.1, 0.25, 0.05)
    seqs = simulate(true)
    wrong = fm.Params(0.1, 0.04, 0.2, 0.35, 0.05)
    assert fm.score(seqs, true) > fm.score(seqs, wrong)
    best, _ = fm.fit(seqs)
    assert abs(best.p_transit - true.p_transit) <= 0.04 and abs(best.slip - true.slip) <= 0.05


def test_no_answers_says_so(capsys, monkeypatch):
    monkeypatch.setattr(fm, "load", lambda subject: [])
    assert fm.main([]) == 1
    assert "No answers yet" in capsys.readouterr().out
