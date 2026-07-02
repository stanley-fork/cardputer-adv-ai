"""Hand-written kindergarten Q&A material for the chat fine-tune.

Two skills are taught from here:
  1. Answerable facts — things a 3M-param model can actually memorize
     (colors, animal sounds, opposites, ...). Questions and answers are
     generated from hand-written templates over hand-written fact tables.
  2. Graceful failure — deflection replies paired (in prepare_chat_data.py)
     with questions the model cannot answer, plus "meta honesty" exchanges.

Everything in this file is human-written; no LLM-generated text. The
vocabulary deliberately sticks to TinyStories-level English so the samples
pass the corpus OOV filter and don't inflate the pruned vocab.
"""

COLORS = [
    ("sky", "blue"), ("sea", "blue"), ("grass", "green"), ("leaf", "green"),
    ("frog", "green"), ("snow", "white"), ("milk", "white"), ("cloud", "white"),
    ("sun", "yellow"), ("banana", "yellow"), ("lemon", "yellow"),
    ("apple", "red"), ("tomato", "red"), ("fire truck", "red"),
    ("carrot", "orange"), ("pumpkin", "orange"), ("pig", "pink"),
    ("chocolate", "brown"), ("bear", "brown"), ("crow", "black"),
    ("night sky", "dark"), ("zebra", "black and white"),
    ("panda", "black and white"),
]

SOUNDS = [
    ("dog", "woof"), ("cat", "meow"), ("cow", "moo"), ("duck", "quack"),
    ("sheep", "baa"), ("pig", "oink"), ("horse", "neigh"), ("bee", "buzz"),
    ("lion", "roar"), ("bird", "tweet"), ("frog", "ribbit"),
    ("owl", "hoo"), ("snake", "hiss"), ("mouse", "squeak"),
]

LEGS = [
    ("dog", "four"), ("cat", "four"), ("cow", "four"), ("horse", "four"),
    ("bird", "two"), ("chicken", "two"), ("duck", "two"),
    ("spider", "eight"), ("ant", "six"), ("bee", "six"),
]

BABIES = [
    ("dog", "puppy"), ("cat", "kitten"), ("cow", "calf"), ("horse", "foal"),
    ("sheep", "lamb"), ("hen", "chick"), ("frog", "tadpole"),
    ("bear", "cub"), ("duck", "duckling"), ("pig", "piglet"),
]

HOMES = [
    ("bee", "in a hive"), ("bird", "in a nest"), ("fish", "in the water"),
    ("rabbit", "in a hole in the ground"), ("spider", "in a web"),
    ("bear", "in a cave"), ("dog", "in a dog house"),
    ("ant", "under the ground"), ("frog", "by the pond"),
]

OPPOSITES = [
    ("hot", "cold"), ("big", "small"), ("up", "down"), ("fast", "slow"),
    ("happy", "sad"), ("day", "night"), ("wet", "dry"), ("light", "dark"),
    ("open", "closed"), ("loud", "quiet"), ("soft", "hard"),
    ("tall", "short"), ("full", "empty"), ("clean", "dirty"),
    ("old", "new"), ("near", "far"), ("first", "last"), ("good", "bad"),
]

# One-off (question, answer) pairs that don't fit a table.
GENERAL = [
    ("What do bees make?", "Bees make honey."),
    ("What do cows give us?", "Cows give us milk."),
    ("What do hens give us?", "Hens give us eggs."),
    ("Where do fish live?", "Fish live in the water."),
    ("What is rain made of?", "Rain is made of water."),
    ("Is fire hot or cold?", "Fire is very hot. Do not touch it!"),
    ("Is ice hot or cold?", "Ice is very cold."),
    ("Is snow hot or cold?", "Snow is cold. Brr!"),
    ("How many days are in a week?", "There are seven days in a week."),
    ("What do birds use to fly?", "Birds use their wings to fly."),
    ("Where does the sun go at night?",
     "The sun goes down at night, and the moon comes up."),
    ("What comes after night?", "The day comes after night. The sun comes up!"),
    ("What do you wear on your feet?", "You wear shoes on your feet."),
    ("What do you wear on your head?", "You wear a hat on your head."),
    ("What do we use an umbrella for?",
     "We use an umbrella to stay dry in the rain."),
    ("What do plants need to grow?",
     "Plants need water and sun to grow."),
    ("Where does an apple grow?", "An apple grows on a tree."),
    ("What do we do when we are sleepy?", "We go to bed and sleep."),
    ("What do we say when someone helps us?", "We say thank you!"),
    ("How many fingers do you have on one hand?",
     "You have five fingers on one hand."),
    ("What season is very cold with snow?", "Winter is very cold, with snow."),
    ("What season is very hot and sunny?", "Summer is very hot and sunny."),
    ("Can pigs fly?", "No, pigs can not fly! They have no wings."),
    ("Can fish walk?", "No, fish can not walk. They swim in the water."),
    ("Do cats like milk?", "Yes, cats love milk!"),
    ("What do you brush your teeth with?",
     "You brush your teeth with a tooth brush."),
    ("How many legs do you have?", "You have two legs."),
    ("What shines in the sky at night?",
     "The moon and the stars shine at night."),
    ("What do we drink when we are thirsty?",
     "We drink water when we are thirsty."),
    ("What do rabbits like to eat?", "Rabbits like to eat carrots."),
]

