import psycopg2
import psycopg2.extras
import os
import secrets
import string
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://neondb_owner:npg_pgH3kRujF7qy@ep-sweet-glitter-abqhg4k9-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def generate_password(length=12):
    """Generate a secure random password"""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(characters) for i in range(length))
    return password

def create_tables():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recruiters (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            job_matching TEXT,
            questions TEXT,
            answers TEXT,
            correct_answers TEXT,
            evaluation_results TEXT,
            test_completed BOOLEAN DEFAULT FALSE,
            average_score FLOAT,
            test_completed_at TIMESTAMP,
            recruiter_id INTEGER REFERENCES recruiters(id)
        );
    """)

    # Add new columns if they don't exist
    try:
        cur.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS questions TEXT;")
        cur.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS answers TEXT;")
        cur.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS password VARCHAR(255);")
        cur.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS correct_answers TEXT;")
        cur.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS evaluation_results TEXT;")
        cur.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS test_completed BOOLEAN DEFAULT FALSE;")
        cur.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS average_score FLOAT;")
        cur.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS test_completed_at TIMESTAMP;")

        # Add multi-stage testing columns
        cur.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS current_test_stage VARCHAR(10) DEFAULT 'IT';")
        cur.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS math_questions TEXT;")
        cur.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS math_answers TEXT;")
        cur.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS math_correct_answers TEXT;")
        cur.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS math_evaluation_results TEXT;")
        cur.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS math_average_score FLOAT;")
        cur.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS math_test_completed BOOLEAN DEFAULT FALSE;")
        cur.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS math_test_completed_at TIMESTAMP;")
    except Exception as e:
        print(f"Note: Could not alter table structure: {e}")

    conn.commit()
    cur.close()
    conn.close()

def add_recruiter(username, email, password):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO recruiters (username, email, password) VALUES (%s, %s, %s)", (username, email, password))
    conn.commit()
    cur.close()
    conn.close()

def get_recruiter(email, password):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM recruiters WHERE email = %s AND password = %s", (email, password))
    recruiter = cur.fetchone()
    cur.close()
    conn.close()
    return recruiter

def add_candidate(username, email, job_matching, questions, recruiter_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Check if candidate already exists
    cur.execute("SELECT id FROM candidates WHERE email = %s", (email,))
    existing = cur.fetchone()

    if existing:
        cur.close()
        conn.close()
        return False, None  # Candidate already exists

    # Generate a secure password for the candidate
    generated_password = generate_password()

    # Insert new candidate with generated password
    cur.execute("INSERT INTO candidates (username, email, job_matching, questions, password, recruiter_id) VALUES (%s, %s, %s, %s, %s, %s)",
                (username, email, job_matching, questions, generated_password, recruiter_id))
    conn.commit()
    cur.close()
    conn.close()
    return True, generated_password  # Candidate added successfully, return password

def get_candidate(email, password):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM candidates WHERE email = %s AND password = %s", (email, password))
    candidate = cur.fetchone()
    cur.close()
    conn.close()
    return candidate

def get_candidate_by_email(email):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM candidates WHERE email = %s", (email,))
    candidate = cur.fetchone()
    cur.close()
    conn.close()
    return candidate

def get_candidates_by_recruiter(recruiter_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM candidates WHERE recruiter_id = %s", (recruiter_id,))
    candidates = cur.fetchall()
    cur.close()
    conn.close()
    return candidates

def update_candidate_evaluation(candidate_id, answers, correct_answers, evaluation_results, average_score):
    """Update candidate with evaluation results"""
    import json
    from datetime import datetime

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE candidates
        SET answers = %s,
            correct_answers = %s,
            evaluation_results = %s,
            average_score = %s,
            test_completed = TRUE,
            test_completed_at = %s
        WHERE id = %s
    """, (
        answers,
        json.dumps(correct_answers),
        json.dumps(evaluation_results),
        average_score,
        datetime.now(),
        candidate_id
    ))

    conn.commit()
    cur.close()
    conn.close()

def get_recruiter_email_by_candidate(candidate_id):
    """Get recruiter email for a candidate"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT r.email as recruiter_email
        FROM candidates c
        JOIN recruiters r ON c.recruiter_id = r.id
        WHERE c.id = %s
    """, (candidate_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result['recruiter_email'] if result else None

def get_all_recruiters():
    """Get all recruiters for admin"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM recruiters ORDER BY id")
    recruiters = cur.fetchall()
    cur.close()
    conn.close()
    return recruiters

def get_all_candidates():
    """Get all candidates for admin"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT c.*, r.username as recruiter_name
        FROM candidates c
        LEFT JOIN recruiters r ON c.recruiter_id = r.id
        ORDER BY c.id
    """)
    candidates = cur.fetchall()
    cur.close()
    conn.close()
    return candidates

def delete_recruiter(recruiter_id):
    """Delete a recruiter"""
    conn = get_db_connection()
    cur = conn.cursor()
    # First, update candidates to remove recruiter_id reference
    cur.execute("UPDATE candidates SET recruiter_id = NULL WHERE recruiter_id = %s", (recruiter_id,))
    # Then delete the recruiter
    cur.execute("DELETE FROM recruiters WHERE id = %s", (recruiter_id,))
    conn.commit()
    cur.close()
    conn.close()

def delete_candidate(candidate_id):
    """Delete a candidate"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM candidates WHERE id = %s", (candidate_id,))
    conn.commit()
    cur.close()
    conn.close()

# Multi-stage testing functions
def update_candidate_test_stage(candidate_id, stage):
    """Update candidate's current test stage"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE candidates SET current_test_stage = %s WHERE id = %s", (stage, candidate_id))
    conn.commit()
    cur.close()
    conn.close()

def reset_candidate_test_status(candidate_id):
    """Reset test completion status for new stage"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE candidates
        SET test_completed = FALSE,
            test_completed_at = NULL,
            answers = NULL,
            evaluation_results = NULL,
            average_score = NULL
        WHERE id = %s
    """, (candidate_id,))
    conn.commit()
    cur.close()
    conn.close()

def update_candidate_questions(candidate_id, questions_text, correct_answers):
    """Update candidate with IT questions and correct answers"""
    import json
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE candidates
        SET questions = %s, correct_answers = %s
        WHERE id = %s
    """, (questions_text, json.dumps(correct_answers), candidate_id))
    conn.commit()
    cur.close()
    conn.close()

def update_candidate_math_questions(candidate_id, questions_text, correct_answers):
    """Update candidate with MATH questions and correct answers"""
    import json
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE candidates
        SET math_questions = %s, math_correct_answers = %s
        WHERE id = %s
    """, (questions_text, json.dumps(correct_answers), candidate_id))
    conn.commit()
    cur.close()
    conn.close()

def update_candidate_math_evaluation(candidate_id, answers, correct_answers, evaluation_results, average_score):
    """Update candidate with MATH evaluation results"""
    import json
    from datetime import datetime

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE candidates
        SET math_answers = %s,
            math_evaluation_results = %s,
            math_average_score = %s,
            math_test_completed = TRUE,
            math_test_completed_at = %s
        WHERE id = %s
    """, (
        answers,
        json.dumps(evaluation_results),
        average_score,
        datetime.now(),
        candidate_id
    ))

    conn.commit()
    cur.close()
    conn.close()