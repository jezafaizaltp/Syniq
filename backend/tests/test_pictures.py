import copy

from tests.test_api import client, login  # first: it points the app at a test database

from app import content_packs
from app.db import SessionLocal
from app.models import Concept, Explanation
from app.pictures import check_picture

GOOD = {
    "number_line": {"kind": "number_line", "from": 0, "to": 4, "points": [{"at": 1.5, "label": "3/2"}], "alt": "A number line from 0 to 4 with 3/2 marked."},
    "area_grid": {"kind": "area_grid", "cols": [{"size": 3, "label": "a"}, {"size": 1, "label": "b"}], "rows": [{"size": 3, "label": "a"}],
                  "cells": [["a²", "ab"]], "alt": "A rectangle split into a² and ab."},
    "bars": {"kind": "bars", "bars": [{"label": "A", "value": 3}, {"label": "B", "value": 0}], "alt": "Two bars, 3 and 0 tall."},
    "flow": {"kind": "flow", "steps": ["Heat", "Melt"], "alt": "Heating leads to melting."},
    "compare": {"kind": "compare", "columns": [{"title": "Solid", "points": ["fixed shape"]}, {"title": "Gas", "points": ["no shape"]}],
                "alt": "Solids have a fixed shape; gases don't."},
    "geometry": {"kind": "geometry", "points": {"A": [1, 1], "B": [5, 1], "_h": [9, 9]}, "segments": [["A", "B", "4 cm"]],
                 "angles": [{"at": "A", "from": "B", "to": "_h"}], "alt": "A segment AB of 4 cm."},
}


def broken(kind, **changes):
    return check_picture({**copy.deepcopy(GOOD[kind]), **changes})


def test_good_pictures_of_every_kind_pass():
    for kind, picture in GOOD.items():
        assert check_picture(picture) == [], kind


def test_checker_catches_pictures_that_cannot_be_drawn():
    assert "not one of" in check_picture({"kind": "photo", "alt": "something to look at"})[0]
    assert "'alt' sentence" in broken("flow", alt="")[0]
    assert "between 0 and 4" in broken("number_line", points=[{"at": 9, "label": "far"}])[0]
    assert "at most 40 ticks" in broken("number_line", to=100, step=1)[0]
    assert "1 rows of 2" in broken("area_grid", cells=[["a²"]])[0]
    assert "all be 0" in broken("bars", bars=[{"label": "A", "value": 0}, {"label": "B", "value": 0}])[0]
    assert "2 to 8 steps" in broken("flow", steps=["only one"])[0]
    assert "too long" in broken("compare", columns=[{"title": "x" * 41, "points": ["p"]}, {"title": "y", "points": ["q"]}])[0]
    assert "isn't in 'points'" in broken("geometry", segments=[["A", "Z"]])[0]
    assert "between 0 and 10" in broken("geometry", points={"A": [1, 1], "B": [11, 1]})[0]
    assert "only works with axes" in broken("geometry", x_label="t")[0]
    assert "around 0" in broken("geometry", axes=True, range=[1, 5])[0]
    assert all(e.startswith("picture: ") for e in broken("flow", steps=[]))


def test_picture_is_stored_on_the_visual_explanation_and_sent_to_students():
    with SessionLocal() as db:
        concept = db.query(Concept).filter(Concept.code == "math9.ident.square_of_sum").one()
        rows = {e.style: e for e in db.query(Explanation).filter(Explanation.concept_id == concept.id, Explanation.source == "pack")}
        assert rows["visual"].picture["kind"] == "area_grid"
        assert all(e.picture is None for s, e in rows.items() if s != "visual")
        concept_id = concept.id

    anu = login("anu@demo.syniq")
    visual = client.get(f"/concepts/{concept_id}/explanations/visual", headers=anu).json()
    assert visual["picture"]["cells"] == [["a²", "ab"], ["ab", "b²"]]
    assert len(visual["picture"]["alt"]) >= 15
    text = client.get(f"/concepts/{concept_id}/explanations/text", headers=anu).json()
    assert text["picture"] is None
