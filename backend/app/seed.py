"""Demo data for local development and the first walkthrough.

All academic content here is DEMO content written to exercise the engine. It
has not been checked against the current SCERT Class 9 textbooks and must go
through teacher review before any pilot student sees it.

Run:  python -m app.seed
"""

from sqlalchemy.orm import Session as DbSession

from .auth import hash_password
from .db import Base, SessionLocal, engine
from .models import (
    Chapter,
    ClassGroup,
    Concept,
    ConceptPrereq,
    Consent,
    Explanation,
    GuardianLink,
    Item,
    Subject,
    User,
)

DEMO_PASSWORD = "syniq-demo"

SUBJECTS = [
    ("mal", "Malayalam", "ml"),
    ("eng", "English", "en"),
    ("hin", "Hindi", "hi"),
    ("math", "Mathematics", "en"),
    ("phy", "Physics", "en"),
    ("chem", "Chemistry", "en"),
    ("bio", "Biology", "en"),
    ("ss", "Social Science", "en"),
    ("it", "Information Technology", "en"),
]

# concept code -> (title, order, prerequisites)
CONCEPTS = {
    "math9.binomial_product": ("Multiplying two brackets", 0, []),
    "math9.square_of_sum": ("Square of a sum: (a + b)²", 1, ["math9.binomial_product"]),
    "math9.square_of_difference": ("Square of a difference: (a − b)²", 2, ["math9.square_of_sum"]),
    "math9.difference_of_squares": ("Difference of squares: (a + b)(a − b)", 3, ["math9.binomial_product"]),
    "math9.identities_arithmetic": ("Using identities for quick calculation", 4, ["math9.square_of_sum", "math9.square_of_difference", "math9.difference_of_squares"]),
}

EXPLANATIONS = {
    "math9.binomial_product": {
        "text": "To multiply (x + 2)(x + 3), multiply each term in the first bracket by each term in the second: x·x + x·3 + 2·x + 2·3 = x² + 5x + 6.",
        "visual": "Draw a rectangle with sides (x + 2) and (x + 3). Split it into four boxes: x by x gives x², x by 3 gives 3x, 2 by x gives 2x, and 2 by 3 gives 6. The whole area is x² + 5x + 6.",
        "step_by_step": "Step 1: first × first = x². Step 2: outer pair = 3x. Step 3: inner pair = 2x. Step 4: last × last = 6. Step 5: add like terms: x² + 5x + 6.",
        "real_world": "A garden is x metres long. You add 2 metres to one side and 3 metres to the other. Its new area, (x + 2)(x + 3), is x² + 5x + 6 square metres.",
    },
    "math9.square_of_sum": {
        "text": "(a + b)² means (a + b)(a + b). Multiplying out gives a² + ab + ab + b², so (a + b)² = a² + 2ab + b².",
        "visual": "Draw a square with side a + b. Inside it are a square of area a², a square of area b², and two rectangles of area ab each. Total: a² + 2ab + b².",
        "step_by_step": "For (x + 3)²: Step 1: square the first term, x². Step 2: twice the product, 2 × x × 3 = 6x. Step 3: square the last term, 9. Answer: x² + 6x + 9.",
        "real_world": "A square tile of side 20 cm gets a 1 cm border on every side, so its side becomes 22 cm. Its area is (20 + 2)² = 400 + 80 + 4 = 484 cm².",
    },
    "math9.square_of_difference": {
        "text": "(a − b)² = (a − b)(a − b) = a² − ab − ab + b² = a² − 2ab + b². The middle term is negative; the last term is positive.",
        "visual": "Start with a square of side a. Cut a strip of width b from two sides. You remove 2ab but have removed the small b² corner twice, so add it back: a² − 2ab + b².",
        "step_by_step": "For (y − 5)²: Step 1: y². Step 2: twice the product with its sign, 2 × y × (−5) = −10y. Step 3: (−5)² = 25. Answer: y² − 10y + 25.",
        "real_world": "To find 49², think (50 − 1)² = 2500 − 100 + 1 = 2401.",
    },
    "math9.difference_of_squares": {
        "text": "(a + b)(a − b) = a² − ab + ab − b² = a² − b². The middle terms cancel, leaving the difference of two squares.",
        "visual": "Take a square of side a and cut out a small square of side b from a corner. Rearrange the leftover L-shape into a rectangle of sides (a + b) and (a − b). Its area is a² − b².",
        "step_by_step": "For (p + 7)(p − 7): Step 1: p × p = p². Step 2: the middle terms +7p and −7p cancel. Step 3: 7 × (−7) = −49. Answer: p² − 49.",
        "real_world": "To work out 51 × 49 quickly, write it as (50 + 1)(50 − 1) = 2500 − 1 = 2499.",
    },
    "math9.identities_arithmetic": {
        "text": "Identities turn hard multiplication into easy steps. Split a number into a round number and a small part, then use the matching identity.",
        "visual": "102² is a square of side 100 + 2: a 100 × 100 block, two 100 × 2 strips and a 2 × 2 corner. 10000 + 400 + 4 = 10404.",
        "step_by_step": "For 98²: Step 1: write 98 as 100 − 2. Step 2: use (a − b)² = a² − 2ab + b². Step 3: 10000 − 400 + 4 = 9604.",
        "real_world": "A shopkeeper selling 103 boxes at ₹97 each can find 103 × 97 = (100 + 3)(100 − 3) = 10000 − 9 = ₹9991 in their head.",
    },
}

