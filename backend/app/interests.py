"""Interest exploration: short activities across eight areas, open to every student.

Each activity takes 10 to 20 minutes, needs nothing that has to be bought, and can be
done at home or school. Afterwards the student says how it felt (loved it, it was okay,
not for me) and can write what they made or noticed.

SYNiq never turns this into a label such as "you are creative". It only remembers what
the student enjoyed, shows it back to them in their own space, and suggests more from
areas they liked alongside areas they haven't tried yet, so nobody is boxed in early.
Nobody else sees a student's reflections.
"""

AREAS = ("creative", "practical", "scientific", "social", "enterprise", "movement", "nature", "technology")

# Every activity can be done in more than one way: by touch, by talking it through, with a
# helper doing the hands while the student leads, sitting down, or with sound instead of
# sight. The app says so on every activity, so no area is closed to a disabled student.

ACTIVITIES: list[dict] = [
    # --- Creative
    {
        "id": "creative.comic",
        "area": "creative",
        "title": "A four-box comic",
        "minutes": 15,
        "intro": "Tell a tiny story in four pictures. Stick figures are perfect.",
        "steps": [
            "Fold a sheet of paper into four boxes.",
            "Pick something small that happened today: missing the bus, a cat on the wall, a power cut.",
            "Box 1: the start. Box 2: something changes. Box 3: it gets worse or funnier. Box 4: the ending.",
            "Add one speech bubble in at least two boxes.",
        ],
        "reflect": "Which box was the most fun to draw, and why?",
    },
    {
        "id": "creative.sounds",
        "area": "creative",
        "title": "Rhythm from things around you",
        "minutes": 10,
        "intro": "Make a short beat using only objects nearby: a steel tumbler, a table, a bucket.",
        "steps": [
            "Find three things that make different sounds when tapped.",
            "Make a pattern of 8 taps and repeat it until you can do it without thinking.",
            "Add a second pattern on another object that fits with the first.",
            "Try it faster, then slower. Which speed sounds best?",
        ],
        "reflect": "What sound surprised you the most?",
    },
    {
        "id": "creative.poem",
        "area": "creative",
        "title": "A poem about one ordinary thing",
        "minutes": 15,
        "intro": "Write six short lines about something you see every day, in English or Malayalam.",
        "steps": [
            "Choose an ordinary object: an umbrella, a coconut tree, your school bag.",
            "Write one line about how it looks, one about a sound, one about a smell or touch.",
            "Write one line about what it would say if it could talk.",
            "Finish with two lines about what it means to you.",
        ],
        "reflect": "Read it aloud. Which line do you like best?",
    },
    {
        "id": "creative.design",
        "area": "creative",
        "title": "Redesign a book cover",
        "minutes": 15,
        "intro": "Pick any textbook and draw a new cover that would make a Class 6 student want to open it.",
        "steps": [
            "Look at the old cover. What does it tell you about the book?",
            "Choose one picture or symbol that sums up the subject.",
            "Sketch two different layouts before choosing one.",
            "Add the title in lettering that suits the subject.",
        ],
        "reflect": "What did you change, and why would it work better?",
    },
    # --- Practical
    {
        "id": "practical.fix",
        "area": "practical",
        "title": "Find out how something works",
        "minutes": 15,
        "intro": "Look closely at a simple thing at home and work out how it does its job, with an adult's okay.",
        "steps": [
            "Choose something simple and safe: a ball-point pen, a torch, a door latch, a clothes peg.",
            "Without breaking it, look at every part. Draw it and label the parts.",
            "Write how each part helps it work.",
            "What would stop working if one part were missing?",
        ],
        "reflect": "Was it simpler or more clever than you expected?",
    },
    {
        "id": "practical.cook",
        "area": "practical",
        "title": "Make a no-fire snack",
        "minutes": 20,
        "intro": "Make a simple snack that needs no stove, like a fruit chaat or a banana and peanut plate.",
        "steps": [
            "Plan it first: what you need, how much, and the order of steps.",
            "Wash your hands and the fruit. Ask an adult before using a knife.",
            "Make it, and set it out so it looks good.",
            "Share it and ask one person what they would change.",
        ],
        "reflect": "What would you do differently next time?",
    },
    {
        "id": "practical.garden",
        "area": "practical",
        "title": "Start a seed in a cup",
        "minutes": 10,
        "intro": "Plant a seed from your kitchen (green gram, chilli, tomato) and look after it for a week.",
        "steps": [
            "Poke a few holes in the bottom of a used cup or container, and fill it with soil.",
            "Plant 3 or 4 seeds about a finger-joint deep. Water gently.",
            "Put it where it gets some sunlight.",
            "Check it every day and write one line about what you see.",
        ],
        "reflect": "Come back after a few days. What happened?",
    },
    {
        "id": "practical.map",
        "area": "practical",
        "title": "Map your route to school",
        "minutes": 15,
        "intro": "Draw a map of how you get from home to school that a visitor could follow.",
        "steps": [
            "Mark home and school, then the main turns between them.",
            "Add three landmarks a stranger would notice: a temple, a shop, a big tree.",
            "Add a rough scale: how long does each part take to walk or ride?",
            "Give it to someone at home and see if they can follow it.",
        ],
        "reflect": "What was hardest to show on paper?",
    },
    # --- Scientific
    {
        "id": "scientific.float",
        "area": "scientific",
        "title": "What floats?",
        "minutes": 15,
        "intro": "Predict, then test, which things float in a bucket of water.",
        "steps": [
            "Collect 8 small things: a key, a leaf, a coin, a plastic cap, a pencil, a stone, a vegetable, a ball of foil.",
            "Write your guess for each: float or sink.",
            "Test each one and write what happened.",
            "Squash the foil into a tight ball and try again. What changed?",
        ],
        "reflect": "Which result surprised you? What could explain it?",
    },
    {
        "id": "scientific.sky",
        "area": "scientific",
        "title": "Watch the Moon for a week",
        "minutes": 10,
        "intro": "Look at the Moon at the same time each evening and draw what you see.",
        "steps": [
            "Pick a time and a spot you can use every evening.",
            "Draw the Moon's shape and note where it is in the sky (over a tree, a roof).",
            "Do it again each evening for a week, or whenever the sky is clear.",
            "Look at your drawings side by side. What pattern do you see?",
        ],
        "reflect": "Can you guess what it will look like next week?",
    },
    {
        "id": "scientific.survey",
        "area": "scientific",
        "title": "Count the birds",
        "minutes": 15,
        "intro": "Sit quietly for 10 minutes and record every bird you see or hear.",
        "steps": [
            "Find a spot near trees, a field or a backyard.",
            "For 10 minutes, tally each bird: crow, myna, sparrow, kingfisher, or 'unknown'.",
            "Note the time and the weather.",
            "Try again at a different time of day and compare.",
        ],
        "reflect": "Which bird did you see most? Why might that be?",
    },
    {
        "id": "scientific.pattern",
        "area": "scientific",
        "title": "Number patterns in nature",
        "minutes": 15,
        "intro": "Count petals, leaves and seeds and look for numbers that keep coming back.",
        "steps": [
            "Count the petals on five different flowers.",
            "Count how many leaflets are on a few different leaves.",
            "Look at a pineapple, a sunflower or a pine cone if you can find one, and count the spirals.",
            "Write down all your numbers. Do any appear again and again?",
        ],
        "reflect": "Did you find any numbers like 3, 5, 8 or 13 more than once?",
    },
    # --- Social
    {
        "id": "social.interview",
        "area": "social",
        "title": "Interview an elder",
        "minutes": 20,
        "intro": "Ask a grandparent, neighbour or older relative what school was like for them.",
        "steps": [
            "Write four questions first, such as: How did you get to school? What did you learn? What games did you play?",
            "Ask them, and listen more than you talk.",
            "Write the three most interesting things they told you.",
            "Thank them, and tell them one thing about your school today.",
        ],
        "reflect": "What is the biggest difference between their school days and yours?",
    },
    {
        "id": "social.help",
        "area": "social",
        "title": "A small kindness plan",
        "minutes": 10,
        "intro": "Plan and do one small helpful thing for someone this week.",
        "steps": [
            "Think of someone who could use a hand: a younger child, a neighbour, someone at home.",
            "Choose something small you can really do: help with homework, carry shopping, teach a game.",
            "Do it.",
            "Write how they reacted and how you felt.",
        ],
        "reflect": "Would you do something like this again?",
    },
    {
        "id": "social.debate",
        "area": "social",
        "title": "Argue both sides",
        "minutes": 15,
        "intro": "Pick a question and write the best reasons for both answers.",
        "steps": [
            "Pick a question, e.g. 'Should school start an hour later?' or 'Should phones be allowed in class?'",
            "Write three strong reasons for 'yes'.",
            "Write three strong reasons for 'no'.",
            "Now decide what you really think, and which reason changed your mind the most.",
        ],
        "reflect": "Was it hard to argue for the side you disagree with?",
    },
    {
        "id": "social.teach",
        "area": "social",
        "title": "Teach a five-minute lesson",
        "minutes": 15,
        "intro": "Teach someone at home something you know well, in five minutes.",
        "steps": [
            "Choose a small topic you are good at: a maths trick, a game rule, how to draw something.",
            "Plan three steps and one example.",
            "Teach it, then ask them to show you they understood.",
            "Ask them what was clear and what was confusing.",
        ],
        "reflect": "What did you learn from teaching it?",
    },
    # --- Enterprise
    {
        "id": "enterprise.problem",
        "area": "enterprise",
        "title": "Spot a problem worth solving",
        "minutes": 15,
        "intro": "Notice small everyday problems and imagine a fix.",
        "steps": [
            "During one day, write down three small things that annoy people around you.",
            "Pick one. Who has this problem, and how often?",
            "Think of two different ways to fix it.",
            "Which fix is cheapest? Which would people like most?",
        ],
        "reflect": "Would anyone pay for your fix, or would it just be a good thing to do?",
    },
    {
        "id": "enterprise.stall",
        "area": "enterprise",
        "title": "Plan a school-fair stall",
        "minutes": 20,
        "intro": "Plan a stall for a school fair on paper: what you would sell or offer, and whether it would work.",
        "steps": [
            "Choose what to offer: a snack, a game, a craft, a service.",
            "List what you would need and what each thing costs.",
            "Choose a price. How many would you need to sell to cover your costs?",
            "Draw a sign for your stall.",
        ],
        "reflect": "What is the biggest risk, and how could you reduce it?",
    },
    {
        "id": "enterprise.pitch",
        "area": "enterprise",
        "title": "One-minute pitch",
        "minutes": 15,
        "intro": "Pick any everyday object and convince someone in one minute that they need it.",
        "steps": [
            "Choose an object: an umbrella, a water bottle, a pencil box.",
            "Write who needs it, the problem it solves, and one thing that makes it special.",
            "Practise saying it in under a minute.",
            "Pitch it to someone at home and ask: would you buy it?",
        ],
        "reflect": "What part of your pitch worked best?",
    },
    {
        "id": "enterprise.budget",
        "area": "enterprise",
        "title": "Plan a family trip on a budget",
        "minutes": 20,
        "intro": "Plan a one-day trip for your family for ₹1,500, with a little help from someone at home.",
        "steps": [
            "Choose a place within a few hours of home.",
            "List the costs: travel, food, entry tickets.",
            "If it costs more than ₹1,500, find ways to cut it down.",
            "Share your plan. What did your family think?",
        ],
        "reflect": "What was the hardest thing to fit in the budget?",
    },
    # --- Movement
    {
        "id": "movement.routine",
        "area": "movement",
        "title": "Make up a one-minute movement routine",
        "minutes": 10,
        "intro": "Put together eight moves into a routine you can repeat. Sitting down or standing both work.",
        "steps": [
            "Choose four moves your body likes: a clap, a stretch, a turn, a nod, a wheel of the arms.",
            "Put them in an order and count 1 to 8 as you do them.",
            "Repeat the routine three times. Can you do it with your eyes closed?",
            "Teach it to someone, or say it out loud step by step.",
        ],
        "reflect": "Which move felt best? What would make the routine harder?",
    },
    {
        "id": "movement.target",
        "area": "movement",
        "title": "Rolled-paper target game",
        "minutes": 15,
        "intro": "Roll paper into balls and get them into a bucket or box from further and further away.",
        "steps": [
            "Make five paper balls and put a bucket or box on the floor.",
            "Start close. Each time three of five go in, move one step back.",
            "Try throwing, rolling, or pushing the ball along a slope made from a book.",
            "Ask someone to clap near the box if you aim better by sound.",
        ],
        "reflect": "Which way of sending the ball worked best for you?",
    },
    {
        "id": "movement.balance",
        "area": "movement",
        "title": "Balance and breathe",
        "minutes": 10,
        "intro": "Find out how still and steady your body can be.",
        "steps": [
            "Sit or stand tall. Breathe in for 4 counts and out for 4 counts, five times.",
            "Balance something light on your head or hand, like a folded cloth, and count how long it stays.",
            "Try again after slow breathing. Does it stay longer?",
            "Make up your own balance challenge.",
        ],
        "reflect": "How did your body feel at the end?",
    },
    # --- Nature
    {
        "id": "nature.watch",
        "area": "nature",
        "title": "Ten minutes of watching",
        "minutes": 10,
        "intro": "Sit near a window, a plant, a tree or a garden and notice living things.",
        "steps": [
            "Sit quietly for ten minutes. Look, listen and smell.",
            "Count the different birds, insects or animals you notice, by sight or by sound.",
            "Pick one and follow what it does for a minute.",
            "Draw it, describe it aloud, or write three lines about it.",
        ],
        "reflect": "What was the living thing doing, and why do you think it did that?",
    },
    {
        "id": "nature.seed",
        "area": "nature",
        "title": "Grow a seed",
        "minutes": 15,
        "intro": "Plant a few seeds from the kitchen and see what happens over a week.",
        "steps": [
            "Take a few seeds: green gram, mustard, or a chilli seed.",
            "Put them on wet cotton or soil in a cup, and keep it near light.",
            "Check every day. Feel the seed, look at it, note any change.",
            "Try one cup in the dark too. What is different?",
        ],
        "reflect": "What changed first? What did the plant need most?",
    },
    {
        "id": "nature.leaves",
        "area": "nature",
        "title": "A leaf collection",
        "minutes": 15,
        "intro": "Collect fallen leaves and sort them in your own way.",
        "steps": [
            "Gather eight to ten fallen leaves from different plants.",
            "Feel their edges, smell them, look at their veins.",
            "Sort them into groups that make sense to you: by shape, size, smell or feel.",
            "Find out the name of one plant from someone at home.",
        ],
        "reflect": "How did you decide your groups?",
    },
    # --- Technology
    {
        "id": "technology.instructions",
        "area": "technology",
        "title": "Program a person",
        "minutes": 15,
        "intro": "Write exact instructions for a simple job, the way a computer program does.",
        "steps": [
            "Choose a job: making a cup of water, drawing a house, walking to the door.",
            "Write or say every step, one tiny action at a time.",
            "Ask someone to follow your steps exactly, word for word.",
            "Fix any step that went wrong and try again.",
        ],
        "reflect": "Which step was missing the first time?",
    },
    {
        "id": "technology.code",
        "area": "technology",
        "title": "A secret code",
        "minutes": 10,
        "intro": "Invent a code to send a secret message, like early computer engineers did.",
        "steps": [
            "Pick a rule: shift every letter one along (A becomes B), or use taps and pauses.",
            "Write or tap a short message in your code.",
            "Give someone the rule and see if they can read it.",
            "Make a harder rule and try again.",
        ],
        "reflect": "What makes a code easy to read but hard to crack?",
    },
    {
        "id": "technology.machine",
        "area": "technology",
        "title": "Build a simple machine",
        "minutes": 20,
        "intro": "Make something that moves using things at home: a ramp, a lever, or a pulley.",
        "steps": [
            "Choose one: a ramp from a book, a lever from a ruler and pencil, or a pulley from string and a spool.",
            "Use it to move or lift something small.",
            "Change one thing (the slope, the length, the weight) and see what happens.",
            "Explain how it makes the job easier.",
        ],
        "reflect": "What did you change, and what happened?",
    },
]

