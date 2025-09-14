from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
from dotenv import load_dotenv
load_dotenv()
import json
from preprocessing import preprocess_cv
from matching import match_jobs
from agent import (
    generate_answer_for_question,
    evaluate_answers,
    build_vector_store,
    search_knowledge,
    extract_text_from_pdf
)
import google.generativeai as genai
import re
import logging
import sys
from io import StringIO
import contextlib
import traceback
import db
import smtplib
from email.mime.text import MIMEText
import time
import base64
from parsing import parse_cv
from pathlib import Path

# Import functions from app.py for question generation
# We'll define Flask-compatible versions without Streamlit dependencies

# ========== FLASK-COMPATIBLE QUESTION GENERATION ==========
def get_pdf_files_info():
    """Retourne des infos sur les PDFs dans le dossier data pour le cache"""
    pdf_files = []
    if os.path.exists("data"):
        for file_name in os.listdir("data"):
            if file_name.lower().endswith('.pdf'):
                file_path = os.path.join("data", file_name)
                pdf_files.append({
                    'name': file_name,
                    'size': os.path.getsize(file_path),
                    'mtime': os.path.getmtime(file_path)
                })
    return pdf_files

def build_vector_store_cached(pdf_files_info):
    """Cache la construction du vector store basé sur les infos des PDFs"""
    if not pdf_files_info:
        print("Aucun PDF trouvé dans le dossier \"data\"")
        return None, []

    print('Construction de la base de connaissances...')
    index, texts = build_vector_store()

    if index is None:
        print("Impossible de construire la base de connaissances")
        return None, []

    print(f'Base de connaissances construite avec {len(texts)} documents')
    return index, texts

def generate_interview_content():
    """Génère les questions à partir de la base de connaissances (Flask version)"""
    # Obtenir les infos des PDFs pour le cache
    pdf_files_info = get_pdf_files_info()

    if not pdf_files_info:
        knowledge_chunks = []
        index, texts = None, []
    else:
        # Construire le vector store
        index, texts = build_vector_store_cached(tuple(
            (pdf['name'], pdf['size'], pdf['mtime']) for pdf in pdf_files_info
        ))

        if index and texts:
            # Rechercher dans la base de connaissances
            query = "programmation développement techniques Python"
            knowledge_chunks = search_knowledge(query, index, texts, top_k=3)
        else:
            knowledge_chunks = []

    # Générer les questions
    try:
        questions = generate_questions_from_knowledge(knowledge_chunks, n=3)
    except Exception as e:
        print(f"Error generating questions: {e}")
        questions = []

    if not questions or all(not q.strip() for q in questions):
        questions = [
            "Quelles sont les meilleures pratiques en programmation ?",
            "Décrivez les fonctionnalités principales du langage Python.",
            "Comment résoudriez-vous un problème complexe en programmation ?"
        ]

    # Générer les réponses correctes
    correct_answers = {}

    for i, q in enumerate(questions, 1):
        try:
            if index and texts:
                answer = generate_answer_for_question(q, index, texts)
            else:
                answer = f"Réponse basée sur les meilleures pratiques pour la question: {q[:50]}..."

            correct_answers[q] = answer

        except Exception as e:
            print(f"Error generating answer for question {i}: {e}")
            correct_answers[q] = f"Réponse par défaut - erreur de génération"

    return questions, correct_answers

# ========== QUESTION GENERATION FUNCTIONS ==========
def generate_questions_from_knowledge(knowledge_chunks, n=3):
    context = "\n---\n".join(knowledge_chunks[:3])[:3000]
    prompt = f"""
    Voici un extrait de la base de connaissances technique :
    {context}

    Générez {n} exercices pratiques en français basés uniquement sur ce contenu.

    Chaque exercice doit suivre exactement ce format :

    Exercice : [Titre clair et court]
    Description : [Explication complète de la tâche, avec détails sur les entrées, sorties attendues,
    et contraintes éventuelles. Rédigez comme une consigne d'énoncé.]

    ⚠️ Contraintes :
    - Ne mettez pas de numérotation automatique (pas de 1., 2., etc.).
    - Ne répondez qu'avec les exercices, rien d'autre.
    - N'utilisez pas de saisie avec input(). Les exercices doivent définir les valeurs d'entrée sous forme
    de variables ou de paramètres déjà fournis, jamais par interaction utilisateur.
    """

    try:
        # Use Google Gemini
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            text = response.text.strip()
        except Exception as e:
            print(f"❌ Gemini question generation failed: {e}")
            raise Exception("Gemini failed to generate questions")

        # Split on "Exercice :" and keep everything together
        raw_exercises = re.split(r"(?=Exercice\s*:)", text)
        questions = [ex.strip() for ex in raw_exercises if ex.strip()]

        return questions[:n]
    except Exception as e:
        print(f"Error generating questions: {e}")
        # Fallback: generate questions directly from PDF content
        return generate_questions_from_pdf_fallback(n)

