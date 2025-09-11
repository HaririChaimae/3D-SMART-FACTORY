import os
from dotenv import load_dotenv
load_dotenv()
import json
import streamlit as st
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

logger = logging.getLogger(__name__)
GEN_MODEL = "gemini-1.5-flash"  # or whatever model you're using

db.create_tables()


def send_email(to_email, subject, body):
    print(f"Attempting to send email to: {to_email}")
    print(f"Subject: {subject}")
    print(f"From: {os.environ.get('EMAIL_USER', 'noreply@example.com')}")

    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = os.environ.get('EMAIL_USER', 'noreply@example.com')
        msg['To'] = to_email

        print("Connecting to Gmail SMTP...")
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            print("TLS connection established")

            print("Attempting login...")
            server.login(os.environ.get('EMAIL_USER'), os.environ.get('EMAIL_PASSWORD'))
            print("Login successful")

            print("Sending email...")
            server.sendmail(msg['From'], to_email, msg.as_string())
            print(f"EMAIL SENT SUCCESSFULLY TO {to_email}")

    except smtplib.SMTPAuthenticationError as e:
        print(f"AUTHENTICATION FAILED: {e}")
        print("Check your App Password or 2FA settings")
    except smtplib.SMTPConnectError as e:
        print(f"CONNECTION FAILED: {e}")
        print("Check your internet connection")
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        print("Email content that would have been sent:")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Body: {body[:200]}...")

