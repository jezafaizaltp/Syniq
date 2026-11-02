"""Healthy screen time for ages 2 to 4.

Built to the guidelines: WHO (2019) and the Indian Academy of Pediatrics both say at most
1 hour a day for 2 to 4 year olds, less is better, and best with an adult. So:

- The parent sets a daily limit (default 20 minutes, never more than 60) and a session length
  (default 10 minutes, never more than 15). When a session ends, SYNiq says goodbye gently and
  offers something to do away from the screen. Only an adult can start another.
- Nothing plays by itself: every word and picture waits for a tap. No points, stars, streaks,
  timers the child can see, fast cuts or background music.
- Every activity comes with a line for the adult to say along with the child, because toddlers
  learn words far better from a person than from a screen.

Pictures are emoji so every activity works offline once loaded. Three kinds of activity:
"name" (tap a picture, hear its word), "find" (tap the one that was asked for) and
"count" (tap each thing to count it aloud).

From 18 to 24 months there is a smaller together-time: only the "name" activities, at most
10 minutes a day, meant for the child on an adult's lap. Before 18 months there is nothing on screen.
"""

DAILY_DEFAULT, DAILY_MAX = 20, 60
SESSION_DEFAULT, SESSION_MAX = 10, 15
TODDLER_MINUTES = 10  # 18 to 24 months: one short together-time a day at most

AREAS = {
    "words": "First words",
    "colours": "Colours and shapes",
    "counting": "Counting",
    "same": "Same and different",
    "feelings": "Feelings",
    "world": "The world around us",
}


def _n(*pairs):
    return [{"pic": p, "word": w, "say": s} for p, w, s in pairs]


def _f(*rounds):
    return [{"ask": a, "options": [{"pic": p, "word": w} for p, w in opts], "answer": ans} for a, opts, ans in rounds]


def _c(*rounds):
    return [{"pic": p, "word": w, "n": n} for p, w, n in rounds]


