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

app = Flask(__name__)
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

    candidates = db.get_candidates_by_recruiter(recruiter_id)
    jobs = db.get_jobs_by_recruiter(recruiter_id)

    return render_template("recruiter_dashboard.html",
                         recruiter=recruiter,
                         candidates=candidates,
                         jobs=jobs)

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
            session['user'] = candidate
            session['user_type'] = "candidate"
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
    if 'user' not in session or session.get('user_type') != 'candidate':
        flash('Please login first', 'error')
        return redirect(url_for('candidate_login'))

    candidate = session['user']

    # Get test questions
    questions_text = candidate.get('questions', '')
    if questions_text:
        # Parse questions
        questions = [q.strip() for q in questions_text.split('\n\n') if q.strip()]
        return render_template('candidate_test.html', candidate=candidate, questions=questions)
    else:
        flash('No test questions found', 'error')
        return redirect(url_for('jobs'))

@app.route("/candidate/submit-test", methods=['POST'])
def submit_candidate_test():
    """Handle candidate test submission"""
    if 'user' not in session or session.get('user_type') != 'candidate':
        flash('Please login first', 'error')
        return redirect(url_for('candidate_login'))

    candidate = session['user']

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
            # Match stored answers to current questions
            for question in questions:
                if question in stored_answers:
                    correct_answers[question] = stored_answers[question]
        except:
            correct_answers = {}

    # Evaluate answers
    try:
        evaluation_results = evaluate_answers(user_answers, correct_answers)

        # Calculate average score
        scores = [res['score'] for res in evaluation_results.values() if isinstance(res.get('score'), (int, float))]
        average_score = sum(scores) / len(scores) if scores else 0.0

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

        # Send notification to recruiter
        recruiter_email = db.get_recruiter_email_by_candidate(candidate['id'])
        if recruiter_email:
            subject = f"Test Completed - {candidate['username']}"
            body = f"""Dear Recruiter,

The candidate {candidate['username']} ({candidate['email']}) has completed their technical test.

Test Results Summary:
- Average Score: {average_score:.2f}
- Questions Answered: {len(questions)}

Please log in to the recruiter dashboard to view detailed results.

Best regards,
Recruitment System"""

            send_email(recruiter_email, subject, body)

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

if __name__ == "__main__":
    app.run(port=5000, debug=True)
