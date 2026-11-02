"""The baby section (birth to 2 years), written for the mother and family, not for the baby's screen.

Every piece comes from a published source, named in SOURCES and shown in the app. It is
information, not medical advice: each page tells parents when to see a doctor, and SYNiq never
suggests a diagnosis. Milestones follow the CDC's 2022 checklists (things most children, 3 in 4,
do by that age), so a missing one means "mention it to your doctor", never "something is wrong".
"""

SOURCES = {
    "cdc": {"name": "CDC, Learn the Signs. Act Early. (milestone checklists, 2022)", "url": "https://www.cdc.gov/ncbddd/actearly/milestones/index.html"},
    "uip": {"name": "Ministry of Health and Family Welfare, National Immunization Schedule (India)", "url": "https://nhm.gov.in/index1.php?lang=1&level=2&sublinkid=824&lid=220"},
    "who_feeding": {"name": "WHO, Infant and young child feeding", "url": "https://www.who.int/news-room/fact-sheets/detail/infant-and-young-child-feeding"},
    "iap_screen": {"name": "Indian Academy of Pediatrics, Screen time guidelines (2021)", "url": "https://imsear.searo.who.int/items/83e152e9-46a9-44a1-b8e7-8d3fe2e8cb22"},
    "aap_sleep": {"name": "American Academy of Pediatrics, Safe sleep", "url": "https://www.healthychildren.org/English/ages-stages/baby/sleep/Pages/a-parents-guide-to-safe-sleep.aspx"},
    "imnci": {"name": "WHO and Government of India, IMNCI danger signs in young infants", "url": "https://nhm.gov.in/images/pdf/programmes/child-health/guidelines/imnci_chart_booklet.pdf"},
    "nhs": {"name": "NHS, Baby care and your health after birth", "url": "https://www.nhs.uk/baby/"},
    "telemanas": {"name": "Tele-MANAS, national mental health helpline (14416)", "url": "https://telemanas.mohfw.gov.in/"},
}

DISCLAIMER = (
    "Information from WHO, India's Ministry of Health, the Indian Academy of Pediatrics, the CDC and the NHS, not medical advice. "
    "Every baby grows at their own pace. If you're worried, talk to your doctor or health worker."
)

# Go to a doctor or hospital now. Call 108 for an ambulance.
SEE_DOCTOR_NOW = [
    "Not feeding well, or can't feed at all",
    "A fit (convulsion), or very floppy or hard to wake",
    "Fast breathing, or the chest pulls in with each breath",
    "Fever, or feels cold to touch (in a baby under 2 months, any fever)",
    "Yellow palms or soles, or yellow skin in the first day of life",
    "Redness or pus spreading around the belly button",
    "Vomiting everything, very few wet nappies, or blood in the poo",
    "Losing skills they used to have, at any age",
]

# Play you do together, by age in months. Nothing here needs a screen.
PLAY = [
    {"from": 0, "to": 3, "title": "0 to 3 months", "ideas": [
        "Talk and sing to your baby during feeds and nappy changes. Your voice is their favourite sound.",
        "Hold your face about 30 cm from theirs and smile. Wait for them to look back.",
        "Tummy time for a few minutes, several times a day, while they're awake and you're watching.",
        "When they coo, coo back and pause, like a little conversation.",
    ]},
    {"from": 3, "to": 6, "title": "3 to 6 months", "ideas": [
        "Hold a rattle or a bright cloth just within reach so they reach and grab.",
        "Look in a mirror together and name what you see: 'there's your nose'.",
        "Read a picture book with big, simple pictures and point to each one.",
        "Name body parts at bath time: 'washing your hands, washing your feet'.",
    ]},
    {"from": 6, "to": 9, "title": "6 to 9 months", "ideas": [
        "Play peek-a-boo with a cloth. It teaches that things still exist when hidden.",
        "Give two steel bowls or spoons to bang together.",
        "Sit facing each other and roll a ball back and forth.",
        "Name each food at meal time: 'this is dal, this is banana'.",
    ]},
    {"from": 9, "to": 12, "title": "9 to 12 months", "ideas": [
        "Put a few safe things in a box and let them take them out and put them back.",
        "Wave bye-bye and clap together. Sing songs with actions.",
        "Stack cups or blocks and let them knock them down.",
        "Hide a toy under a cloth while they watch, then let them find it.",
    ]},
    {"from": 12, "to": 18, "title": "12 to 18 months", "ideas": [
        "Point to things on a walk and name them: bird, auto, tree.",
        "Give a push toy, or a box to push around the floor.",
        "Let them scribble with a fat crayon on old paper.",
        "Let them help: putting clothes in a basket, wiping the table.",
    ]},
    {"from": 18, "to": 24, "title": "18 to 24 months", "ideas": [
        "Add a word to what they say: if they say 'milk', say 'more milk' or 'warm milk'.",
        "Pretend play: feed a teddy, put a doll to sleep, cook in a toy kitchen.",
        "Sort things by colour or size together: red blocks here, blue ones there.",
        "Lots of outdoor play: running, climbing steps, kicking a ball.",
    ]},
]