# (concept, kind, prompt, options, answer, hints, solution, difficulty, misconceptions, status)
ITEMS = [
    ("math9.binomial_product", "mcq", "Expand (x + 2)(x + 3).", ["x² + 5x + 6", "x² + 6", "x² + 6x + 5", "2x + 5"], "x² + 5x + 6",
     ["Multiply each term in the first bracket by each term in the second.", "x·x, x·3, 2·x and 2·3: add the like terms."],
     "x² + 3x + 2x + 6 = x² + 5x + 6", 1, {"x² + 6": "product_terms", "x² + 6x + 5": "arithmetic"}, "approved"),
    ("math9.binomial_product", "mcq", "Expand (x + 4)(x − 1).", ["x² + 3x − 4", "x² − 4", "x² + 5x − 4", "x² + 3x + 4"], "x² + 3x − 4",
     ["Watch the signs: 4 × (−1) is negative.", "The x terms are −x and +4x."],
     "x² − x + 4x − 4 = x² + 3x − 4", 2, {"x² − 4": "product_terms", "x² + 3x + 4": "arithmetic"}, "approved"),
    ("math9.binomial_product", "mcq", "Expand (2x + 1)(x + 3).", ["2x² + 7x + 3", "2x² + 3", "2x² + 6x + 3", "3x² + 7x + 3"], "2x² + 7x + 3",
     ["2x × x = 2x².", "The x terms are 6x and x."],
     "2x² + 6x + x + 3 = 2x² + 7x + 3", 3, {"2x² + 3": "product_terms", "2x² + 6x + 3": "arithmetic"}, "approved"),

    ("math9.square_of_sum", "mcq", "Expand (x + 3)².", ["x² + 6x + 9", "x² + 9", "x² + 3x + 9", "x² + 6x + 6"], "x² + 6x + 9",
     ["(x + 3)² = (x + 3)(x + 3).", "Use a² + 2ab + b² with a = x and b = 3."],
     "x² + 2(x)(3) + 3² = x² + 6x + 9", 1, {"x² + 9": "square_each_term", "x² + 3x + 9": "missing_double"}, "approved"),
    ("math9.square_of_sum", "mcq", "Expand (a + 5)².", ["a² + 10a + 25", "a² + 25", "a² + 5a + 25", "a² + 10a + 10"], "a² + 10a + 25",
     ["Square the first term, then twice the product, then square the last term."],
     "a² + 2(a)(5) + 25 = a² + 10a + 25", 1, {"a² + 25": "square_each_term", "a² + 5a + 25": "missing_double"}, "approved"),
    ("math9.square_of_sum", "mcq", "Expand (2m + 3)².", ["4m² + 12m + 9", "4m² + 9", "2m² + 12m + 9", "4m² + 6m + 9"], "4m² + 12m + 9",
     ["(2m)² = 4m², not 2m².", "Twice the product: 2 × 2m × 3."],
     "(2m)² + 2(2m)(3) + 3² = 4m² + 12m + 9", 2, {"4m² + 9": "square_each_term", "4m² + 6m + 9": "missing_double"}, "approved"),
    ("math9.square_of_sum", "numeric", "If a + b = 7 and ab = 10, what is a² + b²?", [], "29",
     ["Start from (a + b)² = a² + 2ab + b².", "So a² + b² = (a + b)² − 2ab."],
     "a² + b² = 7² − 2 × 10 = 49 − 20 = 29", 3, {"49": "missing_double", "39": "arithmetic"}, "approved"),

    ("math9.square_of_difference", "mcq", "Expand (y − 5)².", ["y² − 10y + 25", "y² − 25", "y² + 10y + 25", "y² − 10y − 25"], "y² − 10y + 25",
     ["Use a² − 2ab + b² with a = y and b = 5."],
     "y² − 2(y)(5) + 25 = y² − 10y + 25", 1, {"y² − 25": "square_each_term", "y² + 10y + 25": "sign_middle", "y² − 10y − 25": "sign_last"}, "approved"),
    ("math9.square_of_difference", "mcq", "Expand (3k − 2)².", ["9k² − 12k + 4", "9k² − 4", "9k² + 12k + 4", "3k² − 12k + 4"], "9k² − 12k + 4",
     ["(3k)² = 9k².", "The middle term is −2 × 3k × 2."],
     "(3k)² − 2(3k)(2) + 2² = 9k² − 12k + 4", 2, {"9k² − 4": "square_each_term", "9k² + 12k + 4": "sign_middle"}, "approved"),
    ("math9.square_of_difference", "numeric", "If a − b = 3 and ab = 4, what is a² + b²?", [], "17",
     ["(a − b)² = a² − 2ab + b².", "So a² + b² = (a − b)² + 2ab."],
     "a² + b² = 3² + 2 × 4 = 9 + 8 = 17", 3, {"1": "sign_middle", "9": "missing_double"}, "approved"),

    ("math9.difference_of_squares", "mcq", "Expand (p + 7)(p − 7).", ["p² − 49", "p² + 49", "p² − 14p − 49", "p² − 14"], "p² − 49",
     ["The middle terms +7p and −7p cancel."],
     "p² − 7p + 7p − 49 = p² − 49", 1, {"p² + 49": "sum_not_difference", "p² − 14p − 49": "extra_middle_term"}, "approved"),
    ("math9.difference_of_squares", "mcq", "Expand (2x + 5)(2x − 5).", ["4x² − 25", "4x² + 25", "2x² − 25", "4x² − 20x − 25"], "4x² − 25",
     ["Use a² − b² with a = 2x and b = 5.", "(2x)² = 4x²."],
     "(2x)² − 5² = 4x² − 25", 2, {"4x² + 25": "sum_not_difference", "4x² − 20x − 25": "extra_middle_term"}, "approved"),
    ("math9.difference_of_squares", "mcq", "Which product equals x² − 64?", ["(x + 8)(x − 8)", "(x − 8)²", "(x + 8)²", "(x − 32)(x + 2)"], "(x + 8)(x − 8)",
     ["64 is 8².", "A difference of squares comes from (a + b)(a − b)."],
     "x² − 64 = x² − 8² = (x + 8)(x − 8)", 2, {"(x − 8)²": "sign_last", "(x + 8)²": "sum_not_difference"}, "approved"),

    ("math9.identities_arithmetic", "numeric", "Use an identity to find 102².", [], "10404",
     ["Write 102 as 100 + 2.", "(100 + 2)² = 10000 + 2 × 100 × 2 + 4."],
     "(100 + 2)² = 10000 + 400 + 4 = 10404", 1, {"10004": "square_each_term", "10204": "missing_double"}, "approved"),
    ("math9.identities_arithmetic", "numeric", "Use an identity to find 98².", [], "9604",
     ["Write 98 as 100 − 2.", "(100 − 2)² = 10000 − 400 + 4."],
     "(100 − 2)² = 10000 − 400 + 4 = 9604", 2, {"9996": "square_each_term", "10404": "sign_middle", "9596": "sign_last"}, "approved"),
    ("math9.identities_arithmetic", "numeric", "Use an identity to find 51 × 49.", [], "2499",
     ["51 = 50 + 1 and 49 = 50 − 1.", "(50 + 1)(50 − 1) = 50² − 1²."],
     "50² − 1² = 2500 − 1 = 2499", 2, {"2501": "sum_not_difference"}, "approved"),
    ("math9.identities_arithmetic", "numeric", "Use an identity to find 105².", [], "11025",
     ["105 = 100 + 5."], "(100 + 5)² = 10000 + 1000 + 25 = 11025", 3, {"10025": "square_each_term"}, "draft"),
    ("math9.identities_arithmetic", "numeric", "Use an identity to find 997 × 1003.", [], "999991",
     ["997 = 1000 − 3 and 1003 = 1000 + 3."], "1000² − 3² = 1000000 − 9 = 999991", 3, {}, "draft"),
]