def generate_questions_from_pdf_fallback(n=3):
    """Generate questions directly from PDF content when API fails"""
    try:
        pdf_path = "data/IT_exercices.pdf"
        if os.path.exists(pdf_path):
            pdf_text = extract_text_from_pdf(pdf_path)

            # Parse exercises from PDF text
            exercises = []
            lines = pdf_text.split('\n')

            current_exercise = ""
            in_exercise = False

            for line in lines:
                line = line.strip()
                if line.startswith("Exercice "):
                    if current_exercise:
                        exercises.append(current_exercise.strip())
                    current_exercise = line + "\n"
                    in_exercise = True
                elif in_exercise and line:
                    if line.startswith("Correction :"):
                        # Convert input() calls to variable assignments
                        current_exercise += "Description : Écrivez un programme qui "
                        continue
                    elif "input(" in line:
                        # Replace input calls with variable assignments
                        if "nombre1" in line:
                            current_exercise += "Définissez nombre1 = 5 et nombre2 = 3 comme variables.\n"
                        elif "nombre" in line and "pair" in current_exercise.lower():
                            current_exercise += "Définissez nombre = 7 comme variable.\n"
                        elif "a" in line and "b" in line and "c" in line:
                            current_exercise += "Définissez a = 10, b = 25, c = 15 comme variables.\n"
                        continue
                    elif "print(" in line:
                        current_exercise += "Affichez le résultat avec print().\n"
                        continue
                    elif line and not line.startswith("#"):
                        current_exercise += line + "\n"

            if current_exercise:
                exercises.append(current_exercise.strip())

            # Convert to required format
            formatted_exercises = []
            for exercise in exercises[:n]:
                if "Somme de deux nombres" in exercise:
                    formatted_exercises.append("""Exercice : Calcul de la somme de deux nombres
Description : Écrivez une fonction en Python qui calcule la somme de deux nombres donnés. Définissez les valeurs des deux nombres comme des variables au début de votre code (par exemple, nombre1 = 5 et nombre2 = 3). La fonction doit retourner la somme de ces deux nombres. Testez votre fonction en affichant le résultat avec print().""")
                elif "pair ou impair" in exercise:
                    formatted_exercises.append("""Exercice : Vérification de parité d'un nombre
Description : Écrivez une fonction en Python qui détermine si un nombre donné est pair ou impair. Définissez le nombre à vérifier comme une variable au début de votre code (par exemple, nombre = 7). La fonction doit retourner une chaîne de caractères indiquant si le nombre est "pair" ou "impair". Testez votre fonction en affichant le résultat avec print().""")
                elif "plus grand" in exercise:
                    formatted_exercises.append("""Exercice : Recherche du plus grand nombre parmi trois
Description : Écrivez une fonction en Python qui trouve le plus grand nombre parmi trois nombres donnés. Définissez les trois nombres comme des variables au début de votre code (par exemple, a = 10, b = 25, c = 15). La fonction doit retourner le plus grand des trois nombres. Testez votre fonction en affichant le résultat avec print().""")

            return formatted_exercises

    except Exception as e:
        print(f"Error in PDF fallback: {e}")

    return []

# ========== ANSWER GENERATION FUNCTION ==========
def generate_answer_for_question(question, index=None, texts=None, max_context_length=1500):
    """Génère une réponse à une question en utilisant OpenRouter ou Gemini"""
    try:
        # Recherche dans la base de connaissances si disponible
        context = ""
        if index and texts:
            relevant = search_knowledge(question, index, texts, top_k=2)
            if relevant:
                context = "\n".join(relevant)[:max_context_length]

        prompt = f"""
        Question d'entretien :
        {question}

        {"Contexte (issu du PDF corrigé) :" + context if context else ""}

        Donne une réponse complète et pédagogique en français.
        Explique le concept et fournis un exemple de code si applicable.
        """

        # Use Google Gemini
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            print("✅ Réponse générée avec Gemini")
            return response.text.strip()
        except Exception as e:
            print(f"⚠️ Gemini failed: {e}")
            return "Réponse par défaut - IA temporairement indisponible"

    except Exception as e:
        print(f"❌ Erreur génération réponse: {e}")
        return "Réponse non disponible - erreur système."

app = Flask(__name__, template_folder='.')
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("🚀 DEBUG - Flask app starting...")
print("🔧 DEBUG - Logging configured")
print("📊 DEBUG - Database initialization...")

GEN_MODEL = "gemini-1.5-flash"

# Initialize database (will use SQLite by default from .env)
try:
    db.create_tables()
    print("✅ Database initialized successfully")
except Exception as e:
    print(f"❌ Database initialization error: {e}")
    print("🔄 Switching to SQLite for simple setup...")
    # Force SQLite if PostgreSQL fails
    import os
    os.environ['DATABASE_URL'] = 'sqlite:///entretien_automatise.db'
    try:
        db.create_tables()
        print("✅ SQLite database initialized successfully")
    except Exception as e2:
        print(f"❌ SQLite initialization also failed: {e2}")
        print("💡 Please check your database configuration")

# ========== EMAIL FUNCTION ==========
def send_email(to_email, subject, body):
    """Send email with better error handling and logging"""
    email_user = os.environ.get('EMAIL_USER')
    email_password = os.environ.get('EMAIL_PASSWORD')

    print("🔍 DEBUG EMAIL CONFIGURATION:")
    print(f"   EMAIL_USER: {email_user}")
    print(f"   EMAIL_PASSWORD: {'*' * len(email_password) if email_password else 'NOT SET'}")
    print(f"   To: {to_email}")
    print(f"   Subject: {subject}")

    # Check if email credentials are configured
    if not email_user or not email_password:
        print("❌ EMAIL CONFIGURATION MISSING")
        print("   Please set EMAIL_USER and EMAIL_PASSWORD in your .env file")
        print("   For Gmail, use your email and an App Password (not your regular password)")
        print("   Current .env values:")
        print(f"   EMAIL_USER={email_user}")
        print(f"   EMAIL_PASSWORD={email_password}")
        print("   Email content that would have been sent:")
        print(f"   To: {to_email}")
        print(f"   Subject: {subject}")
        print(f"   Body: {body[:200]}...")
        return False

    # Check if using default values
    if email_user == "your_email@gmail.com" or email_password == "your_app_password_here":
        print("❌ USING DEFAULT EMAIL VALUES")
        print("   Please update your .env file with real Gmail credentials")
        print("   1. Set EMAIL_USER=your.real.email@gmail.com")
        print("   2. Set EMAIL_PASSWORD=your_16_char_app_password")
        return False

    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = email_user
        msg['To'] = to_email

        print("🔗 Connecting to Gmail SMTP...")
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            print("🔒 TLS connection established")

            print("🔑 Attempting login...")
            server.login(email_user, email_password)
            print("✅ Login successful")

            print("📤 Sending email...")
            server.sendmail(msg['From'], to_email, msg.as_string())
            print(f"✅ EMAIL SENT SUCCESSFULLY TO {to_email}")
            return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ AUTHENTICATION FAILED: {e}")
        print("   Check your App Password or 2FA settings")
        print("   For Gmail: Go to Google Account > Security > 2-Step Verification > App passwords")
    except smtplib.SMTPConnectError as e:
        print(f"❌ CONNECTION FAILED: {e}")
        print("   Check your internet connection")
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        print("   Email content that would have been sent:")
        print(f"   To: {to_email}")
        print(f"   Subject: {subject}")
        print(f"   Body: {body[:200]}...")

    return False

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/jobs")
def jobs():
    # Get all jobs from database
    jobs_data = db.get_all_jobs()

    # Extract unique locations and types for filters
    locations = ["All"] + sorted(list(set([job['location'] for job in jobs_data if job.get('location')])))
    job_types = ["All"] + sorted(list(set([job['type'] for job in jobs_data if job.get('type')])))

    return render_template("jobs.html", jobs=jobs_data, locations=locations, job_types=job_types)