# Ideas for every child, including those who need a different pace.
EVERY_CHILD = [
    "Follow your child's lead: notice what holds their attention and join in with that.",
    "If loud or busy places upset your child, play in a quiet corner with one toy at a time.",
    "Use the same simple words and a daily routine. Picture cards for 'eat', 'bath' and 'sleep' help many children.",
    "Celebrate small steps. Progress at their own pace is still progress.",
]

# CDC 2022 milestone checklists, a few per age. Ids are stable; never renumber.
MILESTONES = [
    {"months": 2, "items": [
        ("m2-face", "Looks at your face"), ("m2-smile", "Smiles when you talk to or smile at them"),
        ("m2-sounds", "Makes sounds other than crying"), ("m2-head", "Holds head up when on tummy"),
        ("m2-calms", "Calms down when spoken to or picked up"), ("m2-moves", "Moves both arms and both legs"),
    ]},
    {"months": 4, "items": [
        ("m4-chuckle", "Chuckles when you try to make them laugh"), ("m4-coo", "Makes cooing sounds"),
        ("m4-voice", "Turns head towards the sound of your voice"), ("m4-hold", "Holds a toy when you put it in their hand"),
        ("m4-steady", "Holds head steady without support when you hold them"), ("m4-mouth", "Brings hands to mouth"),
    ]},
    {"months": 6, "items": [
        ("m6-people", "Knows familiar people"), ("m6-laughs", "Laughs"), ("m6-turns", "Takes turns making sounds with you"),
        ("m6-reach", "Reaches to grab a toy they want"), ("m6-roll", "Rolls from tummy to back"),
        ("m6-sitlean", "Leans on hands to support themselves when sitting"),
    ]},
    {"months": 9, "items": [
        ("m9-name", "Looks when you call their name"), ("m9-babble", "Makes sounds like 'mamamama' and 'babababa'"),
        ("m9-armsup", "Lifts arms up to be picked up"), ("m9-looks", "Looks for things when you drop them out of sight"),
        ("m9-sits", "Sits without support"), ("m9-passes", "Moves things from one hand to the other"),
    ]},
    {"months": 12, "items": [
        ("m12-wave", "Waves bye-bye"), ("m12-mama", "Calls a parent 'mama', 'dada' or another special name"),
        ("m12-no", "Understands 'no' (pauses or stops when you say it)"), ("m12-pull", "Pulls up to stand"),
        ("m12-cruise", "Walks holding on to furniture"), ("m12-pincer", "Picks up small things between thumb and finger"),
    ]},
    {"months": 15, "items": [
        ("m15-shows", "Shows you something they like"), ("m15-words", "Tries to say one or two words besides 'mama' or 'dada'"),
        ("m15-points", "Points to ask for something"), ("m15-steps", "Takes a few steps on their own"),
        ("m15-stack", "Stacks at least two small things"), ("m15-feeds", "Uses fingers to feed themselves"),
    ]},
    {"months": 18, "items": [
        ("m18-three", "Tries to say three or more words besides 'mama' or 'dada'"), ("m18-follows", "Follows one-step directions without gestures, like 'give it to me'"),
        ("m18-pointshow", "Points to show you something interesting"), ("m18-walks", "Walks without holding on"),
        ("m18-scribble", "Scribbles"), ("m18-copies", "Copies you doing chores, like sweeping"),
    ]},
    {"months": 24, "items": [
        ("m24-two", "Says at least two words together, like 'more milk'"), ("m24-body", "Points to at least two body parts when you ask"),
        ("m24-book", "Points to things in a book when you ask"), ("m24-notices", "Notices when others are hurt or upset"),
        ("m24-kick", "Kicks a ball"), ("m24-spoon", "Eats with a spoon"),
    ]},
]
MILESTONE_IDS = {mid for group in MILESTONES for mid, _ in group["items"]}

