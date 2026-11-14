"""Adaptive difficulty with an Elo rating per student and subject.

Each answer moves the student's rating toward the question's: a hard question answered
well raises it a lot, an easy one missed lowers it. The next question is the difficulty
the student is most likely to get right about TARGET of the time, so it stays hard
enough to learn from but easy enough to keep going.
"""
START = 1000.0
K = 32
K_NEW = 96          # a new student's rating moves faster until it has seen enough answers
NEW_ANSWERS = 10
QUESTION_RATING = {1: 850.0, 2: 1000.0, 3: 1150.0}
TARGET = {"Launchpad": 0.8, "Steady": 0.7, "Challenge": 0.55}


def expected(rating, difficulty):
    return 1 / (1 + 10 ** ((QUESTION_RATING[difficulty] - rating) / 400))


def update(rating, difficulty, credit, answers=NEW_ANSWERS):
    """credit is 1 for right first time, 0.5 for right on the second try, 0 for missed."""
    k = K_NEW if answers < NEW_ANSWERS else K
    return rating + k * (credit - expected(rating, difficulty))


def pick_difficulty(rating, mode):
    target = TARGET.get(mode, 0.7)
    return min(QUESTION_RATING, key=lambda d: abs(expected(rating, d) - target))