@app.route("/jobs/search", methods=['POST'])
def search_jobs():
    # Get search parameters
    search_term = request.form.get('search', '').strip()
    location_filter = request.form.get('location', 'All')
    type_filter = request.form.get('type', 'All')

    # Get all jobs
    jobs_data = db.get_all_jobs()

    # Apply filters
    filtered_jobs = jobs_data

    if search_term:
        filtered_jobs = [job for job in filtered_jobs if
            search_term.lower() in job['title'].lower() or
            search_term.lower() in job.get('company_name', '').lower() or
            (job.get('skills') and any(search_term.lower() in skill.lower() for skill in job['skills'])) or
            search_term.lower() in job.get('description', '').lower()]

    if location_filter != "All":
        filtered_jobs = [job for job in filtered_jobs if job.get('location') == location_filter]

    if type_filter != "All":
        filtered_jobs = [job for job in filtered_jobs if job.get('type') == type_filter]

    # Extract unique locations and types for filters
    locations = ["All"] + sorted(list(set([job['location'] for job in jobs_data if job.get('location')])))
    job_types = ["All"] + sorted(list(set([job['type'] for job in jobs_data if job.get('type')])))

    return render_template("jobs.html",
                         jobs=filtered_jobs,
                         locations=locations,
                         job_types=job_types,
                         search_term=search_term,
                         location_filter=location_filter,
                         type_filter=type_filter)

@app.route("/jobs/filter", methods=['POST'])
def filter_jobs():
    """Handle AJAX filtering requests"""
    search_term = request.form.get('search', '').strip()
    location_filter = request.form.get('location', 'All')
    type_filter = request.form.get('type', 'All')

    # Get all jobs
    jobs_data = db.get_all_jobs()

    # Apply filters
    filtered_jobs = jobs_data

    if search_term:
        filtered_jobs = [job for job in filtered_jobs if
            search_term.lower() in job['title'].lower() or
            search_term.lower() in job.get('company_name', '').lower() or
            (job.get('skills') and any(search_term.lower() in skill.lower() for skill in job['skills'])) or
            search_term.lower() in job.get('description', '').lower()]

    if location_filter != "All":
        filtered_jobs = [job for job in filtered_jobs if job.get('location') == location_filter]

    if type_filter != "All":
        filtered_jobs = [job for job in filtered_jobs if job.get('type') == type_filter]

    return jsonify({
        'jobs': filtered_jobs,
        'count': len(filtered_jobs)
    })

@app.route("/upload-cv", methods=['POST'])
def upload_cv():
    if 'cv_file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('jobs'))

    file = request.files['cv_file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('jobs'))

    if file and (file.filename.lower().endswith('.pdf') or file.filename.lower().endswith('.docx')):
        try:
            # Process the CV
            file_content = file.read()
            file_name = file.filename
            cv_text, cv_data = process_cv_cached(file_content, file_name)

            if cv_data and cv_data.get("skills"):
                # Store CV data in session
                session['cv_data'] = cv_data
                session['cv_text'] = cv_text

                # Get matched jobs
                jobs_data = db.get_all_jobs()
                matched_jobs = process_job_matching(cv_data, jobs_data)

                flash(f'CV processed successfully! Found {len(cv_data.get("skills", []))} skills.', 'success')

                # Extract unique locations and types for filters
                locations = ["All"] + sorted(list(set([job['location'] for job in jobs_data if job.get('location')])))
                job_types = ["All"] + sorted(list(set([job['type'] for job in jobs_data if job.get('type')])))

                return render_template("jobs.html",
                                     jobs=matched_jobs,
                                     locations=locations,
                                     job_types=job_types,
                                     cv_data=cv_data,
                                     matched_jobs=matched_jobs)
            else:
                flash('Could not extract skills from CV. Please try again.', 'error')
                return redirect(url_for('jobs'))

        except Exception as e:
            flash(f'Error processing CV: {str(e)}', 'error')
            return redirect(url_for('jobs'))
    else:
        flash('Please upload a PDF or DOCX file.', 'error')
        return redirect(url_for('jobs'))

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/recruiter/login", methods=['POST'])
def recruiter_login():
    email = request.form.get('email')
    password = request.form.get('password')

    # Check for default recruiter credentials
    if email == "recruiter@gmail.com" and password == "123":
        # Check if default recruiter exists, if not create it
        default_recruiter = db.get_recruiter_by_id(1)
        if not default_recruiter:
            # Create default recruiter
            db.add_recruiter("Recruiter", "recruiter@gmail.com", "123")
            default_recruiter = db.get_recruiter_by_id(1)

        if default_recruiter:
            session['user'] = default_recruiter
            session['user_type'] = "recruiter"
            flash('Login successful!', 'success')
            return redirect(url_for('recruiter_dashboard'))
        else:
            flash('Failed to setup default recruiter', 'error')
            return redirect(url_for('login'))
    else:
        recruiter = db.get_recruiter(email, password)
        if recruiter:
            session['user'] = recruiter
            session['user_type'] = "recruiter"
            flash('Login successful!', 'success')
            return redirect(url_for('recruiter_dashboard'))
        else:
            flash('Invalid credentials', 'error')
            return redirect(url_for('login'))

@app.route("/recruiter/register", methods=['POST'])
def recruiter_register():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    try:
        recruiter_id = db.add_recruiter(username, email, password, None)
        if recruiter_id:
            flash('Registration successful! Please login.', 'success')
        else:
            flash('Email already exists', 'error')
    except Exception as e:
        flash(f'Registration failed: {str(e)}', 'error')

    return redirect(url_for('login'))

@app.route("/admin/login", methods=['POST'])
def admin_login():
    email = request.form.get('email')
    password = request.form.get('password')

    # For demo purposes, using simple admin credentials
    if email == "admin@gmail.com" and password == "123":
        session['user'] = {"username": "Admin", "email": email, "id": 0}
        session['user_type'] = "admin"
        flash('Admin login successful!', 'success')
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Invalid admin credentials', 'error')
        return redirect(url_for('login'))

@app.route("/recruiter/dashboard")
def recruiter_dashboard():
    if 'user' not in session or session.get('user_type') != 'recruiter':
        flash('Please login first', 'error')
        return redirect(url_for('login'))

    recruiter = session['user']
    recruiter_id = recruiter.get('id') if isinstance(recruiter, dict) else recruiter['id']

    jobs = db.get_jobs_by_recruiter(recruiter_id)

    # Get all applications (resumes) for this recruiter's jobs
    applications = []
    candidate_ids = set()  # Track unique candidates with active applications
    if jobs:
        for job in jobs:
            job_applications = db.get_resumes_by_job(job['id'])
            if job_applications:
                # Add job info to each application
                for app in job_applications:
                    app['job_title'] = job['title']
                    app['job_company'] = job['company_name']
                    applications.append(app)
                    candidate_ids.add(app['candidate_id'])

    # Only get candidates who have active applications to current jobs
    candidates = []
    if candidate_ids:
        for candidate_id in candidate_ids:
            candidate = db.get_candidate_by_id(candidate_id)
            if candidate:
                # Parse evaluation_results JSON if it exists
                if candidate.get('evaluation_results'):
                    try:
                        candidate['evaluation_results'] = json.loads(candidate['evaluation_results'])
                        print(f"🔍 DEBUG - Parsed evaluation_results for candidate {candidate_id}: {candidate['evaluation_results']}")
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"❌ DEBUG - Failed to parse evaluation_results for candidate {candidate_id}: {e}")
                        candidate['evaluation_results'] = {}
                else:
                    candidate['evaluation_results'] = {}

                # Ensure average_score is a float
                if candidate.get('average_score') is not None:
                    try:
                        candidate['average_score'] = float(candidate['average_score'])
                    except (ValueError, TypeError):
                        candidate['average_score'] = 0.0

                candidates.append(candidate)

    return render_template("recruiter_dashboard.html",
                           recruiter=recruiter,
                           candidates=candidates,
                           jobs=jobs,
                           applications=applications)