# India's National Immunization Schedule, birth to 2 years. "weeks" or "months" is when it is due.
VACCINES = [
    {"id": "bcg", "name": "BCG", "due_days": 0, "when": "At birth"},
    {"id": "opv0", "name": "OPV-0 (polio drops)", "due_days": 0, "when": "At birth"},
    {"id": "hepb0", "name": "Hepatitis B birth dose", "due_days": 0, "when": "At birth (within 24 hours)"},
    {"id": "w6", "name": "OPV-1, Pentavalent-1, Rotavirus-1, fIPV-1, PCV-1", "due_days": 42, "when": "6 weeks"},
    {"id": "w10", "name": "OPV-2, Pentavalent-2, Rotavirus-2", "due_days": 70, "when": "10 weeks"},
    {"id": "w14", "name": "OPV-3, Pentavalent-3, Rotavirus-3, fIPV-2, PCV-2", "due_days": 98, "when": "14 weeks"},
    {"id": "m9", "name": "MR-1 (measles, rubella), PCV booster, fIPV-3, Vitamin A (1st dose)", "due_days": 274, "when": "9 months"},
    {"id": "je1", "name": "JE-1 (Japanese encephalitis, in districts where it is given)", "due_days": 274, "when": "9 months", "optional": True},
    {"id": "m16", "name": "MR-2, DPT booster-1, OPV booster, Vitamin A (2nd dose)", "due_days": 487, "when": "16 to 24 months"},
    {"id": "je2", "name": "JE-2 (in districts where it is given)", "due_days": 487, "when": "16 to 24 months", "optional": True},
]
VACCINE_IDS = {v["id"] for v in VACCINES}
VACCINE_NOTE = (
    "Free at government health centres and anganwadis. Your doctor may also suggest other vaccines from the "
    "Indian Academy of Pediatrics schedule. A mild fever or a sore leg for a day or two afterwards is common."
)

# Feeding by age (WHO).
FOOD = [
    {"from": 0, "to": 6, "points": [
        "Only breast milk for the first 6 months: no water, honey, ghutti or other drinks, even in hot weather.",
        "Feed whenever your baby wants, usually 8 to 12 times in 24 hours, day and night.",
        "Enough milk usually means 6 or more wet nappies a day after the first week, and steady weight gain at check-ups.",
    ]},
    {"from": 6, "to": 12, "points": [
        "Start other foods at 6 months and keep breastfeeding.",
        "Begin with soft, mashed foods: rice and dal, ragi porridge, mashed banana, egg yolk, well-cooked vegetables.",
        "Start with 2 to 3 spoons, 2 or 3 times a day, and give more as your baby wants it.",
        "No honey before 1 year, and no added salt or sugar.",
    ]},
    {"from": 12, "to": 24, "points": [
        "Three meals and one or two healthy snacks a day, from what the family eats, cut small and not spicy.",
        "Keep breastfeeding up to 2 years or beyond if you both want to.",
        "Include iron-rich foods every day: dal, green leafy vegetables, eggs, meat or fish if your family eats them.",
        "Avoid packaged chips, biscuits and sweet drinks.",
    ]},
]

SLEEP = [
    "Always put your baby to sleep on their back, on a firm, flat surface.",
    "Keep pillows, soft toys and loose blankets away from your baby's face.",
    "Keep your baby close, in your room. If you share a bed, keep pillows and quilts away from your baby, and never share a bed after alcohol or if anyone smokes.",
    "No smoking anywhere near your baby.",
]

LOG_KINDS = {
    "breastfeed": {"label": "Breastfeed", "icon": "🤱"},
    "bottle": {"label": "Bottle", "icon": "🍼"},
    "food": {"label": "Food", "icon": "🥣"},
    "sleep": {"label": "Sleep", "icon": "😴"},
    "nappy": {"label": "Nappy", "icon": "🧷"},
}