BY_ID = {a["id"]: a for a in ACTIVITIES}
FEELINGS = ("loved", "okay", "not_for_me")


def suggest(done: dict[str, str], count: int = 3) -> list[str]:
    """Suggestions that keep exploring broad: an area the student hasn't tried first,
    then more from areas they loved. Activities already done are not suggested again."""
    tried_areas = {BY_ID[a]["area"] for a in done if a in BY_ID}
    loved_areas = [BY_ID[a]["area"] for a, f in done.items() if f == "loved" and a in BY_ID]
    fresh = [a for a in ACTIVITIES if a["id"] not in done]
    picks: list[str] = []

    def take(pred):
        for a in fresh:
            if len(picks) >= count:
                return
            if a["id"] not in picks and pred(a) and a["area"] not in {BY_ID[p]["area"] for p in picks}:
                picks.append(a["id"])
                return

    take(lambda a: a["area"] not in tried_areas)  # somewhere new
    for area in dict.fromkeys(loved_areas):  # more of what they loved
        take(lambda a, area=area: a["area"] == area)
    while len(picks) < count:
        before = len(picks)
        take(lambda a: a["area"] not in tried_areas)
        take(lambda a: True)
        if len(picks) == before:
            # Fewer areas than slots: allow a second from the same area.
            extra = [a["id"] for a in fresh if a["id"] not in picks]
            if not extra:
                break
            picks.append(extra[0])
    return picks[:count]
