"""Questions for each subject, grade (3 to 7) and difficulty (1 easy, 2 medium, 3 hard).

Mathematics is generated, so a student never runs out and numbers grow with the grade.
English and Computer Science come from a written bank.
"""
import random
from dataclasses import dataclass, field

SUBJECTS = {
    "Mathematics": {"emoji": "📐", "blurb": "Numbers, shapes and word problems"},
    "English": {"emoji": "📖", "blurb": "Words, grammar and reading"},
    "Computer Science": {"emoji": "💻", "blurb": "Logic, code and staying safe online"},
}


@dataclass
class Question:
    skill: str
    difficulty: int
    prompt: str
    options: list
    answer: int
    hint: str
    explanation: str = ""
    key: str = field(default="")


def _options(rng, correct, wrong):
    """Shuffle the right answer in with three distinct wrong ones."""
    seen, picks = {str(correct)}, []
    for w in wrong:
        if str(w) not in seen:
            seen.add(str(w))
            picks.append(str(w))
        if len(picks) == 3:
            break
    step = 1
    while len(picks) < 3 and isinstance(correct, int):
        # Too few distinct wrong answers: fall back to neighbouring numbers
        for v in (correct + step, correct - step):
            if v >= 0 and str(v) not in seen and len(picks) < 3:
                seen.add(str(v))
                picks.append(str(v))
        step += 1
    opts = [str(correct)] + picks
    rng.shuffle(opts)
    return opts, opts.index(str(correct))


def _near(rng, n, spread, positive=True):
    out = []
    while len(out) < 6:
        d = rng.randint(1, max(2, spread))
        for v in (n + d, n - d):
            if (v > 0 or not positive) and v != n:
                out.append(v)
    rng.shuffle(out)
    return out


# ── Mathematics ──────────────────────────────────────────────