ACTIVITIES = [
    # --- First words
    {"id": "farm-animals", "area": "words", "title": "Farm animals", "pic": "🐄", "kind": "name",
     "items": _n(("🐄", "cow", "Cow. The cow says moo."), ("🐐", "goat", "Goat. The goat says meh."), ("🐓", "hen", "Hen. The hen says cluck cluck."),
                 ("🐃", "buffalo", "Buffalo. A big buffalo."), ("🐕", "dog", "Dog. The dog says woof.")),
     "together": "Make each animal's sound together, then ask: which one is your favourite?",
     "after": "Next time you see a cow, a dog or a hen outside, stop and name it together."},
    {"id": "fruits", "area": "words", "title": "Fruits", "pic": "🍌", "kind": "name",
     "items": _n(("🍌", "banana", "Banana. Long and yellow."), ("🥭", "mango", "Mango. Sweet and juicy."), ("🍎", "apple", "Apple. Round and red."),
                 ("🍉", "watermelon", "Watermelon. Green outside, red inside."), ("🍇", "grapes", "Grapes. Small and round.")),
     "together": "Ask which fruit they ate today, and which one they'd like tomorrow.",
     "after": "At meal time, let them hold a real fruit, smell it, and say its name."},
    {"id": "my-body", "area": "words", "title": "My body", "pic": "👃", "kind": "name",
     "items": _n(("👀", "eyes", "Eyes. We see with our eyes."), ("👃", "nose", "Nose. We smell with our nose."), ("👂", "ears", "Ears. We hear with our ears."),
                 ("✋", "hand", "Hand. We wave with our hand."), ("🦶", "foot", "Foot. We walk with our feet.")),
     "together": "After each one, touch your own nose, ears or hands together.",
     "after": "Play 'touch your nose, touch your toes' together, faster and slower."},
    {"id": "at-home", "area": "words", "title": "Things at home", "pic": "🏠", "kind": "name",
     "items": _n(("🛏️", "bed", "Bed. We sleep in a bed."), ("🪑", "chair", "Chair. We sit on a chair."), ("🥄", "spoon", "Spoon. We eat with a spoon."),
                 ("🚪", "door", "Door. Open and close the door."), ("🧸", "teddy", "Teddy. A soft teddy to hug.")),
     "together": "After each one, point to the real one in your home.",
     "after": "Walk around the house and let them show you the bed, a chair and a spoon."},
    {"id": "vehicles", "area": "words", "title": "Things that go", "pic": "🚌", "kind": "name",
     "items": _n(("🚌", "bus", "Bus. A big bus with many people."), ("🛺", "auto", "Auto. The auto goes put put put."), ("🚲", "cycle", "Cycle. Ring the bell, tring tring."),
                 ("🚂", "train", "Train. Choo choo, a long train."), ("⛵", "boat", "Boat. The boat floats on water.")),
     "together": "Make each one's sound together. Which one have they ridden in?",
     "after": "On your next walk, count the autos and buses you see together."},
    # --- Colours and shapes
    {"id": "find-colours", "area": "colours", "title": "Find the colour", "pic": "🔴", "kind": "find",
     "rounds": _f(("Find the red one", [("🔴", "red"), ("🔵", "blue"), ("🟡", "yellow")], 0),
                  ("Find the yellow one", [("🟢", "green"), ("🟡", "yellow"), ("🔴", "red")], 1),
                  ("Find the blue one", [("🟡", "yellow"), ("🟢", "green"), ("🔵", "blue")], 2),
                  ("Find the green one", [("🟢", "green"), ("🔴", "red"), ("🔵", "blue")], 0)),
     "together": "Before they tap, ask them to point to something that colour in the room.",
     "after": "Play 'I spy something red' around the house."},
    {"id": "find-shapes", "area": "colours", "title": "Find the shape", "pic": "🔺", "kind": "find",
     "rounds": _f(("Find the circle", [("⚪", "circle"), ("🔺", "triangle"), ("⬜", "square")], 0),
                  ("Find the square", [("🔺", "triangle"), ("⬜", "square"), ("⚪", "circle")], 1),
                  ("Find the triangle", [("⬜", "square"), ("⚪", "circle"), ("🔺", "triangle")], 2),
                  ("Find the star", [("⭐", "star"), ("⚪", "circle"), ("🔺", "triangle")], 0)),
     "together": "Draw each shape in the air with your finger together.",
     "after": "Find round things at home: a plate, a coin, a roti."},
    {"id": "colour-fruits", "area": "colours", "title": "What colour is it?", "pic": "🍋", "kind": "find",
     "rounds": _f(("Find the yellow fruit", [("🍋", "lemon"), ("🍇", "grapes"), ("🍓", "strawberry")], 0),
                  ("Find the red fruit", [("🍌", "banana"), ("🍓", "strawberry"), ("🍐", "pear")], 1),
                  ("Find the green vegetable", [("🥕", "carrot"), ("🍅", "tomato"), ("🥦", "broccoli")], 2),
                  ("Find the orange one", [("🥕", "carrot"), ("🍆", "brinjal"), ("🥒", "cucumber")], 0)),
     "together": "Name the colour and the food together: a yellow lemon, a red strawberry.",
     "after": "In the kitchen, sort a few vegetables by colour together."},
    # --- Counting
    {"id": "count-to-three", "area": "counting", "title": "Count to three", "pic": "🍎", "kind": "count",
     "rounds": _c(("🍎", "apples", 1), ("🐟", "fish", 2), ("🌸", "flowers", 3), ("🦆", "ducks", 2)),
     "together": "Count out loud together, touching each one.",
     "after": "Count the steps as you climb them together: one, two, three."},
    {"id": "count-to-five", "area": "counting", "title": "Count to five", "pic": "🎈", "kind": "count",
     "rounds": _c(("🎈", "balloons", 3), ("🐥", "chicks", 4), ("⭐", "stars", 5), ("🥥", "coconuts", 4)),
     "together": "Hold up one finger for each one you count.",
     "after": "Count spoons or plates when you set the table together."},
    {"id": "count-animals", "area": "counting", "title": "How many animals?", "pic": "🐘", "kind": "count",
     "rounds": _c(("🐘", "elephants", 2), ("🐒", "monkeys", 3), ("🦜", "parrots", 1), ("🐢", "turtles", 4)),
     "together": "Make the animal sound once for each one you count.",
     "after": "Line up toys and count them together."},
    # --- Same and different
    {"id": "find-same", "area": "same", "title": "Find the same one", "pic": "🐶", "kind": "find",
     "rounds": _f(("Find another dog 🐶", [("🐱", "cat"), ("🐶", "dog"), ("🐟", "fish")], 1),
                  ("Find another ball ⚽", [("⚽", "ball"), ("🧸", "teddy"), ("🚗", "car")], 0),
                  ("Find another flower 🌼", [("🍃", "leaf"), ("🍄", "mushroom"), ("🌼", "flower")], 2),
                  ("Find another moon 🌙", [("🌙", "moon"), ("☀️", "sun"), ("⭐", "star")], 0)),
     "together": "Ask: how do you know they're the same?",
     "after": "Pair up socks from the washing together."},
    {"id": "big-small", "area": "same", "title": "Big and small", "pic": "🐘", "kind": "find",
     "rounds": _f(("Find the big animal", [("🐁", "mouse"), ("🐘", "elephant"), ("🐜", "ant")], 1),
                  ("Find the small animal", [("🐜", "ant"), ("🦒", "giraffe"), ("🐋", "whale")], 0),
                  ("Find the big one", [("🏠", "house"), ("🔑", "key"), ("🥄", "spoon")], 0),
                  ("Find the small one", [("🚌", "bus"), ("🌳", "tree"), ("🐞", "ladybird")], 2)),
     "together": "Show big with your arms wide and small with two fingers.",
     "after": "Find something big and something small in the house."},
    {"id": "odd-one", "area": "same", "title": "Which one is different?", "pic": "🍌", "kind": "find",
     "rounds": _f(("Which one is not a fruit?", [("🍌", "banana"), ("🚗", "car"), ("🍎", "apple")], 1),
                  ("Which one is not an animal?", [("🐄", "cow"), ("🐕", "dog"), ("🪑", "chair")], 2),
                  ("Which one does not fly?", [("🐟", "fish"), ("🐦", "bird"), ("🦋", "butterfly")], 0)),
     "together": "Ask why that one is different. Any reason they give is a good start.",
     "after": "Put a spoon, a cup and a toy together, and ask which one you can't eat with."},
    # --- Feelings
    {"id": "faces", "area": "feelings", "title": "How do they feel?", "pic": "😊", "kind": "name",
     "items": _n(("😊", "happy", "Happy. A big smile."), ("😢", "sad", "Sad. Tears are okay."), ("😠", "cross", "Cross. Take a big breath."),
                 ("😮", "surprised", "Surprised. Oh!"), ("😴", "sleepy", "Sleepy. Time to rest.")),
     "together": "Make each face together in a mirror or at each other.",
     "after": "At bedtime, ask: what made you happy today?"},
    {"id": "find-feeling", "area": "feelings", "title": "Find the feeling", "pic": "😢", "kind": "find",
     "rounds": _f(("Find the happy face", [("😢", "sad"), ("😊", "happy"), ("😴", "sleepy")], 1),
                  ("Find the sleepy face", [("😴", "sleepy"), ("😮", "surprised"), ("😊", "happy")], 0),
                  ("Find the sad face", [("😠", "cross"), ("😊", "happy"), ("😢", "sad")], 2)),
     "together": "Ask what makes them feel happy, and what helps when they're sad.",
     "after": "When they feel cross today, name it for them: 'you feel cross'."},
    # --- The world around us
    {"id": "weather", "area": "world", "title": "Sun and rain", "pic": "🌧️", "kind": "name",
     "items": _n(("☀️", "sun", "Sun. Bright and warm."), ("🌧️", "rain", "Rain. Pitter patter."), ("🌈", "rainbow", "Rainbow. So many colours."),
                 ("🌙", "moon", "Moon. We see it at night."), ("☁️", "cloud", "Cloud. Soft and grey.")),
     "together": "Look out of the window together. What's the weather now?",
     "after": "Next time it rains, listen to the sound together at the window."},
    {"id": "garden", "area": "world", "title": "In the garden", "pic": "🌻", "kind": "name",
     "items": _n(("🌳", "tree", "Tree. Tall with green leaves."), ("🌻", "flower", "Flower. It smells nice."), ("🐛", "caterpillar", "Caterpillar. Slow and wiggly."),
                 ("🐝", "bee", "Bee. Buzz buzz."), ("🐌", "snail", "Snail. Very, very slow.")),
     "together": "Move like each one: tall like a tree, slow like a snail.",
     "after": "Go outside and find a leaf, a flower and a stone together."},
    {"id": "find-sky", "area": "world", "title": "Up in the sky", "pic": "✈️", "kind": "find",
     "rounds": _f(("What flies in the sky?", [("✈️", "aeroplane"), ("🚗", "car"), ("🐟", "fish")], 0),
                  ("What lives in water?", [("🐦", "bird"), ("🐟", "fish"), ("🐄", "cow")], 1),
                  ("What do we see at night?", [("☀️", "sun"), ("🌈", "rainbow"), ("🌙", "moon")], 2)),
     "together": "Ask where else they have seen each one.",
     "after": "Look at the sky together tonight and find the moon."},
]

BY_ID = {a["id"]: a for a in ACTIVITIES}


def card(a: dict) -> dict:
    return {"id": a["id"], "area": a["area"], "title": a["title"], "pic": a["pic"], "kind": a["kind"]}