# Common questions, answered from the sources above. Each says when to see a doctor.
QUESTIONS = [
    {"id": "feeds", "q": "How often should my newborn feed?", "source": "who_feeding",
     "a": "Most newborns feed 8 to 12 times in 24 hours, including at night. Feed when you see early hunger signs: rooting, sucking on hands, lip smacking. Crying is a late sign."},
    {"id": "enough-milk", "q": "How do I know my baby is getting enough milk?", "source": "who_feeding",
     "a": "After the first week, 6 or more wet nappies a day, regular yellow poos, and steady weight gain at check-ups are good signs. See a doctor if there are fewer wet nappies, your baby is very sleepy and hard to wake for feeds, or isn't gaining weight."},
    {"id": "water", "q": "Can I give my baby water in hot weather?", "source": "who_feeding",
     "a": "Not before 6 months if your baby is breastfed. Breast milk is mostly water and gives all they need, even in summer. Feed more often instead."},
    {"id": "solids", "q": "When and how do I start solid food?", "source": "who_feeding",
     "a": "At 6 months, while you keep breastfeeding. Start with soft mashed foods like rice and dal, ragi porridge or banana, a few spoons a day, and slowly give more and thicker food. No honey before 1 year, no added salt or sugar."},
    {"id": "jaundice", "q": "My baby looks a little yellow. Is that normal?", "source": "imnci",
     "a": "Mild yellowness in the face from day 2 to 3 is common and often fades within two weeks. See a doctor the same day if it starts in the first 24 hours, spreads to the palms or soles, or your baby is feeding poorly or very sleepy."},
    {"id": "fever", "q": "What should I do if my baby has a fever?", "source": "imnci",
     "a": "Any fever in a baby under 2 months needs a doctor now. For older babies, keep feeding, dress them lightly, and see a doctor if the fever lasts more than a day, or there are any of the warning signs listed on this page. Only give medicine your doctor has advised, at the dose for your baby's weight."},
    {"id": "crying", "q": "My baby cries a lot in the evening. What can I do?", "source": "nhs",
     "a": "Many babies have a fussy time in the evening in the first 3 months. Try feeding, burping, holding them close, gentle rocking, a quiet dark room, or a walk. If you feel overwhelmed, put the baby down safely and take a few minutes. See a doctor if the crying is unusual for your baby, very high-pitched, or comes with fever, vomiting or poor feeding."},
    {"id": "spitup", "q": "My baby spits up after feeds. Is that a problem?", "source": "nhs",
     "a": "Bringing up small amounts of milk is common and usually stops by about a year. Keep your baby upright for a while after feeds. See a doctor if the vomit is forceful, green, has blood, or your baby isn't gaining weight."},
    {"id": "teething", "q": "What helps with teething?", "source": "nhs",
     "a": "A clean, cool teething ring or a gentle rub of the gums with a clean finger. Teething can make babies fussy but does not cause high fever or diarrhoea; if those happen, see a doctor."},
    {"id": "massage", "q": "Is oil massage safe?", "source": "nhs",
     "a": "A gentle massage with a little plain oil is a lovely way to bond. Don't put oil in the nose, ears or eyes, and stop if the skin gets a rash."},
    {"id": "sleep-position", "q": "Which position should my baby sleep in?", "source": "aap_sleep",
     "a": "Always on their back, on a firm flat surface, with no pillows, soft toys or loose blankets near the face. This lowers the risk of sudden infant death."},
    {"id": "screens", "q": "Can my baby watch videos?", "source": "iap_screen",
     "a": "Doctors in India advise no screens before 2 years. Babies learn words from you, not from videos. If you need a few minutes, SYNiq's together-time for 18 to 24 months is slow and short, but talking and playing with your baby is always better."},
    {"id": "talking", "q": "When should I worry if my baby isn't talking?", "source": "cdc",
     "a": "Most babies babble by 9 months, say a word or two by 15 months, and put two words together by 2 years. If your baby isn't doing these, doesn't respond to their name, or has stopped using words they had, mention it to your doctor. Checking early is always better than waiting."},
    {"id": "vaccine-side", "q": "My baby has a fever after vaccines. Is that normal?", "source": "uip",
     "a": "A mild fever, fussiness or a sore spot for a day or two is common. Keep feeding and cuddling. See a doctor if the fever is high, lasts more than two days, or your baby is very unwell."},
    {"id": "baby-blues", "q": "I feel low and cry a lot since the baby came. Is that normal?", "source": "telemanas",
     "a": "Many mothers feel weepy and tired in the first two weeks. If it lasts longer, you feel hopeless, can't sleep even when the baby sleeps, or have thoughts of harming yourself or the baby, please talk to your doctor or call Tele-MANAS on 14416 (free, any time). You're not alone, and help works."},
    {"id": "mum-rest", "q": "How do I look after myself?", "source": "nhs",
     "a": "Rest when the baby sleeps, eat well and drink water, and let family help with cooking and chores. See a doctor if you have heavy bleeding, fever, a painful red area in the breast, or pain that's getting worse."},
]


def play_for(months: int) -> dict:
    return next((p for p in PLAY if p["from"] <= months < p["to"]), PLAY[-1])


def food_for(months: int) -> dict:
    return next((f for f in FOOD if f["from"] <= months < f["to"]), FOOD[-1])
