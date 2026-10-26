"""The game layer: buddies, monsters, coins, the shop, combos and the daily challenge.

None of this changes how the AI judges a quest. It changes how a quest feels: every
quest is a boss battle, right answers are attacks, and coins buy gear for your buddy.
"""
import random
from datetime import date

from .questions import SUBJECTS

BUDDIES = {
    "robo": {"name": "Robo", "kind": "robot", "line": "Beep boop! I love crunching numbers.",
             "power": "Laser stars"},
    "hoot": {"name": "Hoot", "kind": "owl", "line": "Hoo-hoo! Every question is a new adventure.",
             "power": "Feather darts"},
    "blaze": {"name": "Blaze", "kind": "dragon", "line": "Rawr! Let's turn up the brain heat.",
              "power": "Fire puffs"},
}
DEFAULT_BUDDY = "robo"

# code: (slot, name, price)
ITEMS = {
    "bowtie": ("neck", "Bow tie", 30),
    "party_hat": ("head", "Party hat", 40),
    "shades": ("face", "Cool shades", 60),
    "scarf": ("neck", "Cosy scarf", 70),
    "monocle": ("face", "Monocle", 90),
    "wizard_hat": ("head", "Wizard hat", 120),
    "cape": ("back", "Hero cape", 150),
    "jetpack": ("back", "Jetpack", 200),
    "crown": ("head", "Golden crown", 250),
}
SLOTS = ("back", "neck", "face", "head")

MONSTERS = {
    "Mathematics": {"id": "golem", "name": "Number Golem", "lair": "Calculation Caves"},
    "English": {"id": "gremlin", "name": "Grammar Gremlin", "lair": "Library of Riddles"},
    "Computer Science": {"id": "bug", "name": "Bug Beast", "lair": "Glitch Galaxy"},
}

COINS_FIRST_TRY = 3
COINS_SECOND_TRY = 1
BOSS_BONUS = 10
DAILY_COIN_MULTIPLIER = 2
DAILY_XP = 25
COMBO_START = 3          # combo bonus from the 3rd right-first-time answer in a row
COMBO_XP = 3
MAP_STOPS = 10

LINES = {
    "start": ["A wild {monster} appears! Let's do this!", "The {monster} blocks the path. Ready?",
              "Five questions stand between us and the {monster}!"],
    "hit": ["Boom! Direct hit!", "Nailed it! Take that, {monster}!", "You're on fire!",
            "Super smart move!", "Bullseye! Keep going!"],
    "hit_retry": ["Got it! Teamwork!", "Never give up, that's the spirit!", "Second try, still a hit!"],
    "miss": ["Oof! We'll get the next one.", "Mistakes help our brains grow!", "Shake it off, hero!"],
    "oops": ["Hmm, not that one. Try again!", "Close! Think it through once more.",
             "Look for a clue in the question."],
    "hint": ["Here's a clue!", "Psst… try this!", "A little help never hurts."],
    "win": ["We beat the {monster}! High five!", "Victory dance time!"],
    "escape": ["The {monster} ran away… we'll catch it next time!", "So close! Let's train and try again."],
}


def say(event, seed, **names):
    options = LINES[event]
    return random.Random(seed).choice(options).format(**names)


def daily_subject(day=None):
    day = day or date.today()
    return list(SUBJECTS)[day.toordinal() % len(SUBJECTS)]


def combo_series(items):
    """Combo after each answer: right first time adds one, anything else resets it."""
    combo, out = 0, []
    for it in items:
        combo = combo + 1 if it["correct"] and it["tries"] == 1 else 0
        out.append(combo)
    return out


def combo_xp(items):
    return sum(COMBO_XP for c in combo_series(items) if c >= COMBO_START)


def hits(items):
    return sum(1 for it in items if it["correct"])


def quest_coins(items, defeated, daily):
    coins = sum(COINS_FIRST_TRY if it["tries"] == 1 else COINS_SECOND_TRY for it in items if it["correct"])
    coins += BOSS_BONUS if defeated else 0
    return coins * (DAILY_COIN_MULTIPLIER if daily else 1)


def stage_for(level):
    """Buddies evolve: an aura at level 3 and a star at level 6."""
    return 3 if level >= 6 else 2 if level >= 3 else 1


def map_path(count, width=300, height=74):
    """Ten stops along a winding path, for the adventure map of one subject."""
    chapter, done = count // MAP_STOPS + 1, count % MAP_STOPS
    stops = []
    for i in range(MAP_STOPS):
        x = 16 + i * (width - 32) / (MAP_STOPS - 1)
        y = height / 2 + (18 if i % 2 else -18) * (1 if (i // 2) % 2 == 0 else 0.6)
        stops.append({"x": round(x, 1), "y": round(y, 1), "done": i < done, "next": i == done, "boss": i == MAP_STOPS - 1})
    return {"chapter": chapter, "done": done, "stops": stops,
            "points": " ".join(f"{s['x']},{s['y']}" for s in stops)}


def owned(conn, student_id):
    return {r["item"]: bool(r["equipped"]) for r in
            conn.execute("SELECT item, equipped FROM inventory WHERE student_id = ?", (student_id,))}


def equipped(conn, student_id):
    gear = {}
    for item, on in owned(conn, student_id).items():
        if on and item in ITEMS:
            gear[ITEMS[item][0]] = item
    return gear
