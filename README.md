# EduQuest AI: AI-Powered Gamified Learning Platform

![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3-black?logo=flask)
![scikit-learn](https://img.shields.io/badge/scikit--learn-training-orange)
![Model](https://img.shields.io/badge/Model-Logistic%20Regression-brightgreen)
![CV accuracy](https://img.shields.io/badge/CV%20accuracy-95%25-brightgreen)
![License](https://img.shields.io/badge/License-FCCU-yellow)

## 🎯 Quick Links
- 🚀 [Run it](#-run-it)
- 🎮 [How a quest works](#-how-a-quest-works)
- 🤖 [The AI](#-the-ai)
- 🔐 [Security and privacy](#-security-and-privacy)
- 📁 [Project layout](#-project-layout)

---

## Project Contributors
* **Amzi Asif** (ID: 281133626)
* **Musfira Sehar** (ID: 280048443)

**Institution:** Forman Christian College University (FCCU)
**Course:** Introduction to Artificial Intelligence

---

## Project Overview and Vision
Traditional educational platforms often apply a rigid, one-size-fits-all approach that fails to align with an individual student's unique learning pace. This frequently results in early disengagement or cognitive overload, particularly for younger learners in Grades 3–7.

EduQuest AI treats what a student actually does in the app as behavioral telemetry. A machine-learning model estimates their engagement after every quest, and the next quest adapts: more help for students who are struggling, harder challenges for students who are flying.

## ⚡ Features at a Glance
- ✅ **Real quests**: five-question quests in Mathematics, English and Computer Science, pitched at grades 3 to 7
- ✅ **Measured, not typed**: score, hints, tries, time, streak and completion are recorded by the server while the student plays
- ✅ **Adaptive difficulty**: an Elo-style rating per subject picks each next question
- ✅ **Three tiers that change the game**: Launchpad (Bronze), Steady (Silver) and Challenge (Gold)
- ✅ **Explainable results**: what counted toward the tier, the shortest path to the next one, and what the AI noticed
- ✅ **XP, levels, streaks and 12 badges**, with extra reward for effort at the lowest tier
- ✅ **Animated buddies**: pick Robo the robot, Hoot the owl or Blaze the dragon. They blink, bob, cheer, sulk, think and dance, talk in speech bubbles, and grow an aura (level 3) and sparkles (level 6)
- ✅ **Boss battles**: every quest is a fight against the Number Golem, the Grammar Gremlin or the Bug Beast. Right answers are attacks that knock off one of five hearts; get all five for a KO
- ✅ **Combos, coins and a buddy shop**: answers right in a row build a combo, and coins (3 per answer, 10 per boss) buy hats, shades, a cape or a jetpack in four gear slots
- ✅ **Daily challenge and adventure map**: one subject a day pays double coins and +25 XP, and each subject has a 10-stop map with a boss castle
- ✅ **8-bit sound effects** synthesised in the browser (with a remembered mute button) and drifting clouds; all motion respects reduced-motion settings
- ✅ **Kid-friendly sign-in** with a picture password, plus download-my-data and delete-my-account controls
- ✅ **Accessible**: works without JavaScript, keyboard play (1–4, then Enter), read-aloud questions, reduced-motion support

---

## 🚀 Run it

```bash
git clone https://github.com/MoNsT3R-code/EduQuest-AI-Platform.git
cd EduQuest-AI-Platform
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000, choose **I'm new here**, and pick three secret pictures.

| Setting | Default | What it does |
| --- | --- | --- |
| `EDUQUEST_SECRET_KEY` | random, saved in `instance/secret_key` | Signs the session cookie. Set it in any shared deployment. |
| `EDUQUEST_HTTPS` | off | Set to `1` behind HTTPS: secure cookies and HSTS. |
| `FLASK_DEBUG` | off | Set to `1` for the debugger. Never in production. |

The database (`instance/eduquest.db`) and the secret key are created on first run and are git-ignored.

**Tests:** `python -m pytest`
**Retrain the model:** `python scripts/train_model.py` (rewrites `models/engagement_model.json`)

---

## 🎮 How a quest works

1. The student picks a subject. The quest's **mode** comes from their last tier in that subject:

   | Tier | Mode | What changes |
   | --- | --- | --- |
   | 🥉 Bronze Beginner | **Launchpad** | No timer, two hints per question (a clue, then a 50:50), questions aimed at ~80% success |
   | 🥈 Silver Star | **Steady** | One hint, timer shown, ~70% success |
   | 🏆 Gold Scholar | **Challenge** | One hint, timer, harder questions aimed at ~55% success |

2. Each question is chosen **one at a time** for the student's current rating. Right first time is full credit, right on the second try is half, and the answer is explained either way. Mathematics questions are generated, so numbers scale with the grade and never run out.
3. At the end, the server turns the quest into the model's six inputs, predicts the tier, awards XP and badges, and shows a results page that explains the decision.

## 🤖 The AI

### Dataset and labels
`student_data.csv` holds 200 synthetic student records (seed 42) built in `Notebook.ipynb`. Each record is labelled by a weighted composite score:

S = 0.4·quiz score + 0.3·assignments completed + 0.2·streak (out of 30 days) + 0.1·time (out of 10 hours)

* **High:** S > 65  · **Medium:** 50 < S ≤ 65  · **Low:** S ≤ 50

### What the app feeds the model
| Model input | Measured in the app as |
| --- | --- |
| `quiz_score` | score in the quest just finished |
| `time_spent_hrs` | time answering finished quests in the last 30 days (idle time over 5 minutes per question ignored) |
| `attempts` | quests finished in this subject in the last 30 days (1–5) |
| `hints_used` | hints taken in this quest |
| `streak_days` | consecutive days, up to today, with a finished quest |
| `assignments_completed` | share of quests started in the last 30 days that were finished |

### Model choice
Because the labels are a weighted sum, a linear model fits them far better than trees. `scripts/train_model.py` compares candidates with 5-fold stratified cross-validation:

| Model | CV accuracy |
| --- | --- |
| Random Forest (original notebook) | 78.5% ± 8.0 |
| Gradient Boosting | 80.5% ± 6.0 |
| **Logistic Regression (C=100), used** | **95.0% ± 4.2** |

On the notebook's own 80/20 split the logistic regression scores **90.0%**, against 72.5% for the Random Forest.

The model ships as **plain JSON weights** (`models/engagement_model.json`) rather than a pickle, so a tampered model file can never execute code. The file also carries the comparison, hold-out metrics and confusion matrix, which the in-app **How the AI works** page displays.

### Explanations
Every result page shows:
* **What counts toward your tier:** the four parts of S, with the Bronze, Silver and Gold zones
* **Your path to the next tier:** the smallest single changes that would cross the threshold (for example "Play 2 more days in a row")
* **What the AI noticed:** which inputs pushed toward the predicted tier, the probability for each tier, and a note when the student is near a boundary or the model is unsure

### Limits
The training data is synthetic, so a tier is a nudge for the next quest, never a grade. Grade level is not an input to the model.

---

## 🔐 Security and privacy
* **CSRF tokens** on every form, and a strict **Content Security Policy** (no inline scripts or styles), plus `X-Frame-Options`, `nosniff`, `Referrer-Policy`, `Permissions-Policy` and `no-store` caching on pages
* **Picture passwords hashed** with Werkzeug (scrypt), a fresh session on sign-in, `HttpOnly` and `SameSite=Lax` cookies with an 8-hour lifetime, and rate limits (5 wrong tries per name, 20 per device, per 10 minutes)
* **Answers stay on the server** until a question is answered, double submits count once, and students can only open their own quests
* **No pickle loading**, debug mode off by default, a generated secret key, and a 32 KB request size limit
* **Data minimisation:** first name, grade, hashed picture password and quest results only, with no IP addresses. Students (or parents) can **download** everything as JSON or **delete** their account from *My progress*
* `eduquest.db`, compiled `.pyc` files and pickles are no longer tracked in git

## 📁 Project layout
```
app.py                     entry point
eduquest/
  __init__.py              app factory, error pages
  db.py                    SQLite, foreign keys, versioned migrations
  security.py              CSRF, security headers, secret key, rate limiter
  auth.py                  picture-password sign-in
  quests.py                quest engine: serving, answers, hints, finishing
  questions.py             question bank and Mathematics generator
  gamify.py                XP, levels, badges
  dashboard.py             progress, About the AI, export and delete
  ai/model.py              JSON logistic-regression model and explanations
  ai/features.py           real activity → model inputs
  ai/coach.py              tier formula, next-tier path, tips
  ai/adaptive.py           Elo-style adaptive difficulty
  templates/, static/      pages, styles, small progressive-enhancement script
models/engagement_model.json
scripts/train_model.py
tests/                     pytest suite
Notebook.ipynb, student_data.csv, *.png   original analysis
```