@app.route("/recruiter/add-job", methods=['GET', 'POST'])
def add_job():
    if 'user' not in session or session.get('user_type') != 'recruiter':
        flash('Please login first', 'error')
        return redirect(url_for('login'))

    recruiter = session['user']
    recruiter_id = recruiter.get('id') if isinstance(recruiter, dict) else recruiter['id']

    if request.method == 'POST':
        try:
            # Get form data
            company_name = request.form.get('company_name')
            position = request.form.get('position')
            title = request.form.get('title')
            description = request.form.get('description')
            location = request.form.get('location', 'Remote')
            job_type = request.form.get('job_type', 'full-time')
            salary_from = request.form.get('salary_from')
            salary_to = request.form.get('salary_to')
            salary_currency = request.form.get('salary_currency', 'EUR')
            skills = request.form.get('skills', '')
            apply_url = request.form.get('apply_url')

            # Convert salary to float if provided
            salary_from = float(salary_from) if salary_from and salary_from.strip() else None
            salary_to = float(salary_to) if salary_to and salary_to.strip() else None

            # Parse skills (comma-separated)
            skills_list = [s.strip() for s in skills.split(',') if s.strip()]

            # Get or create company
            company_id = db.add_company(company_name, "", False, "", "")

            if not company_id:
                flash('Error creating company', 'error')
                return redirect(request.url)

            # Handle job image upload
            job_image = None
            if 'job_image' in request.files:
                image_file = request.files['job_image']
                if image_file and image_file.filename:
                    image_data = image_file.read()
                    job_image = base64.b64encode(image_data).decode('utf-8')

            # Add job to database
            db.add_job(
                company_id=company_id,
                recruiter_id=recruiter_id,
                position=position,
                title=title,
                description=description,
                url="",
                job_type=job_type,
                posted=request.form.get('posted_date'),
                location=location,
                skills=skills_list,
                salary_from=salary_from,
                salary_to=salary_to,
                salary_currency=salary_currency,
                equity_from=0.0,
                equity_to=0.0,
                perks=[],
                apply_url=apply_url,
                job_image=job_image
            )

            flash('Job added successfully!', 'success')
            return redirect(url_for('jobs'))

        except Exception as e:
            flash(f'Error adding job: {str(e)}', 'error')
            return redirect(request.url)

    # GET request - show form
    from datetime import datetime
    companies = db.get_all_companies()
    return render_template("add_job.html",
                         recruiter=recruiter,
                         companies=companies,
                         today=datetime.now().date())

@app.route("/admin/dashboard")
def admin_dashboard():
    if 'user' not in session or session.get('user_type') != 'admin':
        flash('Please login first', 'error')
        return redirect(url_for('login'))

    recruiters = db.get_all_recruiters()
    candidates = db.get_all_candidates()

    total_candidates = len(candidates)
    completed_tests = sum(1 for c in candidates if c.get('test_completed'))
    completion_rate = (completed_tests / total_candidates * 100) if total_candidates > 0 else 0

    return render_template("admin_dashboard.html",
                          recruiters=recruiters,
                          candidates=candidates,
                          total_candidates=total_candidates,
                          completed_tests=completed_tests,
                          completion_rate=completion_rate)

