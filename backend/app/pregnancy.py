"""The pregnancy section: for the mother's wellbeing and to know what to expect.

Calm activities are offered for her peace of mind. SYNiq does not claim they build the baby's
brain: there is no good evidence for that. Check-ups and warning signs follow WHO and India's
Ministry of Health. Information, not medical advice.
"""

SOURCES = {
    "who_anc": {"name": "WHO recommendations on antenatal care for a positive pregnancy experience (2016)", "url": "https://www.who.int/publications/i/item/9789241549912"},
    "pmsma": {"name": "Pradhan Mantri Surakshit Matritva Abhiyan (free check-up on the 9th of every month)", "url": "https://pmsma.mohfw.gov.in/"},
    "mohfw_anc": {"name": "Ministry of Health and Family Welfare, Mother and Child Protection Card", "url": "https://nhm.gov.in/images/pdf/programmes/maternal-health/guidelines/MCP_Card_English_version.pdf"},
    "telemanas": {"name": "Tele-MANAS, national mental health helpline (14416)", "url": "https://telemanas.mohfw.gov.in/"},
}

DISCLAIMER = (
    "Information from WHO and India's Ministry of Health, not medical advice. "
    "Your doctor or ANM knows your pregnancy best: follow their advice."
)

GO_TO_HOSPITAL_NOW = [
    "Bleeding from the vagina",
    "Severe headache, blurred vision, or swelling of the face and hands",
    "Fits (convulsions) or fainting",
    "High fever",
    "Severe pain in the belly",
    "Water leaking from the vagina",
    "Baby moving much less than usual, or not at all (later in pregnancy)",
    "Difficulty breathing",
]

CARE = [
    "Have at least 4 check-ups, and more if your doctor advises; WHO now recommends 8 contacts. The first one as early as possible.",
    "Free check-ups at government hospitals on the 9th of every month (PMSMA).",
    "Take the iron and folic acid tablets and calcium your health worker gives you, every day.",
    "Get the two Td (tetanus) injections on time.",
    "Eat a little extra every day: dal, green vegetables, fruit, milk, eggs or meat if you eat them. Rest on your left side when you lie down later in pregnancy.",
    "No smoking, tobacco or alcohol.",
]

# Month of pregnancy (1 to 9): what's happening, and something to do this month.
MONTHS = [
    {"month": 1, "baby": "The baby is just starting to form. Many mothers don't know yet.", "you": "Start folic acid tablets if you haven't, and book your first check-up."},
    {"month": 2, "baby": "The heart starts beating and the main organs begin to form.", "you": "Tiredness and morning sickness are common. Small, frequent meals help."},
    {"month": 3, "baby": "Tiny fingers and toes have formed. The baby is about the size of a lime.", "you": "Have your first check-up and blood tests if you haven't yet. Register for the MCP card."},
    {"month": 4, "baby": "The baby can move, though you may not feel it yet.", "you": "Many mothers feel more energy now. Start the iron and calcium tablets your health worker gives you."},
    {"month": 5, "baby": "You may feel the first flutters of movement.", "you": "Your anomaly scan is usually done around now. Gentle walks are good for you."},
    {"month": 6, "baby": "The baby can hear sounds, including your voice.", "you": "Talk or sing to your baby if you like: it's a lovely way to feel close. Watch for swelling or headaches."},
    {"month": 7, "baby": "The baby is growing fast and moves a lot.", "you": "Get to know your baby's pattern of movements. Plan where you'll give birth and how you'll get there."},
    {"month": 8, "baby": "The baby is putting on weight and getting ready for birth.", "you": "Pack a bag for hospital: your MCP card, clothes for you and the baby, and a phone charger."},
    {"month": 9, "baby": "The baby is ready to be born any time from 37 weeks.", "you": "Learn the signs of labour: regular pains getting closer, water breaking, or a show of blood. Call 102 or 108 for free transport."},
]

# Calm activities for the mother. Offered for her peace, never as "brain building" for the baby.
CALM = [
    {"id": "breathe", "title": "Slow breathing", "minutes": 3, "steps": [
        "Sit comfortably and rest one hand on your belly.",
        "Breathe in through your nose for a count of 4.",
        "Breathe out slowly through your mouth for a count of 6.",
        "Repeat ten times. Notice your shoulders dropping.",
    ]},
    {"id": "walk", "title": "A gentle walk", "minutes": 15, "steps": [
        "Walk at an easy pace, in the morning or evening when it's cooler.",
        "Notice five things you can see, four you can hear, and three you can smell.",
        "Stop and rest whenever you want. Drink water afterwards.",
    ]},
    {"id": "letter", "title": "A letter to your baby", "minutes": 10, "steps": [
        "Write a few lines to your baby: what you're looking forward to, a hope, a song you'll sing.",
        "There's no right way. Keep it to read together one day.",
    ]},
    {"id": "words", "title": "A word puzzle for you", "minutes": 5, "steps": [
        "Think of a word for each letter of your baby's name, or the word BABY.",
        "Then try a word that starts with the last letter of the one before, as many as you can.",
        "It's just for fun and a calm mind.",
    ]},
    {"id": "music", "title": "Music and rest", "minutes": 10, "steps": [
        "Lie on your left side with a pillow between your knees.",
        "Play a song you love, softly. Close your eyes and just listen.",
    ]},
    {"id": "worry", "title": "Put a worry down", "minutes": 5, "steps": [
        "Write down one thing that's worrying you.",
        "Next to it, write one small thing you could do, or who you could ask.",
        "If worries won't leave you, talk to your doctor or call Tele-MANAS on 14416.",
    ]},
]


def week_of(days_to_due: int) -> int:
    return max(1, min(42, 40 - days_to_due // 7))


def month_of(week: int) -> int:
    return max(1, min(9, -(-week * 9 // 40)))  # nine months over 40 weeks