# ========== QUESTION GENERATION ==========
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
    - N’utilisez pas de saisie avec input(). Les exercices doivent définir les valeurs d’entrée sous forme
    de variables ou de paramètres déjà fournis, jamais par interaction utilisateur.
    """

    try:
        model = genai.GenerativeModel(GEN_MODEL)
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Split on "Exercice :" and keep everything together
        raw_exercises = re.split(r"(?=Exercice\s*:)", text)
        questions = [ex.strip() for ex in raw_exercises if ex.strip()]

        return questions[:n]
    except Exception as e:
        logger.error(f"Error generating questions: {e}")
        # Fallback: generate questions directly from PDF content
        return generate_questions_from_pdf_fallback(n)

def generate_questions_from_pdf_fallback(n=3):
    """Generate questions directly from PDF content when API fails"""
    try:
        from agent import extract_text_from_pdf
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
        logger.error(f"Error in PDF fallback: {e}")

    return []

# ========== CODE EDITOR WITH EXECUTION ==========
def jupyter_style_editor(key, default_code=""):
    """Crée un éditeur de code style Jupyter avec exécution"""

    # Only show styles once to avoid duplication
    if not hasattr(st.session_state, 'styles_shown'):
        st.markdown(f"""
        <style>
            .jupyter-cell {{
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                margin-bottom: 20px;
                background-color: #fafafa;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .code-header {{
                background-color: #f5f5f5;
                padding: 8px 12px;
                border-bottom: 1px solid #e0e0e0;
                font-family: monospace;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }}
            .code-language {{
                font-weight: bold;
                color: #388e3c;
            }}
            .code-area {{
                background-color: #fafafa;
                color: #333;
                font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                width: 100%;
                min-height: 200px;
                padding: 12px;
                border: none;
                resize: vertical;
                white-space: pre;
                overflow-x: auto;
                line-height: 1.4;
                tab-size: 4;
            }}
            .code-area:focus {{
                outline: none;
                box-shadow: inset 0 0 0 2px #2196f3;
            }}
            .run-button {{
                background-color: #4caf50;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.9em;
            }}
            .run-button:hover {{
                background-color: #388e3c;
            }}
            .output-area {{
                background-color: black;
                border-top: 1px solid #e0e0e0;
                padding: 12px;
                font-family: monospace;
                white-space: pre-wrap;
                max-height: 300px;
                overflow-y: auto;
            }}
            .output-error {{
                color: #d32f2f;
            }}
        </style>
        """, unsafe_allow_html=True)
        st.session_state.styles_shown = True

    # Conteneur principal
    st.markdown(f'<div class="jupyter-cell">', unsafe_allow_html=True)

    # En-tête avec bouton d'exécution
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f'<div class="code-language">Python</div>', unsafe_allow_html=True)
    with col2:
        run_clicked = st.button("▶️ Exécuter", key=f"run_{key}", width='stretch')

    # Éditeur de code
    code = st.text_area(
        "Code Editor",
        value=default_code,
        height=250,
        key=f"code_{key}",
        label_visibility="collapsed"
    )

    # Zone de sortie
    output_key = f"output_{key}"
    if output_key not in st.session_state:
        st.session_state[output_key] = ""

    # Exécution du code seulement si le bouton est cliqué
    if run_clicked and code.strip():
        with st.spinner("Exécution en cours..."):
            output = execute_code(code)
            st.session_state[output_key] = output

    # Afficher la sortie seulement si elle existe
    if st.session_state.get(output_key, ""):
        output_class = "output-area output-error" if "Error" in st.session_state[output_key] else "output-area"
        st.markdown(f'<div class="{output_class}">{st.session_state[output_key]}</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    return code

@st.cache_data
def execute_code(code):
    """Exécute le code Python et retourne la sortie"""
    try:
        # Capturer la sortie standard
        output_capture = StringIO()
        with contextlib.redirect_stdout(output_capture), contextlib.redirect_stderr(output_capture):
            # Exécuter le code
            exec(code, {})

        output = output_capture.getvalue()
        if not output:
            output = "# Code exécuté avec succès (aucune sortie)"

        return output
    except Exception as e:
        return f"Error: {str(e)}\n\n{traceback.format_exc()}"

from parsing import parse_cv
from pathlib import Path

# === Configuration Streamlit ===
st.set_page_config(page_title="Entretien Automatisé", page_icon="🤖", layout="centered")

# Add Font Awesome icons and custom styles
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    .icon-large { font-size: 1.5em; margin-right: 10px; vertical-align: middle; }
    .icon-medium { font-size: 1.2em; margin-right: 8px; vertical-align: middle; }
    .icon-small { font-size: 1em; margin-right: 5px; vertical-align: middle; }
    
    /* Simple button styles */
    .stButton > button {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
    }
    
    /* Success/Warning/Error icons */
    .success-icon { color: #28a745; }
    .warning-icon { color: #ffc107; }
    .error-icon { color: #dc3545; }
    .info-icon { color: #17a2b8; }
    
    /* Header styles */
    .main-title {
        display: flex;
        align-items: center;
        margin-bottom: 20px;
    }
    
    .section-header {
        display: flex;
        align-items: center;
        margin: 20px 0 10px 0;
    }
    
    /* Simple styling */
    .stButton > button {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
    }

    /* Recruiter profile styling */
    .recruiter-profile {
        display: flex;
        align-items: center;
        margin-bottom: 15px;
        padding: 12px;
        background: #0e1117;
        border-radius: 8px;
        border: 1px solid #30363d;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
    }

    .recruiter-profile:hover {
        border-color: #58a6ff;
        box-shadow: 0 4px 8px rgba(88, 166, 255, 0.2);
    }

    .recruiter-avatar {
        width: 45px;
        height: 45px;
        border-radius: 50%;
        object-fit: cover;
        margin-right: 12px;
        border: 2px solid #58a6ff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }

    .recruiter-info h4 {
        margin: 0;
        color: #f0f6fc;
        font-size: 1.1em;
        font-weight: 600;
        cursor: pointer;
        transition: color 0.3s ease;
    }

    .recruiter-info h4:hover {
        color: #58a6ff;
    }

    .recruiter-info p {
        margin: 2px 0;
        font-size: 0.9em;
        color: #8b949e;
    }

    .recruiter-default-avatar {
        width: 45px;
        height: 45px;
        border-radius: 50%;
        background: #30363d;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 12px;
        border: 2px solid #58a6ff;
        color: #f0f6fc;
        font-size: 1.3em;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_jobs_data(jobs_file_path):
    """Cache le chargement des jobs"""
    with open(jobs_file_path, "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def process_cv_cached(file_content, file_name):
    """Cache le traitement du CV pour éviter la répétition"""
    cv_text = parse_cv_from_content(file_content, file_name)
    if not cv_text.strip():
        return None, None
    cv_data = preprocess_cv(cv_text)
    return cv_text, cv_data

def parse_cv_from_content(file_content, file_name):
    """Parse CV à partir du contenu binaire"""
    import io
    file_obj = io.BytesIO(file_content)
    file_obj.name = file_name
    return parse_cv(file_obj)

@st.cache_data
def process_job_matching(cv_data, jobs_data):
    """Cache le matching des jobs"""
    return match_jobs(cv_data, jobs_data)

# ========== FONCTIONS CACHÉES ==========
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

@st.cache_data
def build_vector_store_cached(pdf_files_info):
    """Cache la construction du vector store basé sur les infos des PDFs"""
    if not pdf_files_info:
        st.warning("Aucun PDF trouvé dans le dossier \"data\"")
        return None, []

    with st.spinner('Construction de la base de connaissances...'):
        index, texts = build_vector_store()

    if index is None:
        st.error("Impossible de construire la base de connaissances")
        return None, []

    st.success(f'Base de connaissances construite avec {len(texts)} documents')
    return index, texts

@st.cache_data
def generate_interview_content():
    """Génère les questions à partir de la base de connaissances"""
    # Obtenir les infos des PDFs pour le cache
    pdf_files_info = get_pdf_files_info()

    if not pdf_files_info:
        knowledge_chunks = []
        index, texts = None, []
    else:
        # Construire le vector store (avec cache)
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
            correct_answers[q] = f"Réponse par défaut - erreur de génération"

    return questions, correct_answers

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None
    st.session_state.user_type = None
    st.session_state.initialized = True

# Check for URL parameters (for candidate login link and recruiter profile)
query_params = st.query_params
if 'email' in query_params:
    candidate = db.get_candidate_by_email(query_params['email'])
    if candidate:
        if 'mode' not in st.session_state or st.session_state.mode != 'candidate_login':
            st.session_state.user = None
            st.session_state.user_type = None
            st.session_state.mode = 'candidate_login'
            st.session_state.candidate_email = query_params['email']

# Check for recruiter profile view
if 'recruiter' in query_params:
    recruiter_id = query_params['recruiter']
    try:
        recruiter_id = int(recruiter_id)
        recruiter = db.get_recruiter_by_id(recruiter_id)
        if recruiter:
            if 'mode' not in st.session_state or st.session_state.mode != 'recruiter_profile':
                st.session_state.user = None
                st.session_state.user_type = None
                st.session_state.mode = 'recruiter_profile'
                st.session_state.profile_recruiter = recruiter
    except ValueError:
        pass

if st.session_state.user is None:
    # Check if this is a recruiter profile view
    if 'mode' in st.session_state and st.session_state.mode == 'recruiter_profile':
        recruiter = st.session_state.get('profile_recruiter', {})

        # Show recruiter profile page
        st.markdown('<div class="main-title"><i class="fas fa-user-tie icon-large"></i><h1 style="margin: 0;">Recruiter Profile</h1></div>', unsafe_allow_html=True)

        # Simple profile header without cover photo
        if recruiter.get('profile_picture'):
            st.markdown(f"""
            <div style="display: flex; align-items: center; margin-bottom: 30px; padding: 20px; background: #000000; border-radius: 15px; color: white; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
                <img src="data:image/png;base64,{recruiter['profile_picture']}" style="width: 120px; height: 120px; border-radius: 50%; object-fit: cover; margin-right: 25px; border: 4px solid white; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                <div>
                    <h1 style="margin: 0; font-size: 2.5em; color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);">{recruiter['username']}</h1>
                    <p style="margin: 8px 0; font-size: 1.2em; opacity: 0.9; color: #e0e0e0;">Senior Recruiter</p>
                    <p style="margin: 5px 0; font-size: 1.1em; color: #cccccc;"><i class="fas fa-envelope"></i> {recruiter['email']}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="display: flex; align-items: center; margin-bottom: 30px; padding: 20px; background: #000000; border-radius: 15px; color: white; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
                <div style="width: 120px; height: 120px; border-radius: 50%; background: rgba(255,255,255,0.2); display: flex; align-items: center; justify-content: center; margin-right: 25px; border: 4px solid white; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                    <i class="fas fa-user-tie" style="font-size: 3em; color: white;"></i>
                </div>
                <div>
                    <h1 style="margin: 0; font-size: 2.5em; color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);">{recruiter['username']}</h1>
                    <p style="margin: 8px 0; font-size: 1.2em; opacity: 0.9; color: #e0e0e0;">Senior Recruiter</p>
                    <p style="margin: 5px 0; font-size: 1.1em; color: #cccccc;"><i class="fas fa-envelope"></i> {recruiter['email']}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Get recruiter's job statistics
        jobs = db.get_jobs_by_recruiter(recruiter['id'])
        total_jobs = len(jobs) if jobs else 0

        # Get total applications for this recruiter
        total_applications = 0
        if jobs:
            for job in jobs:
                applications = db.get_resumes_by_job(job['id'])
                if applications:
                    total_applications += len(applications)

        # Statistics cards - Focus on jobs and applications
        st.markdown("### 📊 Recruiter Statistics")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Jobs Posted", total_jobs)
        with col2:
            st.metric("Total Applications", total_applications)

        # All job postings by this recruiter
        if jobs:
            st.markdown("### 💼 All Job Postings")
            for job in jobs:
                with st.expander(f"📋 {job['title']} at {job['company_name']}", expanded=False):
                    # Show job image if available
                    if job['job_image']:
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.image(f"data:image/png;base64,{job['job_image']}", width=150, caption="Job Image")
                        with col2:
                            st.write(f"**Location:** {job['location']}")
                            st.write(f"**Type:** {job['type']}")
                            st.write(f"**Posted:** {job['posted']}")
                            if job['salary_from']:
                                st.write(f"**Salary:** {job['salary_currency']} {job['salary_from']:,} - {job['salary_to']:,}")
                            if job['skills']:
                                st.write(f"**Skills:** {', '.join(job['skills'][:3])}...")
                    else:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Location:** {job['location']}")
                            st.write(f"**Type:** {job['type']}")
                            st.write(f"**Posted:** {job['posted']}")
                        with col2:
                            if job['salary_from']:
                                st.write(f"**Salary:** {job['salary_currency']} {job['salary_from']:,} - {job['salary_to']:,}")
                            if job['skills']:
                                st.write(f"**Skills:** {', '.join(job['skills'][:3])}...")

                    # Show job description
                    st.write(f"**Description:** {job['description'][:200]}..." if len(job['description']) > 200 else f"**Description:** {job['description']}")

                    # Show applications count for this job
                    applications = db.get_resumes_by_job(job['id'])
                    application_count = len(applications) if applications else 0
                    st.write(f"**Applications Received:** {application_count}")

        # Add link to go back to main site
        st.markdown("---")
        if st.button("← Back to Job Search"):
            st.session_state.mode = None
            st.session_state.profile_recruiter = None
            st.rerun()

    # Check if this is a candidate login link
    elif 'mode' in st.session_state and st.session_state.mode == 'candidate_login':
        candidate_email = st.session_state.get('candidate_email', '')

        # Show candidate login page directly
        st.markdown('<div class="main-title"><i class="fas fa-user-graduate icon-large"></i><h1 style="margin: 0;">Technical Interview Test</h1></div>', unsafe_allow_html=True)
        st.markdown("Please log in to access your technical interview test.")

        # Minimal login form - just inputs and button
        with st.form("candidate_login"):
            email = st.text_input("Email", value=candidate_email)
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login to Test")

            if submitted:
                candidate = db.get_candidate(email, password)
                if candidate:
                    st.session_state.user = candidate
                    st.session_state.user_type = "candidate"
                    st.rerun()  # Refresh to show the test
                else:
                    st.error("Invalid credentials. Please check your email for the correct password.")

        # Add link to go back to main site
        st.markdown("---")
        if st.button("← Back to Job Search"):
            st.session_state.mode = None
            st.session_state.candidate_email = None
            st.rerun()

    else:
        # Public Jobs Page with Login Option
        tab1, tab2 = st.tabs(["🔍 Browse Jobs", "🔐 Login"])

        with tab1:
            st.markdown('<div class="main-title"><i class="fas fa-briefcase icon-large"></i><h1 style="margin: 0;">Find Your Dream Job</h1></div>', unsafe_allow_html=True)
        st.markdown("Discover exciting opportunities from top companies")

        # Get all jobs for public browsing
        jobs = db.get_all_jobs()

        if jobs:
            # Search and filter options
            col1, col2, col3 = st.columns(3)
            with col1:
                search_term = st.text_input("Search jobs", placeholder="Job title, company, or skills")
            with col2:
                location_filter = st.selectbox("Location", ["All"] + list(set([job['location'] for job in jobs if job['location']])))
            with col3:
                type_filter = st.selectbox("Job Type", ["All"] + list(set([job['type'] for job in jobs if job['type']])))

            # Filter jobs
            filtered_jobs = jobs
            if search_term:
                filtered_jobs = [job for job in filtered_jobs if
                    search_term.lower() in job['title'].lower() or
                    search_term.lower() in job['company_name'].lower() or
                    (job['skills'] and any(search_term.lower() in skill.lower() for skill in job['skills'])) or
                    search_term.lower() in job['description'].lower()]

            if location_filter != "All":
                filtered_jobs = [job for job in filtered_jobs if job['location'] == location_filter]

            if type_filter != "All":
                filtered_jobs = [job for job in filtered_jobs if job['type'] == type_filter]

            st.markdown(f"**Found {len(filtered_jobs)} job(s)**")

            # Display jobs as posts
            for job in filtered_jobs:
                with st.container():
                    # Recruiter profile section - Circular image with small clickable name
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; margin-bottom: 15px;">
                        {'<img src="data:image/png;base64,' + job['recruiter_picture'] + '" style="width: 45px; height: 45px; border-radius: 50%; object-fit: cover; margin-right: 10px;">' if job.get('recruiter_picture') else '<div style="width: 45px; height: 45px; border-radius: 50%; background: #30363d; display: flex; align-items: center; justify-content: center; margin-right: 10px;"><i class="fas fa-user-tie" style="font-size: 1.3em; color: #f0f6fc;"></i></div>'}
                        <button onclick="window.location.href='?recruiter={job['recruiter_id']}'" style="background: none; border: none; color: #0066cc; cursor: pointer; font-size: 0.9em; font-weight: 600; padding: 0; text-decoration: underline; margin-right: 10px;">{job['recruiter_name']}</button>
                        <span style="font-size: 0.8em; color: #666;">Posted {job['posted']}</span>
                    </div>
                    """, unsafe_allow_html=True)

                    # Job post styling
                    if job['job_image']:
                        # Job with image
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.image(f"data:image/png;base64,{job['job_image']}", width='stretch')
                        with col2:
                            st.markdown(f"### {job['title']}")
                            st.markdown(f"**🏢 {job['company_name']}** • **📍 {job['location']}** • **💼 {job['type']}**")
                            st.markdown(f"**Posted:** {job['posted']}")
                            if job['salary_from']:
                                st.markdown(f"**💰 Salary:** {job['salary_currency']} {job['salary_from']:,} - {job['salary_to']:,}")
                            if job['skills']:
                                st.markdown(f"**🛠️ Skills:** {', '.join(job['skills'][:5])}")
                            st.markdown(job['description'][:200] + "..." if len(job['description']) > 200 else job['description'])
                    else:
                        # Job without image
                        st.markdown("---")
                        st.markdown(f"### {job['title']}")
                        st.markdown(f"**🏢 {job['company_name']}** • **📍 {job['location']}** • **💼 {job['type']}**")
                        st.markdown(f"**Posted:** {job['posted']}")
                        if job['salary_from']:
                            st.markdown(f"**💰 Salary:** {job['salary_currency']} {job['salary_from']:,} - {job['salary_to']:,}")
                        if job['skills']:
                            st.markdown(f"**🛠️ Skills:** {', '.join(job['skills'][:5])}")
                        st.markdown(job['description'][:300] + "..." if len(job['description']) > 300 else job['description'])

                    # Apply section - Always show internal application form
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown("**📝 Apply for this position**")
                    with col2:
                        if job['apply_url']:
                            st.markdown(f"[🔗 External Link]({job['apply_url']})")

                    # Create application form for direct application
                    with st.expander("📄 Submit Your Application", expanded=False):
                        with st.form(f"apply_{job['id']}"):
                            applicant_name = st.text_input("Full Name")
                            applicant_email = st.text_input("Email")
                            applicant_phone = st.text_input("Phone (optional)")
                            cover_letter = st.text_area("Cover Letter (optional)")
                            resume = st.file_uploader("Upload Resume", type=["pdf", "docx"], help="Upload your resume in PDF or DOCX format")

                            submitted = st.form_submit_button("🚀 Submit Application")
                            if submitted and applicant_name and applicant_email and resume:
                                try:
                                    # Process the resume
                                    file_content = resume.read()
                                    file_name = resume.name
                                    cv_text, cv_data = process_cv_cached(file_content, file_name)

                                    if cv_data:
                                        # Check if candidate already exists
                                        existing_candidate = db.get_candidate_by_email(applicant_email)
                                        if existing_candidate:
                                            candidate_id = existing_candidate['id']
                                            # Ensure candidate has a password for test access
                                            if not existing_candidate.get('password'):
                                                # Generate password if missing
                                                generated_password = db.generate_password()
                                                conn = db.get_db_connection()
                                                cur = conn.cursor()
                                                cur.execute("UPDATE candidates SET password = %s WHERE id = %s", (generated_password, candidate_id))
                                                conn.commit()
                                                cur.close()
                                                conn.close()
                                        else:
                                            # Create job matching info for the candidate
                                            job_matching_info = f"Applied to: {job['title']} at {job['company_name']} - {job['location']} ({job['type']})"

                                            # Create new candidate with generated password
                                            generated_password = db.generate_password()
                                            candidate_added, _ = db.add_candidate(applicant_name, applicant_email, job_matching_info, "", job['recruiter_id'])
                                            if candidate_added:
                                                candidate = db.get_candidate_by_email(applicant_email)
                                                candidate_id = candidate['id']
                                            else:
                                                st.error("Failed to create candidate profile")
                                                st.stop()

                                        # Check if already applied for this job
                                        existing_resume = db.get_resume_by_candidate_and_job(candidate_id, job['id'])
                                        if existing_resume:
                                            st.warning(f"You have already applied for this position.")
                                        else:
                                            # Save resume to database
                                            extracted_data_json = json.dumps(cv_data) if cv_data else "{}"
                                            db.add_resume(candidate_id, job['recruiter_id'], job['id'], cv_text, extracted_data_json)

                                            st.success(f"✅ Thank you {applicant_name}! Your application for '{job['title']}' has been submitted successfully.")

                                            # Send confirmation email to candidate
                                            subject = f"Application Received - {job['title']}"
                                            body = f"""Dear {applicant_name},