@app.route("/admin/add-recruiter", methods=['POST'])
def add_recruiter():
    """Add a new recruiter"""
    if 'user' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Handle profile picture upload
        profile_picture = None
        if 'profile_picture' in request.files:
            image_file = request.files['profile_picture']
            if image_file and image_file.filename:
                image_data = image_file.read()
                profile_picture = base64.b64encode(image_data).decode('utf-8')

        # Add recruiter to database
        recruiter_id = db.add_recruiter(username, email, password, profile_picture)

        if recruiter_id:
            flash('Recruiter added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Email already exists', 'error')
            return redirect(url_for('admin_dashboard'))

    except Exception as e:
        flash(f'Error adding recruiter: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route("/admin/delete-recruiter/<int:recruiter_id>", methods=['POST'])
def delete_recruiter(recruiter_id):
    """Delete a recruiter"""
    if 'user' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    try:
        # Check if recruiter exists
        recruiter = db.get_recruiter_by_id(recruiter_id)
        if not recruiter:
            return jsonify({'success': False, 'error': 'Recruiter not found'}), 404

        # Delete the recruiter
        db.delete_recruiter(recruiter_id)

        return jsonify({'success': True, 'message': 'Recruiter deleted successfully'})

    except Exception as e:
        print(f"Error deleting recruiter: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/admin/delete-candidate/<int:candidate_id>", methods=['POST'])
def delete_candidate(candidate_id):
    """Delete a candidate"""
    if 'user' not in session or session.get('user_type') != 'admin':
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    try:
        # Check if candidate exists
        candidate = db.get_candidate_by_id(candidate_id)
        if not candidate:
            return jsonify({'success': False, 'error': 'Candidate not found'}), 404

        # Delete the candidate
        db.delete_candidate(candidate_id)

        return jsonify({'success': True, 'message': 'Candidate deleted successfully'})

    except Exception as e:
        print(f"Error deleting candidate: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/logout")
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('home'))

@app.route("/candidate/login", methods=['GET', 'POST'])
def candidate_login():
    """Handle candidate login for technical test"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        candidate = db.get_candidate(email, password)
        if candidate:
            # Store only essential data in session to avoid cookie size limits
            session['user_id'] = candidate['id']
            session['user_type'] = "candidate"
            session['username'] = candidate['username']
            flash('Login successful!', 'success')
            return redirect(url_for('candidate_test'))
        else:
            flash('Invalid credentials', 'error')
            return redirect(request.url)

    # Pre-fill email if provided in URL
    prefilled_email = request.args.get('email', '')
    return render_template('candidate_login.html', prefilled_email=prefilled_email)

@app.route("/candidate/test")
def candidate_test():
    """Display candidate technical test"""
    if 'user_id' not in session or session.get('user_type') != 'candidate':
        flash('Please login first', 'error')
        return redirect(url_for('candidate_login'))

    # Get candidate data from database using user_id
    candidate_id = session['user_id']
    candidate = db.get_candidate_by_id(candidate_id)
    if not candidate:
        flash('Candidate data not found', 'error')
        return redirect(url_for('candidate_login'))

    # Get test questions
    questions_text = candidate.get('questions', '')
    if questions_text:
        # Parse questions
        questions = [q.strip() for q in questions_text.split('\n\n') if q.strip()]
        return render_template('candidate_test.html', candidate=candidate, questions=questions)
    else:
        flash('No test questions found. Please wait for the recruiter to send you a test invitation.', 'error')
        return redirect(url_for('jobs'))

@app.route("/candidate/submit-test", methods=['POST'])
def submit_candidate_test():
    """Handle candidate test submission"""
    if 'user_id' not in session or session.get('user_type') != 'candidate':
        flash('Please login first', 'error')
        return redirect(url_for('candidate_login'))

    # Get candidate data from database
    candidate_id = session['user_id']
    candidate = db.get_candidate_by_id(candidate_id)
    if not candidate:
        flash('Candidate data not found', 'error')
        return redirect(url_for('candidate_login'))

    # Get test questions
    questions_text = candidate.get('questions', '')
    if not questions_text:
        flash('No test questions found', 'error')
        return redirect(url_for('candidate_test'))

    # Parse questions
    questions = [q.strip() for q in questions_text.split('\n\n') if q.strip()]

    # Get user answers
    user_answers = {}
    for i, question in enumerate(questions, 1):
        answer_key = f'answer_{i}'
        user_answers[question] = request.form.get(answer_key, '')

    # Get correct answers
    correct_answers = {}
    if candidate.get('correct_answers'):
        try:
            import json
            stored_answers = json.loads(candidate['correct_answers'])
            print(f"🔍 DEBUG - Stored correct answers: {stored_answers}")
            # Match stored answers to current questions
            for question in questions:
                if question in stored_answers:
                    correct_answers[question] = stored_answers[question]
                    print(f"🔍 DEBUG - Matched answer for question: {question[:50]}...")
                else:
                    print(f"⚠️ DEBUG - No stored answer for question: {question[:50]}...")
        except Exception as e:
            print(f"❌ DEBUG - Error parsing correct answers: {e}")
            correct_answers = {}

    # If no stored answers, generate them on the fly
    if not correct_answers:
        print("🔄 DEBUG - No stored answers found, generating on the fly...")
        try:
            # Build knowledge base for answer generation
            pdf_files_info = get_pdf_files_info()
            if pdf_files_info:
                index, texts = build_vector_store_cached(tuple(
                    (pdf['name'], pdf['size'], pdf['mtime']) for pdf in pdf_files_info
                ))
            else:
                index, texts = None, []

            # Generate answers for each question
            for question in questions:
                try:
                    if index and texts:
                        answer = generate_answer_for_question(question, index, texts)
                    else:
                        answer = f"Réponse par défaut pour: {question[:50]}..."
                    correct_answers[question] = answer
                    print(f"✅ DEBUG - Generated answer for: {question[:50]}...")
                except Exception as e:
                    correct_answers[question] = f"Erreur génération: {e}"
                    print(f"❌ DEBUG - Error generating answer: {e}")
        except Exception as e:
            print(f"❌ DEBUG - Error in answer generation: {e}")
            # Fallback: simple default answers
            for question in questions:
                correct_answers[question] = "Réponse par défaut - génération échouée"

    # Evaluate answers
    try:
        print(f"🔍 DEBUG EVALUATION - Starting evaluation for {len(user_answers)} answers")
        print(f"🔍 DEBUG EVALUATION - User answers: {user_answers}")
        print(f"🔍 DEBUG EVALUATION - Correct answers: {correct_answers}")

        evaluation_results = evaluate_answers(user_answers, correct_answers)

        print(f"🔍 DEBUG EVALUATION - Results: {evaluation_results}")

        # Calculate average score
        scores = [res['score'] for res in evaluation_results.values() if isinstance(res.get('score'), (int, float))]
        average_score = sum(scores) / len(scores) if scores else 0.0

        print(f"🔍 DEBUG EVALUATION - Scores: {scores}")
        print(f"🔍 DEBUG EVALUATION - Average score: {average_score}")

        # Format answers text
        answers_text = "\n\n".join([
            f"Question {i+1}: {q}\nAnswer: {user_answers[q]}"
            for i, q in enumerate(questions)
        ])

        # Save to database
        db.update_candidate_evaluation(
            candidate['id'],
            answers_text,
            correct_answers,
            evaluation_results,
            average_score
        )

        print(f"✅ DEBUG EVALUATION - Successfully saved evaluation for candidate {candidate['id']}")

        # Send detailed notification to recruiter with correct answers and justifications
        recruiter_email = db.get_recruiter_email_by_candidate(candidate['id'])
        if recruiter_email:
            subject = f"Test Completed - {candidate['username']} - Score: {average_score:.2f}/10"

            # Build detailed results section
            detailed_results = ""
            for i, question in enumerate(questions, 1):
                result = evaluation_results.get(question, {})
                user_answer = result.get('user', 'N/A')
                correct_answer = result.get('correct', 'N/A')
                score = result.get('score', 0)
                justification = result.get('justification', 'N/A')

                print(f"🔍 DEBUG EMAIL - Question {i}: score={score}, justification='{justification[:50]}...'")

                detailed_results += f"""

