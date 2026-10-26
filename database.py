import sqlite3

DATABASE = "eduquest.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            grade INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            quiz_score REAL NOT NULL,
            time_spent REAL NOT NULL,
            attempts INTEGER NOT NULL,
            hints_used INTEGER NOT NULL,
            streak_days INTEGER NOT NULL,
            assignments REAL NOT NULL,
            prediction TEXT NOT NULL,
            confidence REAL NOT NULL,
            points INTEGER NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS login_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            login_time TEXT DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def save_student(name, grade):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO students (name, grade) VALUES (?, ?)", (name, grade))
    student_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return student_id

def log_login(student_id, ip_address):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO login_log (student_id, ip_address) VALUES (?, ?)",
                   (student_id, ip_address))
    conn.commit()
    conn.close()

def save_performance(student_id, subject, quiz_score, time_spent,
                     attempts, hints_used, streak_days,
                     assignments, prediction, confidence, points):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO performance
        (student_id, subject, quiz_score, time_spent, attempts,
         hints_used, streak_days, assignments, prediction,
         confidence, points)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (student_id, subject, quiz_score, time_spent, attempts,
          hints_used, streak_days, assignments, prediction,
          confidence, points))
    conn.commit()
    conn.close()

def get_student_history(student_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM performance
        WHERE student_id = ?
        ORDER BY timestamp DESC
    """, (student_id,))
    records = cursor.fetchall()
    conn.close()
    return records

def get_student(student_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    student = cursor.fetchone()
    conn.close()
    return student