# A short warm-up so the no-AI response modes (stars, stories, smaller questions) can be tried.
WARMUP_EXPLANATIONS = {
    "text": "Adding puts groups together. Taking away removes some. Multiplying is adding equal groups again and again. Dividing shares equally.",
    "visual": "Picture 10 stars and 10 more stars. Count them all one by one: 20 stars.",
    "step_by_step": "Step 1: read the sign (+, −, × or ÷). Step 2: start with the first number. Step 3: add, take away, make groups or share. Step 4: check by counting back.",
    "real_world": "If you have 10 mangoes and your friend gives you 10 more, you now have 20 mangoes.",
}
WARMUP_ITEMS = [
    ("What is 10 + 10?", "20", 1), ("What is 8 + 7?", "15", 1), ("What is 15 − 6?", "9", 1),
    ("What is 6 × 4?", "24", 2), ("What is 24 ÷ 6?", "4", 2), ("What is 37 + 25?", "62", 2), ("What is 9 × 7?", "63", 3),
]


def seed(db: DbSession) -> None:
    if db.query(Subject).count():
        return

    subjects = {code: Subject(code=code, name=name, language=lang) for code, name, lang in SUBJECTS}
    db.add_all(subjects.values())
    db.flush()

    chapter = Chapter(subject_id=subjects["math"].id, number=1, title="Demo: Algebraic identities")
    db.add(chapter)
    db.flush()

    concepts = {}
    for code, (title, order, _) in CONCEPTS.items():
        concepts[code] = Concept(chapter_id=chapter.id, code=code, title=title, order=order)
    db.add_all(concepts.values())
    db.flush()
    for code, (_, _, prereqs) in CONCEPTS.items():
        for p in prereqs:
            db.add(ConceptPrereq(concept_id=concepts[code].id, prereq_id=concepts[p].id))

    for code, styles in EXPLANATIONS.items():
        for style, body in styles.items():
            db.add(Explanation(concept_id=concepts[code].id, style=style, body=body, status="approved"))

    for code, kind, prompt, options, answer, hints, solution, diff, miscon, status in ITEMS:
        db.add(
            Item(
                concept_id=concepts[code].id, kind=kind, prompt=prompt, options=options, answer=answer,
                hints=hints, solution=solution, difficulty=diff, misconceptions=miscon, status=status,
            )
        )

    warmup = Chapter(subject_id=subjects["math"].id, number=0, title="Demo: Number sense warm-up")
    db.add(warmup)
    db.flush()
    warm = Concept(chapter_id=warmup.id, code="math9.number_warmup", title="Adding, taking away, groups and sharing", order=0)
    db.add(warm)
    db.flush()
    for style, body in WARMUP_EXPLANATIONS.items():
        db.add(Explanation(concept_id=warm.id, style=style, body=body, status="approved"))
    for prompt, answer, diff in WARMUP_ITEMS:
        sum_text = prompt.removeprefix("What is ").rstrip("?")
        db.add(
            Item(
                concept_id=warm.id, kind="numeric", prompt=prompt, answer=answer, hints=["Try drawing it with dots or stars."],
                solution=f"{sum_text} = {answer}", difficulty=diff, misconceptions={}, status="approved",
            )
        )

    pw = hash_password(DEMO_PASSWORD)
    teacher = User(name="Demo Teacher", email="teacher@demo.syniq", password_hash=pw, role="teacher", settings={})
    admin = User(name="Demo Admin", email="admin@demo.syniq", password_hash=pw, role="admin", settings={})
    db.add_all([teacher, admin])
    db.flush()
    group = ClassGroup(name="Class 9 A (demo)", teacher_id=teacher.id)
    db.add(group)
    db.flush()

    students = [
        User(name="Anu", email="anu@demo.syniq", password_hash=pw, role="student", class_group_id=group.id, settings={}),
        User(name="Rahul", email="rahul@demo.syniq", password_hash=pw, role="student", class_group_id=group.id, settings={}),
        User(name="Fathima", email="fathima@demo.syniq", password_hash=pw, role="student", class_group_id=group.id, settings={}),
    ]
    guardian = User(name="Demo Parent", email="parent@demo.syniq", password_hash=pw, role="guardian", settings={})
    db.add_all(students + [guardian])
    db.flush()

    for s in students:
        db.add(GuardianLink(guardian_id=guardian.id, student_id=s.id))
    # Anu and Rahul have full consent; Fathima's guardian has not consented yet.
    for s in students[:2]:
        for scope in ("core_learning", "mood_checkins", "school_sharing"):
            db.add(Consent(student_id=s.id, guardian_id=guardian.id, scope=scope, granted=True, method="school_form"))
    db.commit()


def main() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    print("Seeded demo data. Password for all demo accounts:", DEMO_PASSWORD)


if __name__ == "__main__":
    main()