QUESTION {i}: {question[:100]}{'...' if len(question) > 100 else ''}

CANDIDATE'S ANSWER:
{user_answer}

CORRECT ANSWER:
{correct_answer}

SCORE: {score:.2f}/1.0
JUSTIFICATION: {justification}

{'─' * 80}"""

            body = f"""Dear Recruiter,

The candidate {candidate['username']} ({candidate['email']}) has completed their technical test.

TEST RESULTS SUMMARY:
- Average Score: {average_score:.2f}/10 ({average_score*10:.1f}%)
- Questions Answered: {len(questions)}
- Test Completed: {candidate.get('test_completed_at', 'N/A')}

DETAILED RESULTS:{detailed_results}

Please log in to the recruiter dashboard to view the complete evaluation and manage this candidate.

Best regards,
Recruitment System"""

            email_sent = send_email(recruiter_email, subject, body)
            if email_sent:
                print(f"✅ DEBUG EMAIL - Successfully sent detailed results to {recruiter_email}")
            else:
                print(f"❌ DEBUG EMAIL - Failed to send email to {recruiter_email}")

        flash('Test submitted successfully!', 'success')

        # Clear session
        session.clear()

        return redirect(url_for('home'))

    except Exception as e:
        flash(f'Error submitting test: {str(e)}', 'error')
        return redirect(url_for('candidate_test'))


@app.route("/apply/<int:job_id>", methods=['GET', 'POST'])
def apply_for_job(job_id):
    print(f"🎯 DEBUG - Apply route called for job {job_id} with method {request.method}")
    print(f"🔄 DEBUG - Route /apply/{job_id} called with method: {request.method}")
    print(f"📋 DEBUG - Request headers: {dict(request.headers)}")
    print(f"📝 DEBUG - Request content type: {request.content_type}")
    print(f"🔍 DEBUG - Request data length: {request.content_length}")

    job = db.get_job_by_id(job_id)
    if not job:
        print(f"❌ DEBUG - Job {job_id} not found")
        flash('Offre d\'emploi introuvable', 'error')
        return redirect(url_for('jobs'))

    print(f"✅ DEBUG - Job found: {job['title']} at {job['company_name']}")

    if request.method == 'POST':
        print("📝 DEBUG - Form submission detected")
        print(f"   Form data keys: {list(request.form.keys())}")
        print(f"   Files keys: {list(request.files.keys())}")

        try:
            # Get form data
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            cover_letter = request.form.get('cover_letter')

            print(f"   📋 RAW Form data received:")
            print(f"      Raw name: '{request.form.get('name')}'")
            print(f"      Raw email: '{request.form.get('email')}'")
            print(f"      Raw phone: '{request.form.get('phone')}'")
            print(f"      Raw cover_letter: '{request.form.get('cover_letter')}'")

            print(f"   📋 Processed Form data:")
            print(f"      Name: '{name}' (type: {type(name)})")
            print(f"      Email: '{email}' (type: {type(email)})")
            print(f"      Phone: '{phone}' (type: {type(phone)})")
            print(f"      Cover letter: '{cover_letter[:50] if cover_letter else 'None'}...' (length: {len(cover_letter) if cover_letter else 0})")

            # Get uploaded file
            resume_file = request.files.get('resume')
            print(f"   📄 Resume file details:")
            print(f"      File object: {resume_file}")
            if resume_file:
                print(f"      Filename: '{resume_file.filename}'")
                print(f"      Content type: '{resume_file.content_type}'")
                print(f"      File size: {len(resume_file.read()) if resume_file else 0} bytes")
                resume_file.seek(0)  # Reset file pointer
            else:
                print(f"      No file uploaded")

            if not name or not email or not resume_file:
                flash('Veuillez remplir tous les champs obligatoires', 'error')
                return redirect(request.url)

            # Process the resume
            file_content = resume_file.read()
            file_name = resume_file.filename

            # Parse and preprocess CV
            cv_text, cv_data = process_cv_cached(file_content, file_name)

            if cv_data:
                # Initialize generated_password variable
                generated_password = None
    
                # Check if candidate already exists
                existing_candidate = db.get_candidate_by_email(email)
                if existing_candidate:
                    candidate_id = existing_candidate['id']
                    # Update candidate's recruiter association if different
                    if existing_candidate['recruiter_id'] != job['recruiter_id']:
                        print(f"🔄 Updating candidate {candidate_id} recruiter from {existing_candidate['recruiter_id']} to {job['recruiter_id']}")
                        conn = db.get_db_connection()
                        cur = conn.cursor()
                        if db.DB_TYPE == 'sqlite':
                            cur.execute("UPDATE candidates SET recruiter_id = ? WHERE id = ?", (job['recruiter_id'], candidate_id))
                        else:
                            cur.execute("UPDATE candidates SET recruiter_id = %s WHERE id = %s", (job['recruiter_id'], candidate_id))
                        conn.commit()
                        cur.close()
                        conn.close()

                    # Ensure candidate has a password for test access
                    if not existing_candidate.get('password'):
                        # Generate password if missing
                        generated_password = db.generate_password()
                        # Update candidate with password
                        conn = db.get_db_connection()
                        cur = conn.cursor()
                        if db.DB_TYPE == 'sqlite':
                            cur.execute("UPDATE candidates SET password = ? WHERE id = ?", (generated_password, candidate_id))
                        else:
                            cur.execute("UPDATE candidates SET password = %s WHERE id = %s", (generated_password, candidate_id))
                        conn.commit()
                        cur.close()
                        conn.close()
                    else:
                        # Use existing password for email
                        generated_password = existing_candidate.get('password')
                else:
                    # Create job matching info for the candidate
                    job_matching_info = f"Applied to: {job['title']} at {job['company_name']} - {job['location']} ({job['type']})"

                    # Create new candidate with generated password
                    generated_password = db.generate_password()
                    candidate_added, _ = db.add_candidate(name, email, job_matching_info, "", job['recruiter_id'])
                    if candidate_added:
                        candidate = db.get_candidate_by_email(email)
                        candidate_id = candidate['id']
                    else:
                        flash('Erreur lors de la création du profil candidat', 'error')
                        return redirect(request.url)

                # Check if already applied for this job
                existing_resume = db.get_resume_by_candidate_and_job(candidate_id, job_id)
                if existing_resume:
                    flash(f'Vous avez déjà postulé pour cette offre.', 'warning')
                    return redirect(url_for('jobs'))

                # Save resume to database
                extracted_data_json = json.dumps(cv_data) if cv_data else "{}"
                db.add_resume(candidate_id, job['recruiter_id'], job_id, cv_text, extracted_data_json)

                # Send confirmation email to candidate
                subject = f"Candidature reçue - {job['title']}"
                body = f"""Bonjour {name},