# "Meta honesty" — the bot knows it is small.
META = [
    ("Do you know everything?",
     "No! I am a very small bot. I know only a little."),
    ("Are you smart?", "I am just a little bot. I know some small things."),
    ("How much do you know?", "Only a little! I am a tiny bot."),
    ("Do you know a lot of things?",
     "No, I am small. I know little things, like colors and animals."),
    ("Can you answer anything?",
     "No, I can not. Big questions are too hard for me."),
]

# Replies for questions the model cannot answer. Paired in
# prepare_chat_data.py with hard (out-of-scope) questions.
DEFLECTIONS = [
    "I am not sure. I am just a little bot.",
    "I don't know that one, sorry!",
    "Hmm, that is a hard one. I don't know.",
    "I don't know. Can we talk about something fun instead?",
    "That is too hard for me. I am a small bot.",
    "I wish I knew, but I don't.",
    "Sorry, I don't know about that.",
    "I don't know that. I only know little things.",
    "That is a big question! I don't know.",
    "I can't answer that one. I am only a tiny bot.",
    "I don't know, sorry! Do you want to hear a story?",
    "Hmm, I don't know that one.",
    "I am too little to know that, sorry!",
    "I don't know! My head is very small.",
    "That one is too tricky for me, sorry.",
]

# --- Question / answer surface templates -----------------------------------

COLOR_Q = ["What color is the {x}?",
           "Do you know what color the {x} is?",
           "Tell me, what color is the {x}?"]
COLOR_A = ["The {x} is {y}.",
           "I know! The {x} is {y}.",
           "The {x} is {y}. I like {y}!"]

SOUND_Q = ["What sound does a {x} make?",
           "What does a {x} say?",
           "Do you know what a {x} says?"]
SOUND_A = ["A {x} says {y}!",
           "The {x} says {y}.",
           "{y}, {y}! That is what a {x} says."]

LEGS_Q = ["How many legs does a {x} have?",
          "Do you know how many legs a {x} has?"]
LEGS_A = ["A {x} has {y} legs.",
          "I know! A {x} has {y} legs."]

BABY_Q = ["What is a baby {x} called?",
          "What do you call a baby {x}?"]
BABY_A = ["A baby {x} is called a {y}.",
          "A {y}! A baby {x} is a {y}."]

HOME_Q = ["Where does a {x} live?",
          "Do you know where a {x} lives?"]
HOME_A = ["A {x} lives {y}.",
          "I know! A {x} lives {y}."]

OPP_Q = ["What is the opposite of {x}?",
         "Do you know the opposite of {x}?"]
OPP_A = ["The opposite of {x} is {y}.",
         "{y}! The opposite of {x} is {y}."]


def qa_pairs(rng):
    """All hand-templated (question, answer) pairs, shuffled.

    Each fact is expanded through every question template with a randomly
    chosen answer template, so the same fact shows up under a few surface
    forms — that's deliberate (we *want* these memorized).
    """
    pairs = []

    def expand(facts, qts, ats):
        for x, y in facts:
            for q in qts:
                a = rng.choice(ats).format(x=x, y=y)
                pairs.append((q.format(x=x, y=y), a[0].upper() + a[1:]))

    expand(COLORS, COLOR_Q, COLOR_A)
    expand(SOUNDS, SOUND_Q, SOUND_A)
    expand(LEGS, LEGS_Q, LEGS_A)
    expand(BABIES, BABY_Q, BABY_A)
    expand(HOMES, HOME_Q, HOME_A)
    opp_both = OPPOSITES + [(b, a) for a, b in OPPOSITES]
    expand(opp_both, OPP_Q, OPP_A)
    pairs.extend(GENERAL)
    pairs.extend(META)
    rng.shuffle(pairs)
    return pairs
