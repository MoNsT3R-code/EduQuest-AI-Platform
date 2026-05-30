from flask import Flask, render_template, request, redirect, url_for, session
import numpy as np
import joblib
from database import init_db, save_student, log_login, save_performance, get_student_history, get_student

app = Flask(__name__)
app.secret_key = "eduquest_secret_key"

model = joblib.load("model.pkl")
le = joblib.load("label_encoder.pkl")

init_db()

subject_recs = {
    "Mathematics": {
        "High": "Excellent in Math! Try advanced problem sets and help peers with difficult concepts.",
        "Medium": "Good progress in Math! Practice more word problems and timed exercises.",
        "Low": "Focus on Math basics — revisit multiplication tables and practice daily exercises."
    },
    "English": {
        "High": "Outstanding in English! Try creative writing challenges and reading advanced texts.",
        "Medium": "Good effort in English! Focus on grammar exercises and reading comprehension.",
        "Low": "Start with basic English — read short stories daily and practice simple writing."
    },
    "Computer Science": {
        "High": "Great at CS! Try building small projects and explore new programming concepts.",
        "Medium": "Good progress in CS! Practice coding exercises and revisit core logic concepts.",
        "Low": "Focus on CS fundamentals — start with basic algorithms and simple coding tasks."
    }
}

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form["name"].strip()
        grade = int(request.form["grade"])
        if not name:
            return render_template("login.html", error="Please enter your name.")
        student_id = save_student(name, grade)
        ip_address = request.remote_addr
        log_login(student_id, ip_address)
        session["student_id"] = student_id
        session["student_name"] = name
        session["student_grade"] = grade
        return redirect(url_for("quiz"))
    return render_template("login.html", error=None)

@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if "student_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        quiz_score = float(request.form["quiz_score"])
        time_spent = float(request.form["time_spent"])
        attempts = float(request.form["attempts"])
        hints_used = float(request.form["hints_used"])
        streak_days = float(request.form["streak_days"])
        assignments = float(request.form["assignments"])
        subject = request.form["subject"]

        input_data = np.array([[quiz_score, time_spent, attempts,
                                hints_used, streak_days, assignments]])

        prediction_encoded = model.predict(input_data)[0]
        prediction_label = le.inverse_transform([prediction_encoded])[0]
        confidence = round(max(model.predict_proba(input_data)[0]) * 100, 1)

        if prediction_label == "High":
            points = 100
            badge = "🏆 Gold Scholar"
            badge_desc = "Elite performer — Top of the class!"
            level = "high"
        elif prediction_label == "Medium":
            points = 60
            badge = "🥈 Silver Star"
            badge_desc = "Rising star — Almost there!"
            level = "medium"
        else:
            points = 20
            badge = "🥉 Bronze Beginner"
            badge_desc = "Every expert was once a beginner!"
            level = "low"

        rec = subject_recs[subject][prediction_label]

        save_performance(
            student_id=session["student_id"],
            subject=subject,
            quiz_score=quiz_score,
            time_spent=time_spent,
            attempts=int(attempts),
            hints_used=int(hints_used),
            streak_days=int(streak_days),
            assignments=assignments,
            prediction=prediction_label,
            confidence=confidence,
            points=points
        )

        session["result"] = {
            "label": prediction_label,
            "level": level,
            "confidence": confidence,
            "points": points,
            "badge": badge,
            "badge_desc": badge_desc,
            "rec": rec,
            "quiz_score": int(quiz_score),
            "time_spent": time_spent,
            "attempts": int(attempts),
            "hints_used": int(hints_used),
            "streak_days": int(streak_days),
            "assignments": int(assignments),
            "subject": subject,
        }

        return redirect(url_for("dashboard"))

    return render_template("quiz.html",
                           name=session["student_name"],
                           grade=session["student_grade"])

@app.route("/dashboard")
def dashboard():
    if "student_id" not in session:
        return redirect(url_for("login"))
    student = get_student(session["student_id"])
    result = session.get("result")
    history = get_student_history(session["student_id"])
    total_xp = sum(row["points"] for row in history)
    return render_template("dashboard.html",
                           student=student,
                           result=result,
                           history=history,
                           total_xp=total_xp)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)