Merci d'avoir postulé au poste de {job['title']} chez {job['company_name']}.

Votre candidature a été reçue et est en cours de traitement.

Vos identifiants de connexion :
Email: {email}
Mot de passe: {generated_password}

Vous recevrez bientôt un email avec le lien vers votre test technique personnalisé.

Cordialement,
L'équipe de recrutement
{job['company_name']}"""

                print("📧 DEBUG - About to send confirmation email:")
                print(f"   To: {email}")
                print(f"   Subject: {subject}")
                print(f"   Body preview: {body[:100]}...")

                email_sent = send_email(email, subject, body)
                if not email_sent:
                    print("❌ Failed to send confirmation email to candidate")
                    flash('Candidature enregistrée mais email de confirmation non envoyé. Vérifiez la configuration email.', 'warning')
                else:
                    print("✅ Confirmation email sent successfully")

                flash(f'✅ Merci {name}! Votre candidature pour "{job["title"]}" a été soumise avec succès.', 'success')

                # Send notification to recruiter
                recruiter_email = db.get_recruiter_email_by_candidate(candidate_id)
                if recruiter_email:
                    recruiter_subject = f"Nouvelle candidature - {job['title']}"
                    recruiter_body = f"""Bonjour,

Une nouvelle candidature a été reçue pour le poste "{job['title']}".

Candidat: {name}
Email: {email}
Téléphone: {phone or 'Non fourni'}

Compétences détectées: {', '.join(cv_data.get('skills', [])[:5])}

Veuillez vous connecter à votre tableau de bord pour consulter le CV complet.

Cordialement,
Système de recrutement automatisé"""

                    print("📧 DEBUG - About to send recruiter notification:")
                    print(f"   To: {recruiter_email}")
                    print(f"   Subject: {recruiter_subject}")
                    print(f"   Body preview: {recruiter_body[:100]}...")

                    recruiter_email_sent = send_email(recruiter_email, recruiter_subject, recruiter_body)
                    if not recruiter_email_sent:
                        print("❌ Failed to send notification email to recruiter")
                        flash('Candidature enregistrée mais notification recruteur non envoyée.', 'warning')
                    else:
                        print("✅ Recruiter notification email sent successfully")

                return redirect(url_for('jobs'))
            else:
                flash('❌ Impossible d\'analyser votre CV. Assurez-vous qu\'il s\'agit d\'un fichier PDF ou DOCX valide.', 'error')
                return redirect(request.url)

        except Exception as e:
            print(f"Erreur lors du traitement de la candidature: {e}")
            flash(f'❌ Erreur lors du traitement: {str(e)}', 'error')
            return redirect(request.url)

    return render_template('apply.html', job=job)

@app.route("/recruiter/<int:recruiter_id>")
def recruiter_profile(recruiter_id):
    recruiter = db.get_recruiter_by_id(recruiter_id)
    if not recruiter:
        flash('Recruteur introuvable', 'error')
        return redirect(url_for('jobs'))

    jobs = db.get_jobs_by_recruiter(recruiter_id)
    total_jobs = len(jobs) if jobs else 0

    # Get total applications
    total_applications = 0
    if jobs:
        for job in jobs:
            applications = db.get_resumes_by_job(job['id'])
            if applications:
                total_applications += len(applications)

    return render_template("recruiter_profile.html",
                          recruiter=recruiter,
                          jobs=jobs,
                          total_jobs=total_jobs,
                          total_applications=total_applications)

@app.route("/recruiter/send-test", methods=['POST'])
def send_test_to_applicant():
    """Send test invitation to individual applicant"""
    if 'user' not in session or session.get('user_type') != 'recruiter':
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    data = request.get_json()
    application_id = data.get('application_id')
    email = data.get('email')
    username = data.get('username')
    job_title = data.get('job_title')

    if not all([application_id, email, username, job_title]):
        return jsonify({'success': False, 'error': 'Missing required data'}), 400

    try:
        # Get candidate by email (since we have the email from the application)
        candidate = db.get_candidate_by_email(email)
        if not candidate:
            return jsonify({'success': False, 'error': 'Candidate not found'}), 404

        # Generate questions for this job
        questions, correct_answers = generate_interview_content()
        questions_text = "\n\n".join([f"Question {i+1}: {q}" for i, q in enumerate(questions, 1)])

        print(f"🔍 DEBUG - Generated {len(questions)} questions and {len(correct_answers)} answers")
        print(f"🔍 DEBUG - Sample question: {questions[0][:100] if questions else 'None'}...")
        print(f"🔍 DEBUG - Sample answer: {list(correct_answers.values())[0][:100] if correct_answers else 'None'}...")

        # Update candidate with questions and correct answers
        db.update_candidate_questions(candidate['id'], questions_text, correct_answers)

        # Check if candidate already has a password
        if not candidate.get('password'):
            return jsonify({'success': False, 'error': 'Candidate password not found'}), 404

        # Generate test link
        test_link = f"http://localhost:5000/candidate/login?email={email}"

        subject = f"Technical Interview Test - {job_title} Position"
        body = f"""Dear {username},