def _math_arithmetic(rng, grade):
    top = {3: 100, 4: 500, 5: 1000, 6: 5000, 7: 10000}[grade]
    a, b = rng.randint(top // 10, top // 2), rng.randint(top // 20, top // 2)
    if rng.random() < 0.5:
        ans = a + b
        return "addition", f"What is {a} + {b}?", ans, _near(rng, ans, 12) + [ans + 10, ans - 10], \
            "Add the ones first, then the tens, and carry when a column goes over 9.", f"{a} + {b} = {ans}"
    a, b = max(a, b), min(a, b)
    ans = a - b
    return "subtraction", f"What is {a} − {b}?", ans, _near(rng, ans, 12) + [a + b], \
        "Subtract column by column from the right. Borrow from the next column if you need to.", f"{a} − {b} = {ans}"


def _math_times(rng, grade):
    if grade <= 4 or rng.random() < 0.5:
        a, b = rng.randint(2, 12 if grade >= 4 else 10), rng.randint(2, 10)
    else:
        a, b = rng.randint(12, 25 + grade * 5), rng.randint(3, 9)
    if rng.random() < 0.5:
        ans = a * b
        return "multiplication", f"What is {a} × {b}?", ans, [ans + a, ans - b, ans + b, a + b, ans + 10], \
            f"Think of {b} groups of {a}. You can add {a} again and again.", f"{a} × {b} = {ans}"
    total = a * b
    return "division", f"What is {total} ÷ {b}?", a, [a + 1, a - 1, b, a + 2, a * 2], \
        f"Ask yourself: {b} times what makes {total}?", f"{total} ÷ {b} = {a} because {b} × {a} = {total}"


def _math_word(rng, grade):
    kind = rng.choice(["money", "shape"] if grade <= 4 else ["money", "fraction", "percent"] if grade >= 6 else ["money", "fraction", "shape"])
    if kind == "money":
        price, n = rng.randint(2, 9) * 10, rng.randint(3, 6 + grade)
        paid = (price * n // 100 + 1) * 100
        ans = paid - price * n
        return "word problems", (f"A notebook costs Rs {price}. Sara buys {n} notebooks and pays with Rs {paid}. "
                                 f"How much change does she get?"), ans, [price * n, ans + price, ans - 10 if ans > 10 else ans + 20, paid - price], \
            "First find the total cost (price × number of notebooks), then take it away from what she paid.", \
            f"{n} × {price} = {price * n}, and {paid} − {price * n} = {ans}"
    if kind == "shape":
        w, h = rng.randint(3, 12), rng.randint(2, 9)
        if rng.random() < 0.5:
            ans = 2 * (w + h)
            return "perimeter", f"A rectangle is {w} cm long and {h} cm wide. What is its perimeter in cm?", ans, \
                [w * h, w + h, ans + 2, ans - 2], "Perimeter is the distance all the way around: add all four sides.", \
                f"{w} + {h} + {w} + {h} = {ans} cm"
        ans = w * h
        return "area", f"A rectangle is {w} cm long and {h} cm wide. What is its area in square cm?", ans, \
            [2 * (w + h), w + h, ans + w, ans - h], "Area is length × width.", f"{w} × {h} = {ans} square cm"
    if kind == "fraction":
        d = rng.choice([2, 3, 4, 5, 10])
        n = rng.randint(1, d - 1)
        whole = d * rng.randint(3, 12)
        ans = whole // d * n
        return "fractions", f"What is {n}/{d} of {whole}?", ans, [whole // d, ans + whole // d, whole - ans, ans + n], \
            f"Split {whole} into {d} equal parts, then take {n} of those parts.", f"{whole} ÷ {d} = {whole // d}, and × {n} = {ans}"
    p = rng.choice([10, 20, 25, 50, 75])
    whole = rng.choice([40, 80, 120, 200, 400])
    ans = whole * p // 100
    return "percentages", f"What is {p}% of {whole}?", ans, [p, whole - ans, ans * 2, ans + 10], \
        "Percent means 'out of 100'. 10% is a tenth, 25% is a quarter, 50% is half.", f"{p}% of {whole} = {ans}"


def math_question(rng, grade, difficulty):
    maker = {1: _math_arithmetic, 2: _math_times, 3: _math_word}[difficulty]
    skill, prompt, ans, wrong, hint, explanation = maker(rng, grade)
    options, answer = _options(rng, ans, [w for w in wrong if isinstance(w, int) and w >= 0])
    return Question(skill, difficulty, prompt, options, answer, hint, explanation, key=prompt)


# ── Written banks: (min grade, difficulty, skill, prompt, right answer, wrong answers, hint, explanation) ──

ENGLISH = [
    (3, 1, "vocabulary", "Which word means the opposite of 'hot'?", "cold", ["warm", "sunny", "spicy"], "Think of ice cream in the freezer.", "Hot and cold are opposites."),
    (3, 1, "spelling", "Which word is spelled correctly?", "because", ["becuase", "becaus", "beacause"], "Sound it out: be-cause.", "'Because' is be + cause."),
    (3, 1, "grammar", "Choose the right word: 'The cats ___ sleeping.'", "are", ["is", "am", "be"], "There is more than one cat.", "More than one → 'are'."),
    (3, 1, "punctuation", "Which sentence ends correctly?", "Where is my bag?", ["Where is my bag.", "Where is my bag!", "Where is my bag,"], "Is it asking something?", "Questions end with a question mark."),
    (3, 1, "nouns", "Which word is a noun (a person, place or thing)?", "garden", ["quickly", "jump", "happy"], "Can you touch it or visit it?", "A garden is a place, so it's a noun."),
    (4, 1, "vocabulary", "What does 'enormous' mean?", "very big", ["very small", "very fast", "very old"], "An elephant is enormous.", "Enormous means huge."),
    (3, 1, "plurals", "What is the plural of 'child'?", "children", ["childs", "childes", "childrens"], "It's an irregular plural.", "One child, two children."),
    (4, 1, "synonyms", "Which word means the same as 'happy'?", "joyful", ["angry", "tired", "nervous"], "Think of a smiling face.", "Joyful and happy are synonyms."),
    (3, 2, "verbs", "Which word is a verb (an action)?", "swim", ["blue", "chair", "soft"], "Can you do it?", "Swimming is an action."),
    (4, 2, "past tense", "What is the past tense of 'run'?", "ran", ["runned", "runs", "running"], "Yesterday I ___ to school.", "'Run' becomes 'ran'."),
    (4, 2, "adjectives", "Which word describes a noun in 'The tall boy waved'?", "tall", ["boy", "waved", "the"], "Which word tells you what the boy is like?", "'Tall' is an adjective describing the boy."),
    (4, 2, "homophones", "Choose the right word: 'They left ___ bags here.'", "their", ["there", "they're", "thier"], "The bags belong to them.", "'Their' shows belonging."),
    (5, 2, "prefixes", "What does the prefix 'un-' do in 'unhappy'?", "means 'not'", ["means 'again'", "means 'before'", "means 'very'"], "Unhappy is the opposite of happy.", "'Un-' means not."),
    (5, 2, "reading", "'Ali grabbed his umbrella before leaving.' What is the weather probably like?", "rainy", ["sunny", "snowy", "windy"], "Why do we carry umbrellas?", "An umbrella suggests rain."),
    (5, 2, "conjunctions", "Which word best joins: 'I was tired, ___ I kept reading.'", "but", ["so", "because", "and then"], "The second part is a surprise.", "'But' shows contrast."),
    (6, 2, "apostrophes", "Which is correct for 'the toy belonging to the dog'?", "the dog's toy", ["the dogs toy", "the dogs' toy", "the dog toy's"], "One dog owns the toy.", "Singular owner: 's."),
    (5, 3, "figurative language", "'The wind whispered through the trees' is an example of…", "personification", ["a simile", "rhyme", "an exclamation"], "The wind is doing something a person does.", "Giving human actions to things is personification."),
    (6, 3, "similes", "Which sentence is a simile?", "She ran as fast as a cheetah.", ["She ran very fast.", "She is a cheetah.", "Cheetahs run fast."], "Look for 'like' or 'as'.", "Similes compare using 'like' or 'as'."),
    (6, 3, "vocabulary", "What does 'reluctant' mean?", "not willing", ["very excited", "quick", "careful"], "A reluctant swimmer doesn't want to jump in.", "Reluctant means unwilling."),
    (6, 3, "voice", "Which sentence is in the passive voice?", "The cake was eaten by Omar.", ["Omar ate the cake.", "Omar eats cake.", "Omar will eat the cake."], "Who does the action comes after 'by'.", "Passive: the object comes first, then 'was … by'."),
    (7, 3, "reading", "'Despite the storm, the match went ahead.' What does 'despite' tell us?", "the match happened even though it stormed", ["the match was cancelled", "the storm started after", "the storm helped"], "'Despite' means 'even though'.", "'Despite' introduces something that didn't stop the action."),
    (7, 3, "clauses", "In 'When the bell rang, we went home', which part is the main clause?", "we went home", ["When the bell rang", "the bell", "rang"], "Which part makes sense on its own?", "'We went home' is complete by itself."),
    (5, 3, "idioms", "What does 'a piece of cake' mean?", "very easy", ["very tasty", "a small part", "a birthday"], "It's not about food.", "The idiom means something is easy."),
    (7, 3, "word roots", "The root 'bio' means life. What is 'biology'?", "the study of living things", ["the study of rocks", "a life story", "a kind of medicine"], "'-logy' means 'the study of'.", "Bio (life) + logy (study)."),
]

COMPUTER_SCIENCE = [
    (3, 1, "algorithms", "What is an algorithm?", "a list of steps to solve a problem", ["a type of computer", "a computer virus", "a website"], "A recipe is one too!", "An algorithm is a set of step-by-step instructions."),
    (3, 1, "hardware", "Which of these is an input device?", "keyboard", ["monitor", "speaker", "printer"], "Which one do you use to give the computer information?", "A keyboard sends information into the computer."),
    (3, 1, "online safety", "A stranger online asks for your home address. What should you do?", "not share it and tell an adult", ["share it if they seem nice", "send a photo instead", "ask for theirs first"], "Keep personal information private.", "Never share personal details; tell a trusted adult."),
    (3, 1, "sequencing", "To brush your teeth, what comes right after 'put toothpaste on the brush'?", "brush your teeth", ["open the toothpaste", "rinse your mouth", "buy a toothbrush"], "Put the steps in order.", "Toothpaste on, then brush."),
    (4, 1, "hardware", "Which part is the computer's 'brain'?", "CPU", ["mouse", "screen", "USB cable"], "It does the thinking and calculating.", "The CPU (central processing unit) processes instructions."),
    (4, 1, "online safety", "Which is the strongest password?", "Tiger!Mango7Kite", ["123456", "password", "myname"], "Long passwords with mixed characters are hardest to guess.", "Mixing words, symbols and numbers makes it strong."),
    (3, 1, "debugging", "What is a 'bug' in a program?", "a mistake in the code", ["an insect in the computer", "a fast program", "a new feature"], "Programmers fix these.", "A bug is an error that makes a program behave wrongly."),
    (4, 1, "internet", "What does a web browser do?", "lets you visit websites", ["prints documents", "cools the computer", "stores electricity"], "Chrome and Edge are examples.", "Browsers open and show web pages."),
    (4, 2, "loops", "A robot runs 'repeat 4 times: move 2 steps'. How many steps does it move?", "8", ["4", "6", "2"], "Multiply the repeats by the steps.", "4 × 2 = 8 steps."),
    (4, 2, "conditionals", "'If it is raining, take an umbrella.' It is sunny. What happens?", "no umbrella is taken", ["an umbrella is taken", "it starts raining", "the program stops"], "The condition is false.", "The instruction only runs when the condition is true."),
    (5, 2, "binary", "In binary, what number is 101?", "5", ["101", "3", "6"], "Binary places are worth 4, 2 and 1.", "1×4 + 0×2 + 1×1 = 5."),
    (5, 2, "variables", "score = 10, then score = score + 5. What is score now?", "15", ["10", "5", "105"], "Take the old value and add 5.", "10 + 5 = 15."),
    (5, 2, "data", "Which is the best way to show how temperature changes over a week?", "a line graph", ["a pie chart", "a single number", "a password"], "You want to see change over time.", "Line graphs show change over time."),
    (5, 2, "online safety", "You get an email saying 'You won a prize! Click here and enter your password.' What is it?", "a phishing scam", ["a real prize", "a software update", "a school message"], "Real companies never ask for your password by email.", "This is phishing: it tries to steal your password."),
    (6, 2, "loops", "for i in 1 to 3: print(i * 2). What is printed?", "2 4 6", ["1 2 3", "2 3 4", "6"], "Work out i × 2 for i = 1, 2 and 3.", "1×2, 2×2, 3×2 → 2 4 6."),
    (6, 2, "networks", "What does Wi-Fi let a device do?", "connect to a network without cables", ["charge its battery", "print faster", "store more photos"], "'Wireless' is the clue.", "Wi-Fi is wireless networking."),
    (5, 3, "debugging", "This should add 1 to 5 to get 15, but prints 10: total = 0; for n in 1 to 4: total += n. What's wrong?", "the loop stops at 4 instead of 5", ["total should start at 1", "+= should be -=", "nothing is wrong"], "Check which numbers the loop visits.", "1+2+3+4 = 10; the loop must include 5."),
    (6, 3, "binary", "What is 13 in binary?", "1101", ["1011", "1110", "1001"], "13 = 8 + 4 + 1.", "8+4+0+1 → 1101."),
    (6, 3, "algorithms", "You look for a name in a sorted list of 1,000 by checking the middle and halving each time. About how many checks at most?", "10", ["500", "1000", "100"], "Count how many times you can halve 1,000.", "Binary search: 2¹⁰ ≈ 1,000, so about 10 checks."),
    (7, 3, "logic", "A = true, B = false. What is (A AND B) OR A?", "true", ["false", "both", "error"], "Work out the brackets first.", "(true AND false) = false; false OR true = true."),
    (7, 3, "data", "Why do apps store a hash of your password instead of the password itself?", "so a stolen database doesn't reveal passwords", ["to make login faster", "so passwords can be shared", "to save colours"], "Think about what happens if hackers copy the data.", "A hash can't easily be turned back into the password."),
    (7, 3, "AI", "An AI learns from examples. If every example cat photo is orange, what might go wrong?", "it may not recognise cats of other colours", ["it learns faster", "it becomes a dog detector", "nothing at all"], "The AI only knows what it has seen.", "Biased training data gives biased results."),
    (6, 3, "variables", "x = 3; y = x; x = 7. What is y?", "3", ["7", "10", "x"], "y copied x's value before it changed.", "y kept the value 3."),
    (7, 3, "networks", "What does HTTPS add to a website connection?", "encryption so others can't read it", ["more colours", "faster images", "free Wi-Fi"], "Look for the padlock in the address bar.", "HTTPS encrypts the data between you and the site."),
]

BANKS = {"English": ENGLISH, "Computer Science": COMPUTER_SCIENCE}


def bank_question(rng, subject, grade, difficulty, used):
    pool = [q for q in BANKS[subject] if q[0] <= grade and q[3] not in used]
    exact = [q for q in pool if q[1] == difficulty]
    near = sorted(pool, key=lambda q: abs(q[1] - difficulty))
    choice = rng.choice(exact) if exact else (near[0] if near else rng.choice(BANKS[subject]))
    _g, diff, skill, prompt, right, wrong, hint, explanation = choice
    options, answer = _options(rng, right, wrong)
    return Question(skill, diff, prompt, options, answer, hint, explanation, key=prompt)


def make_question(subject, grade, difficulty, used=(), rng=None):
    rng = rng or random.Random()
    if subject == "Mathematics":
        for _ in range(10):
            q = math_question(rng, grade, difficulty)
            if q.key not in used:
                return q
        return q
    return bank_question(rng, subject, grade, difficulty, set(used))
