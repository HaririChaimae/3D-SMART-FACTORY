import os
import secrets
import string
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///entretien_automatise.db')

# Détecter le type de base de données
if DATABASE_URL.startswith('sqlite://'):
    # SQLite
    import sqlite3
    DB_TYPE = 'sqlite'
    print("🔄 Using SQLite database")
else:
    # PostgreSQL
    try:
        import psycopg2
        import psycopg2.extras
        DB_TYPE = 'postgresql'
        print("🔄 Using PostgreSQL database")
    except ImportError:
        print("❌ PostgreSQL driver not found, falling back to SQLite")
        DATABASE_URL = 'sqlite:///entretien_automatise.db'
        import sqlite3
        DB_TYPE = 'sqlite'

def get_db_connection():
    if DB_TYPE == 'sqlite':
        # SQLite connection
        db_path = DATABASE_URL.replace('sqlite:///', '')
        return sqlite3.connect(db_path)
    else:
        # PostgreSQL connection
        return psycopg2.connect(DATABASE_URL)

def generate_password(length=12):
    """Generate a secure random password"""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(characters) for i in range(length))
    return password

def create_tables():
    conn = get_db_connection()
    cur = conn.cursor()

    if DB_TYPE == 'sqlite':
        # SQLite syntax
        cur.execute("""
            CREATE TABLE IF NOT EXISTS recruiters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                profile_picture TEXT
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                url TEXT,
                remote_friendly INTEGER DEFAULT 0,
                market TEXT,
                size TEXT
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
                recruiter_id INTEGER REFERENCES recruiters(id) ON DELETE CASCADE,
                position TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                url TEXT,
                type TEXT DEFAULT 'full-time',
                posted DATE,
                location TEXT DEFAULT 'Remote',
                skills TEXT,  -- JSON string for SQLite
                salary_from REAL,
                salary_to REAL,
                salary_currency TEXT DEFAULT 'USD',
                equity_from REAL DEFAULT 0,
                equity_to REAL DEFAULT 0,
                perks TEXT,  -- JSON string for SQLite
                apply_url TEXT,
                job_image TEXT
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                job_matching TEXT,
                questions TEXT,
                answers TEXT,
                correct_answers TEXT,
                evaluation_results TEXT,
                test_completed INTEGER DEFAULT 0,
                average_score REAL,
                test_completed_at TIMESTAMP,
                recruiter_id INTEGER REFERENCES recruiters(id),
                password TEXT,
                current_test_stage TEXT DEFAULT 'IT',
                math_questions TEXT,
                math_answers TEXT,
                math_correct_answers TEXT,
                math_evaluation_results TEXT,
                math_average_score REAL,
                math_test_completed INTEGER DEFAULT 0,
                math_test_completed_at TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER REFERENCES candidates(id) ON DELETE CASCADE,
                recruiter_id INTEGER REFERENCES recruiters(id) ON DELETE CASCADE,
                job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
                resume_data TEXT,
                extracted_data TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    else:
        # PostgreSQL syntax (original)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS recruiters (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                profile_picture TEXT
            );
        """)

        # Add profile_picture column if it doesn't exist
        try:
            cur.execute("ALTER TABLE recruiters ADD COLUMN IF NOT EXISTS profile_picture TEXT;")
        except Exception as e:
            print(f"Note: Could not add profile_picture column: {e}")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                url TEXT,
                remote_friendly BOOLEAN DEFAULT FALSE,
                market VARCHAR(255),
                size VARCHAR(255)
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id SERIAL PRIMARY KEY,
                company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
                recruiter_id INTEGER REFERENCES recruiters(id) ON DELETE CASCADE,
                position VARCHAR(255) NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                url TEXT,
                type VARCHAR(50) DEFAULT 'full-time',
                posted DATE,
                location VARCHAR(255) DEFAULT 'Remote',
                skills TEXT[],
                salary_from DECIMAL(10,2),
                salary_to DECIMAL(10,2),
                salary_currency VARCHAR(10) DEFAULT 'USD',
                equity_from DECIMAL(5,4) DEFAULT 0,
                equity_to DECIMAL(5,4) DEFAULT 0,
                perks TEXT[],
                apply_url TEXT,
                job_image TEXT
            );
        """)

        # Add recruiter_id column if it doesn't exist (for existing databases)
        try:
            cur.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS recruiter_id INTEGER REFERENCES recruiters(id) ON DELETE CASCADE;")
            cur.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_image TEXT;")
        except Exception as e:
            print(f"Note: Could not add columns: {e}")

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

        cur.execute("""
            CREATE TABLE IF NOT EXISTS resumes (
                id SERIAL PRIMARY KEY,
                candidate_id INTEGER REFERENCES candidates(id) ON DELETE CASCADE,
                recruiter_id INTEGER REFERENCES recruiters(id) ON DELETE CASCADE,
                job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
                resume_data TEXT,
                extracted_data TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

def add_recruiter(username, email, password, profile_picture=None):
    conn = get_db_connection()
    cur = conn.cursor()

    if DB_TYPE == 'sqlite':
        cur.execute("INSERT INTO recruiters (username, email, password, profile_picture) VALUES (?, ?, ?, ?)", (username, email, password, profile_picture))
    else:
        cur.execute("INSERT INTO recruiters (username, email, password, profile_picture) VALUES (%s, %s, %s, %s)", (username, email, password, profile_picture))

    conn.commit()
    cur.close()
    conn.close()

def get_recruiter(email, password):
    conn = get_db_connection()

    if DB_TYPE == 'sqlite':
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, password, profile_picture FROM recruiters WHERE email = ? AND password = ?", (email, password))
        row = cur.fetchone()
        if row:
            recruiter = {
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'password': row[3],
                'profile_picture': row[4]
            }
        else:
            recruiter = None
    else:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM recruiters WHERE email = %s AND password = %s", (email, password))
        recruiter = cur.fetchone()

    cur.close()
    conn.close()
    return recruiter

def get_recruiter_by_id(recruiter_id):
    conn = get_db_connection()

    if DB_TYPE == 'sqlite':
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, password, profile_picture FROM recruiters WHERE id = ?", (recruiter_id,))
        row = cur.fetchone()
        if row:
            recruiter = {
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'password': row[3],
                'profile_picture': row[4]
            }
        else:
            recruiter = None
    else:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM recruiters WHERE id = %s", (recruiter_id,))
        recruiter = cur.fetchone()

    cur.close()
    conn.close()
    return recruiter

def add_candidate(username, email, job_matching, questions, recruiter_id):
    conn = get_db_connection()
    cur = conn.cursor()

    if DB_TYPE == 'sqlite':
        # Check if candidate already exists
        cur.execute("SELECT id FROM candidates WHERE email = ?", (email,))
        existing = cur.fetchone()

        if existing:
            cur.close()
            conn.close()
            return False, None  # Candidate already exists

        # Generate a secure password for the candidate
        generated_password = generate_password()

        # Insert new candidate with generated password
        cur.execute("INSERT INTO candidates (username, email, job_matching, questions, password, recruiter_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (username, email, job_matching, questions, generated_password, recruiter_id))
    else:
        # PostgreSQL syntax
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

    if DB_TYPE == 'sqlite':
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, password, job_matching, questions, answers, correct_answers, evaluation_results, test_completed, average_score, test_completed_at, recruiter_id FROM candidates WHERE email = ? AND password = ?", (email, password))
        row = cur.fetchone()
        if row:
            candidate = {
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'password': row[3],
                'job_matching': row[4],
                'questions': row[5],
                'answers': row[6],
                'correct_answers': row[7],
                'evaluation_results': row[8],
                'test_completed': bool(row[9]) if row[9] is not None else False,
                'average_score': row[10],
                'test_completed_at': row[11],
                'recruiter_id': row[12]
            }
        else:
            candidate = None
    else:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM candidates WHERE email = %s AND password = %s", (email, password))
        candidate = cur.fetchone()

    cur.close()
    conn.close()
    return candidate

def get_candidate_by_email(email):
    conn = get_db_connection()

    if DB_TYPE == 'sqlite':
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, password, job_matching, questions, answers, correct_answers, evaluation_results, test_completed, average_score, test_completed_at, recruiter_id FROM candidates WHERE email = ?", (email,))
        row = cur.fetchone()
        if row:
            candidate = {
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'password': row[3],
                'job_matching': row[4],
                'questions': row[5],
                'answers': row[6],
                'correct_answers': row[7],
                'evaluation_results': row[8],
                'test_completed': bool(row[9]) if row[9] is not None else False,
                'average_score': row[10],
                'test_completed_at': row[11],
                'recruiter_id': row[12]
            }
        else:
            candidate = None
    else:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM candidates WHERE email = %s", (email,))
        candidate = cur.fetchone()

    cur.close()
    conn.close()
    return candidate

def get_candidates_by_recruiter(recruiter_id):
    conn = get_db_connection()

    if DB_TYPE == 'sqlite':
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, password, job_matching, questions, answers, correct_answers, evaluation_results, test_completed, average_score, test_completed_at, recruiter_id FROM candidates WHERE recruiter_id = ?", (recruiter_id,))
        rows = cur.fetchall()
        candidates = []
        for row in rows:
            candidate = {
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'password': row[3],
                'job_matching': row[4],
                'questions': row[5],
                'answers': row[6],
                'correct_answers': row[7],
                'evaluation_results': row[8],
                'test_completed': bool(row[9]) if row[9] is not None else False,
                'average_score': row[10],
                'test_completed_at': row[11],
                'recruiter_id': row[12]
            }
            candidates.append(candidate)
    else:
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

# Jobs functions
def add_company(name, url, remote_friendly, market, size):
    conn = get_db_connection()
    cur = conn.cursor()

    if DB_TYPE == 'sqlite':
        # First try to get existing company
        cur.execute("SELECT id FROM companies WHERE name = ?", (name,))
        existing = cur.fetchone()
        if existing:
            conn.close()
            return existing[0]

        # If not exists, insert new
        cur.execute("""
            INSERT INTO companies (name, url, remote_friendly, market, size)
            VALUES (?, ?, ?, ?, ?)
        """, (name, url, 1 if remote_friendly else 0, market, size))
        company_id = cur.lastrowid
    else:
        # PostgreSQL syntax
        # First try to get existing company
        cur.execute("SELECT id FROM companies WHERE name = %s", (name,))
        existing = cur.fetchone()
        if existing:
            conn.close()
            return existing[0]

        # If not exists, insert new
        cur.execute("""
            INSERT INTO companies (name, url, remote_friendly, market, size)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (name, url, remote_friendly, market, size))
        result = cur.fetchone()
        company_id = result[0] if result else None

    conn.commit()
    cur.close()
    conn.close()
    return company_id

def add_job(company_id, recruiter_id, position, title, description, url, job_type, posted, location, skills, salary_from, salary_to, salary_currency, equity_from, equity_to, perks, apply_url, job_image=None):
    conn = get_db_connection()
    cur = conn.cursor()

    if DB_TYPE == 'sqlite':
        # Convert skills and perks to JSON strings for SQLite
        import json
        skills_json = json.dumps(skills) if skills else None
        perks_json = json.dumps(perks) if perks else None

        cur.execute("""
            INSERT INTO jobs (company_id, recruiter_id, position, title, description, url, type, posted, location, skills, salary_from, salary_to, salary_currency, equity_from, equity_to, perks, apply_url, job_image)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (company_id, recruiter_id, position, title, description, url, job_type, posted, location, skills_json, salary_from, salary_to, salary_currency, equity_from, equity_to, perks_json, apply_url, job_image))
    else:
        cur.execute("""
            INSERT INTO jobs (company_id, recruiter_id, position, title, description, url, type, posted, location, skills, salary_from, salary_to, salary_currency, equity_from, equity_to, perks, apply_url, job_image)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (company_id, recruiter_id, position, title, description, url, job_type, posted, location, skills, salary_from, salary_to, salary_currency, equity_from, equity_to, perks, apply_url, job_image))

    conn.commit()
    cur.close()
    conn.close()

def get_all_jobs():
    conn = get_db_connection()

    if DB_TYPE == 'sqlite':
        cur = conn.cursor()
        cur.execute("""
            SELECT j.id, j.company_id, j.recruiter_id, j.position, j.title, j.description, j.url, j.type,
                   j.posted, j.location, j.skills, j.salary_from, j.salary_to, j.salary_currency,
                   j.equity_from, j.equity_to, j.perks, j.apply_url, j.job_image,
                   c.name as company_name, c.url as company_url, c.remote_friendly, c.market, c.size,
                   r.username as recruiter_name, r.email as recruiter_email, r.profile_picture as recruiter_picture
            FROM jobs j
            JOIN companies c ON j.company_id = c.id
            JOIN recruiters r ON j.recruiter_id = r.id
            ORDER BY j.posted DESC
        """)

        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

        jobs = []
        for row in rows:
            job = dict(zip(columns, row))
            jobs.append(job)

    else:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT j.*, c.name as company_name, c.url as company_url, c.remote_friendly, c.market, c.size,
                r.username as recruiter_name, r.email as recruiter_email, r.profile_picture as recruiter_picture
            FROM jobs j
            JOIN companies c ON j.company_id = c.id
            JOIN recruiters r ON j.recruiter_id = r.id
            ORDER BY j.posted DESC
        """)
        jobs = cur.fetchall()

    cur.close()
    conn.close()

    # ✅ Normalisation des skills
    for job in jobs:
        skills = job.get("skills", [])
        if isinstance(skills, str):
            # Ex: "{Python,SQL}" → ["Python","SQL"] (PostgreSQL)
            # Ou JSON string (SQLite)
            try:
                import json
                skills = json.loads(skills)
            except:
                skills = [s.strip() for s in skills.strip("{}").split(",") if s.strip()]
        elif skills is None:
            skills = []
        elif isinstance(skills, list):
            skills = [str(s).strip() for s in skills]

        # Mettre en lowercase
        job["skills"] = [s.lower() for s in skills]

    return jobs



def get_jobs_by_recruiter(recruiter_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT j.*, c.name as company_name, c.url as company_url, c.remote_friendly, c.market, c.size,
               r.username as recruiter_name, r.email as recruiter_email, r.profile_picture as recruiter_picture
        FROM jobs j
        JOIN companies c ON j.company_id = c.id
        JOIN recruiters r ON j.recruiter_id = r.id
        WHERE j.recruiter_id = %s
        ORDER BY j.posted DESC
    """, (recruiter_id,))
    jobs = cur.fetchall()
    cur.close()
    conn.close()
    return jobs

def get_job_by_id(job_id):
    """Get a specific job by ID"""
    conn = get_db_connection()

    if DB_TYPE == 'sqlite':
        cur = conn.cursor()
        cur.execute("""
            SELECT j.id, j.company_id, j.recruiter_id, j.position, j.title, j.description, j.url, j.type,
                   j.posted, j.location, j.skills, j.salary_from, j.salary_to, j.salary_currency,
                   j.equity_from, j.equity_to, j.perks, j.apply_url, j.job_image,
                   c.name as company_name, c.url as company_url, c.remote_friendly, c.market, c.size,
                   r.username as recruiter_name, r.email as recruiter_email, r.profile_picture as recruiter_picture
            FROM jobs j
            JOIN companies c ON j.company_id = c.id
            JOIN recruiters r ON j.recruiter_id = r.id
            WHERE j.id = ?
        """, (job_id,))

        columns = [desc[0] for desc in cur.description]
        row = cur.fetchone()

        if row:
            job = dict(zip(columns, row))
        else:
            job = None

    else:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT j.*, c.name as company_name, c.url as company_url, c.remote_friendly, c.market, c.size,
                r.username as recruiter_name, r.email as recruiter_email, r.profile_picture as recruiter_picture
            FROM jobs j
            JOIN companies c ON j.company_id = c.id
            JOIN recruiters r ON j.recruiter_id = r.id
            WHERE j.id = %s
        """, (job_id,))
        job = cur.fetchone()

    cur.close()
    conn.close()

    if job:
        # Normalize skills
        skills = job.get("skills", [])
        if isinstance(skills, str):
            try:
                import json
                skills = json.loads(skills)
            except:
                skills = [s.strip() for s in skills.strip("{}").split(",") if s.strip()]
        elif skills is None:
            skills = []
        elif isinstance(skills, list):
            skills = [str(s).strip() for s in skills]

        job["skills"] = [s.lower() for s in skills]

    return job

def get_jobs_by_company(company_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT * FROM jobs WHERE company_id = %s ORDER BY posted DESC
    """, (company_id,))
    jobs = cur.fetchall()
    cur.close()
    conn.close()
    return jobs

def delete_job(job_id):
    conn = get_db_connection()
    cur = conn.cursor()

    if DB_TYPE == 'sqlite':
        cur.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    else:
        cur.execute("DELETE FROM jobs WHERE id = %s", (job_id,))

    conn.commit()
    cur.close()
    conn.close()

def delete_company(company_id):
    conn = get_db_connection()
    cur = conn.cursor()

    if DB_TYPE == 'sqlite':
        # Jobs will be deleted automatically due to CASCADE
        cur.execute("DELETE FROM companies WHERE id = ?", (company_id,))
    else:
        # Jobs will be deleted automatically due to CASCADE
        cur.execute("DELETE FROM companies WHERE id = %s", (company_id,))

    conn.commit()
    cur.close()
    conn.close()

def get_all_companies():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM companies ORDER BY name")
    companies = cur.fetchall()
    cur.close()
    conn.close()
    return companies

def get_recruiter_email_by_candidate(candidate_id):
    """Get recruiter email for a candidate"""
    conn = get_db_connection()

    if DB_TYPE == 'sqlite':
        cur = conn.cursor()
        cur.execute("""
            SELECT r.email as recruiter_email
            FROM candidates c
            JOIN recruiters r ON c.recruiter_id = r.id
            WHERE c.id = ?
        """, (candidate_id,))
        result = cur.fetchone()
        recruiter_email = result[0] if result else None
    else:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT r.email as recruiter_email
            FROM candidates c
            JOIN recruiters r ON c.recruiter_id = r.id
            WHERE c.id = %s
        """, (candidate_id,))
        result = cur.fetchone()
        recruiter_email = result['recruiter_email'] if result else None

    cur.close()
    conn.close()
    return recruiter_email

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

    if DB_TYPE == 'sqlite':
        # First, update candidates to remove recruiter_id reference
        cur.execute("UPDATE candidates SET recruiter_id = NULL WHERE recruiter_id = ?", (recruiter_id,))
        # Then delete the recruiter
        cur.execute("DELETE FROM recruiters WHERE id = ?", (recruiter_id,))
    else:
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

    if DB_TYPE == 'sqlite':
        cur.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
    else:
        cur.execute("DELETE FROM candidates WHERE id = %s", (candidate_id,))

    conn.commit()
    cur.close()
    conn.close()

# Resume functions
def add_resume(candidate_id, recruiter_id, job_id, resume_data, extracted_data):
    """Add a resume application"""
    conn = get_db_connection()
    cur = conn.cursor()

    if DB_TYPE == 'sqlite':
        cur.execute("""
            INSERT INTO resumes (candidate_id, recruiter_id, job_id, resume_data, extracted_data)
            VALUES (?, ?, ?, ?, ?)
        """, (candidate_id, recruiter_id, job_id, resume_data, extracted_data))
    else:
        cur.execute("""
            INSERT INTO resumes (candidate_id, recruiter_id, job_id, resume_data, extracted_data)
            VALUES (%s, %s, %s, %s, %s)
        """, (candidate_id, recruiter_id, job_id, resume_data, extracted_data))

    conn.commit()
    cur.close()
    conn.close()

def get_resumes_by_job(job_id):
    """Get all resumes for a specific job"""
    conn = get_db_connection()

    if DB_TYPE == 'sqlite':
        cur = conn.cursor()
        cur.execute("""
            SELECT r.id, r.candidate_id, r.recruiter_id, r.job_id, r.resume_data, r.extracted_data, r.applied_at,
                   c.username, c.email, c.password, c.test_completed, c.average_score, c.test_completed_at
            FROM resumes r
            JOIN candidates c ON r.candidate_id = c.id
            WHERE r.job_id = ?
            ORDER BY r.applied_at DESC
        """, (job_id,))

        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        resumes = []
        for row in rows:
            resume = dict(zip(columns, row))
            resumes.append(resume)
    else:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT r.*, c.username, c.email, c.password, c.test_completed, c.average_score, c.test_completed_at
            FROM resumes r
            JOIN candidates c ON r.candidate_id = c.id
            WHERE r.job_id = %s
            ORDER BY r.applied_at DESC
        """, (job_id,))
        resumes = cur.fetchall()

    cur.close()
    conn.close()
    return resumes

def get_resume_by_candidate_and_job(candidate_id, job_id):
    """Check if candidate already applied for this job"""
    conn = get_db_connection()

    if DB_TYPE == 'sqlite':
        cur = conn.cursor()
        cur.execute("SELECT id, candidate_id, recruiter_id, job_id, resume_data, extracted_data, applied_at FROM resumes WHERE candidate_id = ? AND job_id = ?", (candidate_id, job_id))
        row = cur.fetchone()
        if row:
            resume = {
                'id': row[0],
                'candidate_id': row[1],
                'recruiter_id': row[2],
                'job_id': row[3],
                'resume_data': row[4],
                'extracted_data': row[5],
                'applied_at': row[6]
            }
        else:
            resume = None
    else:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM resumes WHERE candidate_id = %s AND job_id = %s", (candidate_id, job_id))
        resume = cur.fetchone()

    cur.close()
    conn.close()
    return resume

# Multi-stage testing functions
def update_candidate_test_stage(candidate_id, stage):
    """Update candidate's current test stage"""
    conn = get_db_connection()
    cur = conn.cursor()

    if DB_TYPE == 'sqlite':
        cur.execute("UPDATE candidates SET current_test_stage = ? WHERE id = ?", (stage, candidate_id))
    else:
        cur.execute("UPDATE candidates SET current_test_stage = %s WHERE id = %s", (stage, candidate_id))

    conn.commit()
    cur.close()
    conn.close()

def reset_candidate_test_status(candidate_id):
    """Reset test completion status for new stage"""
    conn = get_db_connection()
    cur = conn.cursor()

    if DB_TYPE == 'sqlite':
        cur.execute("""
            UPDATE candidates
            SET test_completed = 0,
                test_completed_at = NULL,
                answers = NULL,
                evaluation_results = NULL,
                average_score = NULL
            WHERE id = ?
        """, (candidate_id,))
    else:
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

def update_candidate_questions(candidate_id, questions_text, correct_answers):
    """Update candidate with test questions and correct answers"""
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