Congratulations! You have been selected to take the technical interview test for the {job_title} position.

Your test credentials:
Email: {email}
Password: {candidate['password']}

Please click the link below to access your test:
{test_link}

Instructions:
1. Click the link above
2. Log in with your email and password
3. Complete the technical exercises
4. Submit your answers

The test consists of {len(questions)} programming exercises. You will have time to solve each problem and submit your code.

Good luck!

Best regards,
Recruitment Team"""

        # Send email
        email_sent = send_email(email, subject, body)
        if email_sent:
            return jsonify({'success': True, 'message': 'Test invitation sent successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to send email'}), 500

    except Exception as e:
        print(f"Error sending test to applicant: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/recruiter/delete-job/<int:job_id>", methods=['POST'])
def delete_job(job_id):
    """Delete a job posting"""
    if 'user' not in session or session.get('user_type') != 'recruiter':
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    recruiter = session['user']
    recruiter_id = recruiter.get('id') if isinstance(recruiter, dict) else recruiter['id']

    try:
        # Get the job to verify ownership
        job = db.get_job_by_id(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404

        if job['recruiter_id'] != recruiter_id:
            return jsonify({'success': False, 'error': 'Not authorized to delete this job'}), 403

        # Delete the job
        db.delete_job(job_id)

        return jsonify({'success': True, 'message': 'Job deleted successfully'})

    except Exception as e:
        print(f"Error deleting job: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== UTILITY FUNCTIONS ==========
def process_cv_cached(file_content, file_name):
    """Cache le traitement du CV pour éviter la répétition avec gestion d'erreur Google Gemini"""
    cv_text = parse_cv_from_content(file_content, file_name)
    if not cv_text.strip():
        return None, None

    try:
        cv_data = preprocess_cv(cv_text)

        # ✅ Si preprocess_cv renvoie du JSON en string, on convertit en dict
        if isinstance(cv_data, str):
            try:
                cv_data = json.loads(cv_data)
            except:
                cv_data = {}

        return cv_text, cv_data

    except Exception as e:
        error_message = str(e)
        print(f"⚠️  Error processing CV with AI: {error_message}")

        # Check if it's a quota exceeded error
        if "429" in error_message or "quota" in error_message.lower() or "rate limit" in error_message.lower():
            print("🔄 Google Gemini quota exceeded - using fallback processing")
            print("💡 To fix this:")
            print("   1. Go to https://makersuite.google.com/app/apikey")
            print("   2. Create or get your Google AI API key")
            print("   3. Add GOOGLE_API_KEY=your_key_here to your .env file")
            print("   4. Or wait for quota reset (usually 24 hours)")

            # Fallback: Create basic CV data structure
            fallback_cv_data = {
                "skills": ["python", "programming"],  # Default skills
                "experience": "Entry level",
                "education": "Bachelor's degree"
            }

            print("✅ Using fallback CV processing - limited functionality")
            return cv_text, fallback_cv_data
        else:
            print("❌ Unexpected error in CV processing")
            return cv_text, None

def parse_cv_from_content(file_content, file_name):
    """Parse CV à partir du contenu binaire"""
    import io
    file_obj = io.BytesIO(file_content)
    file_obj.name = file_name
    return parse_cv(file_obj)

def process_job_matching(cv_data, jobs_data):
    """Filtrer et scorer les jobs qui matchent avec le CV"""
    # 🔧 Étape 1 : normaliser les jobs
    flat_jobs = []
    for job in jobs_data:
        if isinstance(job, dict) and "skills" in job:
            flat_jobs.append(job)
        elif isinstance(job, dict) and "jobs" in job:
            for subjob in job["jobs"]:
                subjob = subjob.copy()
                subjob["company_name"] = job["company"]
                subjob["url"] = subjob.get("url", job.get("url"))
                flat_jobs.append(subjob)

    # ✅ Normalisation des skills
    cv_data["skills"] = [s.lower() for s in cv_data.get("skills", [])]
    for job in flat_jobs:
        if "skills" in job and isinstance(job["skills"], list):
            job["skills"] = [s.lower() for s in job["skills"]]

    # 🔧 Étape 2 : calculer les scores pour tous les jobs
    from matching import compute_score
    scored_jobs = []
    for job in flat_jobs:
        score, matched_skills = compute_score(cv_data, job.get("skills", []))
        if score > 0:  # Seulement les jobs avec au moins un match
            job_copy = job.copy()
            job_copy["match_score"] = score
            job_copy["matched_skills"] = matched_skills
            scored_jobs.append(job_copy)

    # 🔧 Étape 3 : trier par score décroissant et prendre top 3
    scored_jobs.sort(key=lambda j: j["match_score"], reverse=True)
    return scored_jobs[:3]

@app.route("/debug/evaluation")
def debug_evaluation():
    """Debug route to test evaluation system"""
    from agent import test_evaluation

    try:
        score, justification = test_evaluation()
        return jsonify({
            "success": True,
            "score": score,
            "justification": justification
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

if __name__ == "__main__":
    app.run(port=5000,host="0.0.0.0" ,debug=True)