Thank you for applying for the {job['title']} position at {job['company_name']}.

Your application has been received and is being reviewed by our recruitment team.

We will contact you soon with next steps.

Best regards,
Recruitment Team"""

                                            send_email(applicant_email, subject, body)

                                    else:
                                        st.error("❌ Could not process your resume. Please ensure it's a valid PDF or DOCX file.")

                                except Exception as e:
                                    st.error(f"❌ Error processing application: {e}")
                            elif submitted:
                                st.error("⚠️ Please fill in your name, email, and upload your resume.")
        else:
            st.info("No jobs available at the moment. Check back later!")

        with tab2:
            # Main login page
            st.markdown('<div class="main-title"><i class="fas fa-sign-in-alt icon-large"></i><h1 style="margin: 0;">Login</h1></div>', unsafe_allow_html=True)
            role = st.selectbox("Select your role:", ["Select", "Recruiter", "Admin"])
            if role == "Recruiter":
                register = st.checkbox("Register new recruiter")
                if register:
                    with st.form("recruiter_register"):
                        username = st.text_input("Username")
                        email = st.text_input("Email")
                        password = st.text_input("Password", type="password")
                        submitted = st.form_submit_button("Register")
                        if submitted:
                            try:
                                db.add_recruiter(username, email, password, None)
                                st.success("Registered successfully")
                            except Exception as e:
                                st.error(f"Error: {e}")
                else:
                    with st.form("recruiter_login"):
                        email = st.text_input("Email")
                        password = st.text_input("Password", type="password")
                        submitted = st.form_submit_button("Login")
                        if submitted:
                            # Check for default recruiter credentials
                            if email == "recruiter@gmail.com" and password == "123":
                                # Check if default recruiter exists, if not create it
                                default_recruiter = db.get_recruiter_by_id(1)
                                if not default_recruiter:
                                    # Create default recruiter
                                    db.add_recruiter("Recruiter", "recruiter@gmail.com", "123")
                                    default_recruiter = db.get_recruiter_by_id(1)

                                if default_recruiter:
                                    st.session_state.user = default_recruiter
                                    st.session_state.user_type = "recruiter"
                                else:
                                    st.error("Failed to setup default recruiter")
                            else:
                                recruiter = db.get_recruiter(email, password)
                                if recruiter:
                                    st.session_state.user = recruiter
                                    st.session_state.user_type = "recruiter"
                                else:
                                    st.error("Invalid credentials")
            elif role == "Admin":
                with st.form("admin_login"):
                    email = st.text_input("Admin Email")
                    password = st.text_input("Admin Password", type="password")
                    submitted = st.form_submit_button("Admin Login")
                    if submitted:
                        # For demo purposes, using simple admin credentials
                        # In production, this should be properly secured
                        if email == "admin@gmail.com" and password == "123":
                            st.session_state.user = {"username": "Admin", "email": email, "id": 0}
                            st.session_state.user_type = "admin"
                        else:
                            st.error("Invalid admin credentials")
    st.stop()

# Logout button
if st.button("Logout"):
    st.session_state.user = None
    st.session_state.user_type = None
    st.rerun()

# Go Back button
if st.button("Go Back to Login"):
    st.session_state.user = None
    st.session_state.user_type = None

# Role based interface
if st.session_state.user_type == "candidate":
    candidate = st.session_state.user

    # Get test questions - MINIMAL UI
    questions_text = candidate.get('questions', '')
    if questions_text:
        # Parse questions
        questions = [q.strip() for q in questions_text.split('\n\n') if q.strip()]

        # Initialize answers in session state if not exists
        if 'candidate_answers' not in st.session_state:
            st.session_state.candidate_answers = {}

        # Display questions with code editor - MINIMAL
        for i, question in enumerate(questions, 1):
            st.markdown(f"**Question {i}:** {question}")

            # Default code template
            default_code = "# Écrivez votre code Python ici\n\ndef solution():\n    # Votre solution ici\n    return \"Résultat\"\n\n# Testez votre code\nif __name__ == \"__main__\":\n    result = solution()\n    print(f\"Résultat: {result}\")"

            # Use code editor
            code = jupyter_style_editor(f"editor_{i}", default_code)

            # Store the code in session state
            st.session_state.candidate_answers[f"answer_{i}"] = code

            st.markdown("---")

        # Submit button - MINIMAL
        if st.button("Submit Test"):
            # Use stored correct answers if available, otherwise generate them
            correct_answers = {}
            if candidate.get('correct_answers'):
                try:
                    # Parse stored correct answers from JSON
                    import json
                    stored_answers = json.loads(candidate['correct_answers'])
                    # Match stored answers to current questions
                    for question in questions:
                        if question in stored_answers:
                            correct_answers[question] = stored_answers[question]
                        else:
                            # If question not found in stored answers, generate it
                            pdf_files_info = get_pdf_files_info()
                            if pdf_files_info:
                                index, texts = build_vector_store_cached(tuple(
                                    (pdf['name'], pdf['size'], pdf['mtime']) for pdf in pdf_files_info
                                ))
                                if index and texts:
                                    try:
                                        answer = generate_answer_for_question(question, index, texts)
                                        correct_answers[question] = answer
                                    except Exception as e:
                                        correct_answers[question] = f"Erreur génération: {e}"
                                else:
                                    correct_answers[question] = "Réponse par défaut - base de connaissances non disponible"
                            else:
                                correct_answers[question] = "Réponse par défaut - aucun PDF disponible"
                except (json.JSONDecodeError, TypeError):
                    # If parsing fails, generate answers for all questions
                    pdf_files_info = get_pdf_files_info()
                    if pdf_files_info:
                        index, texts = build_vector_store_cached(tuple(
                            (pdf['name'], pdf['size'], pdf['mtime']) for pdf in pdf_files_info
                        ))
                        if index and texts:
                            for question in questions:
                                try:
                                    answer = generate_answer_for_question(question, index, texts)
                                    correct_answers[question] = answer
                                except Exception as e:
                                    correct_answers[question] = f"Erreur génération: {e}"
                        else:
                            for question in questions:
                                correct_answers[question] = "Réponse par défaut - base de connaissances non disponible"
                    else:
                        for question in questions:
                            correct_answers[question] = "Réponse par défaut - aucun PDF disponible"
            else:
                # No stored correct answers, generate them
                pdf_files_info = get_pdf_files_info()
                if pdf_files_info:
                    index, texts = build_vector_store_cached(tuple(
                        (pdf['name'], pdf['size'], pdf['mtime']) for pdf in pdf_files_info
                    ))
                    if index and texts:
                        for question in questions:
                            try:
                                answer = generate_answer_for_question(question, index, texts)
                                correct_answers[question] = answer
                            except Exception as e:
                                correct_answers[question] = f"Erreur génération: {e}"
                    else:
                        for question in questions:
                            correct_answers[question] = "Réponse par défaut - base de connaissances non disponible"
                else:
                    for question in questions:
                        correct_answers[question] = "Réponse par défaut - aucun PDF disponible"

            # Collect user answers
            user_answers = {}
            for i, question in enumerate(questions, 1):
                user_answers[question] = st.session_state.candidate_answers.get(f"answer_{i}", "")

            # Evaluate answers
            with st.spinner('Évaluation des réponses en cours...'):
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
            try:
                db.update_candidate_evaluation(
                    candidate['id'],
                    answers_text,
                    correct_answers,
                    evaluation_results,
                    average_score
                )

                st.success("Test submitted and evaluated successfully!")

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

                # Clear answers from session
                if 'candidate_answers' in st.session_state:
                    del st.session_state.candidate_answers

                # Logout after submission
                st.session_state.user = None
                st.session_state.user_type = None

            except Exception as e:
                st.error(f"Error submitting test: {e}")
    else:
        st.error("No test questions found.")

elif st.session_state.user_type == "recruiter":
    # Display profile picture if available
    recruiter = st.session_state.user
    if recruiter.get('profile_picture'):
        profile_pic_html = f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <img src="data:image/png;base64,{recruiter['profile_picture']}" style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover; margin-right: 15px; border: 3px solid #4CAF50;">
            <div>
                <h1 style="margin: 0; color: #4CAF50;">Welcome back, {recruiter['username']}!</h1>
                <p style="margin: 5px 0; color: #666;">Recruiter Dashboard</p>
            </div>
        </div>
        """
        st.markdown(profile_pic_html, unsafe_allow_html=True)
    else:
        st.markdown('<div class="main-title"><i class="fas fa-user-tie icon-large"></i><h1 style="margin: 0;">Recruiter Dashboard</h1></div>', unsafe_allow_html=True)

    # Get recruiter candidates
    recruiter_id = st.session_state.user.get('id') if isinstance(st.session_state.user, dict) else st.session_state.user['id']
    candidates = db.get_candidates_by_recruiter(recruiter_id)

    # Profile Management Section
    st.markdown('<div class="section-header"><i class="fas fa-user-edit icon-medium"></i><h2 style="margin: 0;">Profile Management</h2></div>', unsafe_allow_html=True)

    with st.expander("📸 Update Profile Picture", expanded=False):
        st.markdown("### Profile Picture")
        current_profile_pic = st.session_state.user.get('profile_picture')
        if current_profile_pic:
            st.image(f"data:image/png;base64,{current_profile_pic}", width=100, caption="Current Profile Picture")

        new_profile_pic = st.file_uploader("Upload new profile picture", type=["png", "jpg", "jpeg"], key="profile_pic_upload")
        if st.button("Update Profile Picture", key="update_profile_pic"):
            if new_profile_pic:
                try:
                    image_data = new_profile_pic.read()
                    profile_pic_base64 = base64.b64encode(image_data).decode('utf-8')

                    # Update in database
                    conn = db.get_db_connection()
                    cur = conn.cursor()
                    cur.execute("UPDATE recruiters SET profile_picture = %s WHERE id = %s", (profile_pic_base64, recruiter_id))
                    conn.commit()
                    cur.close()
                    conn.close()

                    # Update session state
                    st.session_state.user['profile_picture'] = profile_pic_base64
                    st.success("Profile picture updated successfully!")
                except Exception as e:
                    st.error(f"Error updating profile picture: {e}")
            else:
                st.warning("Please select a profile picture to upload.")

    st.markdown("---")

    # Show completed tests
    completed_candidates = [c for c in candidates if c.get('test_completed')]
    if completed_candidates:
        st.markdown('<div class="section-header"><i class="fas fa-check-circle icon-medium"></i><h2 style="margin: 0;">Completed Tests</h2></div>', unsafe_allow_html=True)

        for candidate in completed_candidates:
            with st.expander(f"📊 {candidate['username']} - Score: {candidate.get('average_score', 0):.2f}", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Average Score", f"{candidate.get('average_score', 0):.2f}")
                with col2:
                    st.metric("Test Completed", candidate.get('test_completed_at', 'N/A').strftime('%Y-%m-%d %H:%M') if candidate.get('test_completed_at') else 'N/A')
                with col3:
                    st.metric("Email", candidate['email'])

                # Show detailed results
                if candidate.get('evaluation_results'):
                    import json
                    try:
                        results = json.loads(candidate['evaluation_results'])
                        st.markdown("### Detailed Results")
                        for i, (question, result) in enumerate(results.items(), 1):
                            st.markdown(f"**Question {i}:** {question[:100]}...")
                            st.write("**Candidate Answer:**")
                            st.code(result.get('user', 'N/A'), language='python')
                            st.write(f"**Score:** {result.get('score', 0):.2f}")
                            st.write(f"**Justification:** {result.get('justification', 'N/A')}")
                            st.progress(result.get('score', 0))
                            st.markdown("---")
                    except:
                        st.write("Error loading detailed results")

    # Show top 20% best candidates
    if completed_candidates:
        # Sort by average score descending
        sorted_candidates = sorted(completed_candidates, key=lambda x: x.get('average_score', 0), reverse=True)
        # Take top 20% (at least 1 if available)
        top_count = max(1, int(len(sorted_candidates) * 0.2))
        top_candidates = sorted_candidates[:top_count]

        st.markdown('<div class="section-header"><i class="fas fa-trophy icon-medium"></i><h2 style="margin: 0;">Top 20% Best Candidates</h2></div>', unsafe_allow_html=True)

        # Add congratulation email button
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{len(top_candidates)} top candidates selected**")
        with col2:
            if st.button("🎉 Send Congratulations", key="send_congrats", width='stretch'):
                with st.spinner("Sending congratulation emails..."):
                    sent_count = 0
                    failed_emails = []

                    for candidate in top_candidates:
                        try:
                            subject = "Congratulations! You Have Been Selected"
                            body = f"""Dear {candidate['username']},

Congratulations! 🎉

We are pleased to inform you that you have been selected as one of our top candidates based on your excellent performance in the technical interview test.

Your impressive score of {candidate.get('average_score', 0):.2f} out of 10 has placed you among the top 20% of all candidates who completed the assessment.

Next Steps:
- Our recruitment team will contact you within the next 3-5 business days
- Please prepare for a follow-up interview
- Keep an eye on your email for further instructions

We look forward to potentially welcoming you to our team!

Best regards,
Recruitment Team
{candidate.get('recruiter_name', 'Your Recruiter')}"""

                            send_email(candidate['email'], subject, body)
                            sent_count += 1
                            time.sleep(1)  # Brief pause between emails to avoid spam filters

                        except Exception as e:
                            failed_emails.append(f"{candidate['username']} ({candidate['email']}): {str(e)}")

                    # Show results
                    if sent_count > 0:
                        st.success(f"✅ Successfully sent congratulation emails to {sent_count} candidates!")

                    if failed_emails:
                        st.error("❌ Failed to send emails to some candidates:")
                        for failed in failed_emails:
                            st.write(f"- {failed}")

        st.markdown("---")

        for candidate in top_candidates:
            with st.expander(f"🏆 {candidate['username']} - Score: {candidate.get('average_score', 0):.2f}", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Average Score", f"{candidate.get('average_score', 0):.2f}")
                with col2:
                    st.metric("Test Completed", candidate.get('test_completed_at', 'N/A').strftime('%Y-%m-%d %H:%M') if candidate.get('test_completed_at') else 'N/A')
                with col3:
                    st.metric("Email", candidate['email'])

                # Show detailed results
                if candidate.get('evaluation_results'):
                    import json
                    try:
                        results = json.loads(candidate['evaluation_results'])
                        st.markdown("### Detailed Results")
                        for i, (question, result) in enumerate(results.items(), 1):
                            st.markdown(f"**Question {i}:** {question[:100]}...")
                            st.write("**Candidate Answer:**")
                            st.code(result.get('user', 'N/A'), language='python')
                            st.write(f"**Score:** {result.get('score', 0):.2f}")
                            st.write(f"**Justification:** {result.get('justification', 'N/A')}")
                            st.progress(result.get('score', 0))
                            st.markdown("---")
                    except:
                        st.write("Error loading detailed results")

    # Job Applications Management
    st.markdown('<div class="section-header"><i class="fas fa-users icon-medium"></i><h2 style="margin: 0;">Job Applications</h2></div>', unsafe_allow_html=True)

    # Get jobs posted by this recruiter
    jobs = db.get_jobs_by_recruiter(recruiter_id)

    if jobs:
        for job in jobs:
            # Get applications count for this job
            applications = db.get_resumes_by_job(job['id'])
            application_count = len(applications) if applications else 0

            with st.expander(f"📋 {job['title']} at {job['company_name']} - {application_count} candidates applied", expanded=False):

                if applications and application_count > 0:
                    st.markdown(f"**{application_count} candidate(s) applied**")

                    # Button to send test invitations to all applicants
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown("**📤 Send test invitations to all applicants**")
                    with col2:
                        if st.button(f"📨 Send Tests", key=f"send_test_{job['id']}", width='stretch'):
                            with st.spinner("Generating questions and sending test invitations..."):
                                sent_count = 0
                                failed_emails = []

                                # Generate questions for this job
                                try:
                                    questions, correct_answers = generate_interview_content()
                                    questions_text = "\n\n".join([f"Question {i+1}: {q}" for i, q in enumerate(questions, 1)])
                                except Exception as e:
                                    st.error(f"Failed to generate questions: {e}")
                                    questions_text = "Default questions will be used."
                                    correct_answers = {}

                                for app in applications:
                                    try:
                                        # Update candidate with questions and correct answers
                                        db.update_candidate_questions(app['candidate_id'], questions_text, correct_answers)

                                        # Use password from the query result
                                        candidate_password = app['password']

                                        # Generate test link
                                        test_link = f"http://localhost:8501/?email={app['email']}"

                                        subject = f"Technical Interview Test - {job['title']} Position"
                                        body = f"""Dear {app['username']},

Congratulations! You have been selected to take the technical interview test for the {job['title']} position at {job['company_name']}.

Your test credentials:
Email: {app['email']}
Password: {candidate_password}

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
Recruitment Team
{st.session_state.user.get('username', 'Your Recruiter')}"""

                                        send_email(app['email'], subject, body)
                                        sent_count += 1
                                        time.sleep(1)  # Brief pause between emails

                                    except Exception as e:
                                        failed_emails.append(f"{app['username']} ({app['email']}): {str(e)}")

                                # Show results
                                if sent_count > 0:
                                    st.success(f"✅ Successfully sent test invitations to {sent_count} candidates!")

                                if failed_emails:
                                    st.error("❌ Failed to send emails to some candidates:")
                                    for failed in failed_emails:
                                        st.write(f"- {failed}")

                    st.markdown("---")

                    # Filter applications with completed tests
                    completed_applications = [app for app in applications if app.get('test_completed')]

                    if completed_applications:
                        st.markdown("### ✅ Candidates with Test Results")

                        # Sort by score descending
                        sorted_applications = sorted(completed_applications, key=lambda x: x.get('average_score', 0), reverse=True)

                        for app in sorted_applications:
                            col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                            with col1:
                                st.write(f"**{app['username']}**")
                            with col2:
                                st.write(f"📧 {app['email']}")
                            with col3:
                                st.write(f"⭐ {app.get('average_score', 0):.2f}")
                            with col4:
                                test_date = app.get('test_completed_at')
                                if test_date:
                                    st.write(f"📅 {test_date.strftime('%Y-%m-%d')}")

                        # Announce results button
                        st.markdown("---")
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**📢 Announce results to {len(completed_applications)} candidates**")
                        with col2:
                            if st.button(f"📢 Announce Results", key=f"announce_results_{job['id']}", width='stretch'):
                                with st.spinner("Sending result announcement emails..."):
                                    sent_count = 0
                                    failed_emails = []

                                    for app in completed_applications:
                                        try:
                                            subject = f"Test Results - {job['title']} Position"
                                            body = f"""Dear {app['username']},

Thank you for completing the technical interview test for the {job['title']} position at {job['company_name']}.

Your test has been evaluated and your results are now available.

Test Summary:
- Score: {app.get('average_score', 0):.2f}/10
- Test Completed: {app.get('test_completed_at').strftime('%Y-%m-%d %H:%M') if app.get('test_completed_at') else 'N/A'}

Next Steps:
- Our recruitment team will review your application
- You will be contacted within the next 3-5 business days
- Please keep an eye on your email for further updates

We appreciate your interest in joining our team!

Best regards,
Recruitment Team
{st.session_state.user.get('username', 'Your Recruiter')}"""

                                            send_email(app['email'], subject, body)
                                            sent_count += 1
                                            time.sleep(1)  # Brief pause between emails

                                        except Exception as e:
                                            failed_emails.append(f"{app['username']} ({app['email']}): {str(e)}")

                                    # Show results
                                    if sent_count > 0:
                                        st.success(f"✅ Successfully sent result announcements to {sent_count} candidates!")

                                    if failed_emails:
                                        st.error("❌ Failed to send emails to some candidates:")
                                        for failed in failed_emails:
                                            st.write(f"- {failed}")
                    else:
                        st.info("No candidates have completed their tests yet for this position.")

                    # Show all applications (including those without test results)
                    st.markdown("### 📝 All Applications")
                    for app in applications:
                        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                        with col1:
                            st.write(f"**{app['username']}**")
                        with col2:
                            st.write(f"📧 {app['email']}")
                        with col3:
                            status = "✅ Completed" if app.get('test_completed') else "⏳ Pending"
                            st.write(f"**Status:** {status}")
                        with col4:
                            if app.get('test_completed'):
                                st.write(f"⭐ {app.get('average_score', 0):.2f}")
                            else:
                                st.write("Not tested")

                else:
                    st.info("No applications received for this position yet.")
    else:
        st.info("No job postings found. Add jobs using the 'Job Management' section.")

    # Job Management Section
    st.markdown('<div class="section-header"><i class="fas fa-briefcase icon-medium"></i><h2 style="margin: 0;">Job Management</h2></div>', unsafe_allow_html=True)

    # Tabs for job management
    job_tab1, job_tab2, job_tab3 = st.tabs(["📋 View Jobs", "➕ Add New Job", "🏢 Manage Companies"])

    with job_tab1:
        st.markdown("### Your Job Postings")
        jobs = db.get_jobs_by_recruiter(recruiter_id)
        if jobs:
            for job in jobs:
                with st.expander(f"💼 {job['title']} at {job['company_name']}", expanded=False):
                    # Show job image if available
                    if job['job_image']:
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.image(f"data:image/png;base64,{job['job_image']}", width=150)
                        with col2:
                            st.write(f"**Position:** {job['position']}")
                            st.write(f"**Type:** {job['type']}")
                            st.write(f"**Location:** {job['location']}")
                            st.write(f"**Posted:** {job['posted']}")
                            st.write(f"**Salary:** {job['salary_currency']} {job['salary_from']}-{job['salary_to']}" if job['salary_from'] else "Salary not specified")
                            st.write(f"**Equity:** {job['equity_from']*100:.1f}%-{job['equity_to']*100:.1f}%" if job['equity_from'] or job['equity_to'] else "No equity")
                            if job['skills']:
                                st.write(f"**Skills:** {', '.join(job['skills'])}")
                            if job['perks']:
                                st.write(f"**Perks:** {', '.join(job['perks'])}")
                    else:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Position:** {job['position']}")
                            st.write(f"**Type:** {job['type']}")
                            st.write(f"**Location:** {job['location']}")
                            st.write(f"**Posted:** {job['posted']}")
                        with col2:
                            st.write(f"**Salary:** {job['salary_currency']} {job['salary_from']}-{job['salary_to']}" if job['salary_from'] else "Salary not specified")
                            st.write(f"**Equity:** {job['equity_from']*100:.1f}%-{job['equity_to']*100:.1f}%" if job['equity_from'] or job['equity_to'] else "No equity")
                            if job['skills']:
                                st.write(f"**Skills:** {', '.join(job['skills'])}")
                            if job['perks']:
                                st.write(f"**Perks:** {', '.join(job['perks'])}")

                    st.write(f"**Description:** {job['description']}")
                    if job['apply_url']:
                        st.markdown(f"[Apply Here]({job['apply_url']})")

                    # Delete button
                    if st.button(f"🗑️ Delete Job", key=f"delete_job_{job['id']}", width='stretch'):
                        try:
                            db.delete_job(job['id'])
                            st.success(f"Job '{job['title']}' deleted successfully!")
                        except Exception as e:
                            st.error(f"Error deleting job: {e}")
        else:
            st.info("No jobs found. Add your first job using the 'Add New Job' tab.")

    with job_tab2:
        st.markdown("### Add New Job Posting")

        # First, select or add company
        st.markdown("#### Company Information")
        company_option = st.selectbox("Select existing company or add new:", ["Select existing", "Add new company"])

        if company_option == "Select existing":
            companies = db.get_all_companies()  # Get all companies
            if companies:
                company_names = [company['name'] for company in companies]
                selected_company = st.selectbox("Select company:", company_names)
                company_id = None
                for company in companies:
                    if company['name'] == selected_company:
                        company_id = company['id']
                        break
            else:
                st.warning("No companies found. Please add a new company.")
                company_id = None
        else:
            with st.form("add_company"):
                company_name = st.text_input("Company Name")
                company_url = st.text_input("Company Website")
                remote_friendly = st.checkbox("Remote Friendly")
                market = st.text_input("Market/Sector")
                company_size = st.text_input("Company Size (e.g., 10-50, 200-500)")
                submitted = st.form_submit_button("Add Company")

                if submitted and company_name:
                    try:
                        company_id = db.add_company(company_name, company_url, remote_friendly, market, company_size)
                        if company_id:
                            st.success(f"Company '{company_name}' added successfully!")
                        else:
                            st.warning(f"Company '{company_name}' already exists.")
                    except Exception as e:
                        st.error(f"Error adding company: {e}")
                company_id = None

        if company_id:
            st.markdown("#### Job Information")
            with st.form("add_job"):
                position = st.text_input("Position")
                title = st.text_input("Job Title")
                description = st.text_area("Job Description")
                job_url = st.text_input("Job URL")
                job_type = st.selectbox("Job Type", ["full-time", "part-time", "contract", "internship"])
                location = st.text_input("Location", "Remote")
                posted_date = st.date_input("Posted Date")

                # Skills
                skills_input = st.text_input("Skills (comma-separated)", placeholder="Python, JavaScript, SQL")
                skills = [s.strip() for s in skills_input.split(',') if s.strip()]

                # Salary
                col1, col2, col3 = st.columns(3)
                with col1:
                    salary_from = st.number_input("Salary From", min_value=0.0, step=1000.0)
                with col2:
                    salary_to = st.number_input("Salary To", min_value=0.0, step=1000.0)
                with col3:
                    salary_currency = st.selectbox("Currency", ["USD", "EUR", "GBP"], index=0)

                # Equity
                col1, col2 = st.columns(2)
                with col1:
                    equity_from = st.number_input("Equity From (%)", min_value=0.0, max_value=100.0, step=0.1) / 100
                with col2:
                    equity_to = st.number_input("Equity To (%)", min_value=0.0, max_value=100.0, step=0.1) / 100

                # Perks
                perks_input = st.text_input("Perks (comma-separated)", placeholder="free food, gym membership")
                perks = [p.strip() for p in perks_input.split(',') if p.strip()]

                job_image = st.file_uploader("Job Image (optional)", type=["png", "jpg", "jpeg"], help="Upload an image to make the job post more attractive")
                apply_url = st.text_input("Application URL")

                submitted = st.form_submit_button("Add Job")

                if submitted and title and position:
                    try:
                        job_image_base64 = None
                        if job_image is not None:
                            # Convert image to base64
                            image_data = job_image.read()
                            job_image_base64 = base64.b64encode(image_data).decode('utf-8')

                        db.add_job(
                            company_id=company_id,
                            recruiter_id=recruiter_id,
                            position=position,
                            title=title,
                            description=description,
                            url=job_url,
                            job_type=job_type,
                            posted=posted_date,
                            location=location,
                            skills=skills,
                            salary_from=salary_from if salary_from > 0 else None,
                            salary_to=salary_to if salary_to > 0 else None,
                            salary_currency=salary_currency,
                            equity_from=equity_from,
                            equity_to=equity_to,
                            perks=perks,
                            apply_url=apply_url,
                            job_image=job_image_base64
                        )
                        st.success(f"Job '{title}' added successfully!")
                    except Exception as e:
                        st.error(f"Error adding job: {e}")

    with job_tab3:
        st.markdown("### Company Management")
        st.markdown("Manage companies for your job postings")

        # Add new company form
        with st.expander("➕ Add New Company", expanded=False):
            with st.form("add_company_independent"):
                company_name = st.text_input("Company Name")
                company_url = st.text_input("Company Website")
                remote_friendly = st.checkbox("Remote Friendly")
                market = st.text_input("Market/Sector")
                company_size = st.text_input("Company Size (e.g., 10-50, 200-500)")
                submitted = st.form_submit_button("Add Company")

                if submitted and company_name:
                    try:
                        company_id = db.add_company(company_name, company_url, remote_friendly, market, company_size)
                        if company_id:
                            st.success(f"Company '{company_name}' added successfully!")
                        else:
                            st.warning(f"Company '{company_name}' already exists.")
                    except Exception as e:
                        st.error(f"Error adding company: {e}")

        # Display companies
        st.markdown("### Existing Companies")
        companies = db.get_all_companies()
        if companies:
            for company in companies:
                with st.expander(f"🏢 {company['name']}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Website:** {company['url'] or 'N/A'}")
                        st.write(f"**Market:** {company['market'] or 'N/A'}")
                        st.write(f"**Size:** {company['size'] or 'N/A'}")
                    with col2:
                        st.write(f"**Remote Friendly:** {'Yes' if company['remote_friendly'] else 'No'}")

                    # Show jobs count for this company
                    jobs_count = len([j for j in db.get_all_jobs() if j['company_id'] == company['id']])
                    st.write(f"**Jobs Posted:** {jobs_count}")

                    # Delete button (only if no jobs)
                    if jobs_count == 0:
                        if st.button(f"🗑️ Delete Company", key=f"delete_company_{company['id']}", width='stretch'):
                            try:
                                db.delete_company(company['id'])
                                st.success(f"Company '{company['name']}' deleted successfully!")
                            except Exception as e:
                                st.error(f"Error deleting company: {e}")
                    else:
                        st.info("Cannot delete company with existing jobs")
        else:
            st.info("No companies found.")

    # Candidate interface removed - candidates now receive tests via email

elif st.session_state.user_type == "admin":
    st.markdown('<div class="main-title"><i class="fas fa-user-shield icon-large"></i><h1 style="margin: 0;">Admin Dashboard</h1></div>', unsafe_allow_html=True)

    # Admin tabs for different management sections
    tab1, tab2 = st.tabs(["👥 Manage Recruiters", "👨‍🎓 Manage Candidates"])

    with tab1:
        st.markdown('<div class="section-header"><i class="fas fa-users icon-medium"></i><h2 style="margin: 0;">Recruiters Management</h2></div>', unsafe_allow_html=True)

        # Add new recruiter form
        with st.expander("➕ Add New Recruiter", expanded=False):
            with st.form("admin_add_recruiter"):
                username = st.text_input("Username")
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                profile_picture = st.file_uploader("Profile Picture", type=["png", "jpg", "jpeg"], help="Upload a profile picture for the recruiter")
                submitted = st.form_submit_button("Add Recruiter")
                if submitted:
                    try:
                        profile_pic_base64 = None
                        if profile_picture is not None:
                            # Convert image to base64
                            image_data = profile_picture.read()
                            profile_pic_base64 = base64.b64encode(image_data).decode('utf-8')

                        db.add_recruiter(username, email, password, profile_pic_base64)
                        st.success(f"Recruiter {username} added successfully!")
                    except Exception as e:
                        st.error(f"Error adding recruiter: {e}")

        # Display recruiters table
        recruiters = db.get_all_recruiters()
        if recruiters:
            st.markdown("### Current Recruiters")

            # Create a table-like display with delete buttons
            for recruiter in recruiters:
                col1, col2, col3, col4, col5 = st.columns([2, 3, 3, 2, 2])
                with col1:
                    st.write(f"**ID:** {recruiter['id']}")
                with col2:
                    st.write(f"**Username:** {recruiter['username']}")
                with col3:
                    st.write(f"**Email:** {recruiter['email']}")
                with col4:
                    st.write("**Actions:**")
                with col5:
                    if st.button(f"🗑️ Delete", key=f"delete_recruiter_{recruiter['id']}", width='stretch'):
                        try:
                            db.delete_recruiter(recruiter['id'])
                            st.success(f"Recruiter {recruiter['username']} deleted successfully!")
                        except Exception as e:
                            st.error(f"Error deleting recruiter: {e}")
                st.markdown("---")
        else:
            st.info("No recruiters found.")

    with tab2:
        st.markdown('<div class="section-header"><i class="fas fa-user-graduate icon-medium"></i><h2 style="margin: 0;">Candidates Overview</h2></div>', unsafe_allow_html=True)

        # Display candidates table (view only for admin)
        candidates = db.get_all_candidates()
        if candidates:
            st.markdown("### All Candidates in System")

            # Create a table-like display (view only)
            for candidate in candidates:
                col1, col2, col3, col4, col5 = st.columns([1, 2, 3, 2, 2])
                with col1:
                    st.write(f"**ID:** {candidate['id']}")
                with col2:
                    st.write(f"**Name:** {candidate['username']}")
                with col3:
                    st.write(f"**Email:** {candidate['email']}")
                with col4:
                    st.write(f"**Recruiter:** {candidate.get('recruiter_name', 'N/A')}")
                with col5:
                    status = "✅ Completed" if candidate.get('test_completed') else "⏳ Pending"
                    st.write(f"**Status:** {status}")
                st.markdown("---")

            # Summary statistics
            total_candidates = len(candidates)
            completed_tests = sum(1 for c in candidates if c.get('test_completed'))
            completion_rate = (completed_tests / total_candidates * 100) if total_candidates > 0 else 0

            st.markdown("### 📊 System Statistics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Candidates", total_candidates)
            with col2:
                st.metric("Completed Tests", completed_tests)
            with col3:
                st.metric("Completion Rate", f"{completion_rate:.1f}%")

        else:
            st.info("No candidates found in the system.")

# ========== SIDEBAR ==========
with st.sidebar:
    st.markdown('<div class="section-header"><i class="fas fa-info-circle icon-medium"></i><h3 style="margin: 0;">Informations</h3></div>', unsafe_allow_html=True)
    st.markdown("""
    **Comment ça marche :**
    1. <i class="fas fa-upload icon-small"></i> Uploadez votre CV
    2. <i class="fas fa-bullseye icon-small"></i> Découvrez les jobs correspondants  
    3. <i class="fas fa-edit icon-small"></i> Répondez aux questions d'entretien
    4. <i class="fas fa-chart-bar icon-small"></i> Consultez votre évaluation
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="section-header"><i class="fas fa-book icon-medium"></i><h3 style="margin: 0;">Base de connaissances</h3></div>', unsafe_allow_html=True)
    pdf_files = get_pdf_files_info()
    if pdf_files:
        st.markdown(f'<p><i class="fas fa-check-circle success-icon"></i> {len(pdf_files)} PDF(s) chargé(s)</p>', unsafe_allow_html=True)
        for pdf in pdf_files:
            st.markdown(f"<i class='fas fa-file-pdf icon-small'></i> {pdf['name']}", unsafe_allow_html=True)
    else:
        st.markdown('<p><i class="fas fa-exclamation-triangle warning-icon"></i> Aucun PDF dans "data/"</p>', unsafe_allow_html=True)
        st.markdown('<p><i class="fas fa-info-circle info-icon"></i> Ajoutez des PDFs dans le dossier "data" pour des questions personnalisées.</p>', unsafe_allow_html=True)
    
    if st.button('🔄 Actualiser la base'):
        st.cache_data.clear()
        st.success("Cache vidé ! Rafraîchissez la page pour voir les changements.")