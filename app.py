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
        run_clicked = st.button("▶️ Exécuter", key=f"run_{key}", use_container_width=True)

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
    
    /* Custom button styles with icons */
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
    
    /* Metric cards with icons */
    .metric-card {
        background: black;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        border-left: black;
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

# Check for URL parameters (for candidate login link)
query_params = st.query_params
if 'email' in query_params:
    candidate = db.get_candidate_by_email(query_params['email'])
    if candidate:
        if 'mode' not in st.session_state or st.session_state.mode != 'candidate_login':
            st.session_state.user = None
            st.session_state.user_type = None
            st.session_state.mode = 'candidate_login'
            st.session_state.candidate_email = query_params['email']

if st.session_state.user is None:
    # Candidate login page - MINIMAL UI
    if 'mode' in st.session_state and st.session_state.mode == 'candidate_login':
        candidate_email = st.session_state.get('candidate_email', '')

        # Minimal login form - just inputs and button
        with st.form("candidate_login"):
            email = st.text_input("Email", value=candidate_email)
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                candidate = db.get_candidate(email, password)
                if candidate:
                    st.session_state.user = candidate
                    st.session_state.user_type = "candidate"
                else:
                    st.error("Invalid credentials")

    else:
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
                            db.add_recruiter(username, email, password)
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
                            st.session_state.user = {"username": "Recruiter", "email": email, "id": 1}
                            st.session_state.user_type = "recruiter"
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
            # Generate correct answers if not already done
            correct_answers = {}
            if not candidate.get('correct_answers'):
                # Build knowledge base for generating correct answers
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
    st.markdown('<div class="main-title"><i class="fas fa-user-tie icon-large"></i><h1 style="margin: 0;">Recruiter Dashboard</h1></div>', unsafe_allow_html=True)

    # Get recruiter candidates
    recruiter_id = st.session_state.user.get('id') if isinstance(st.session_state.user, dict) else st.session_state.user['id']
    candidates = db.get_candidates_by_recruiter(recruiter_id)

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
            if st.button("🎉 Send Congratulations", key="send_congrats", use_container_width=True):
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

    # Upload new candidates
    st.markdown('<div class="section-header"><i class="fas fa-upload icon-medium"></i><h2 style="margin: 0;">Upload New Candidates</h2></div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader("Upload candidate resumes", type=["pdf", "docx", "png", "jpg", "jpeg"], accept_multiple_files=True)
    if uploaded_files:
        # Only load jobs data when files are uploaded
        jobs_file = Path(__file__).parent / "jobs.json"
        jobs_data = load_jobs_data(str(jobs_file))
        for uploaded_file in uploaded_files:
            file_content = uploaded_file.read()
            file_name = uploaded_file.name
            cv_text, cv_data = process_cv_cached(file_content, file_name)
            if cv_data:
                matches = process_job_matching(cv_data, jobs_data)
                job_matching = str(matches)
                username = cv_data.get('name', file_name.split('.')[0])
                email = cv_data.get('email', f"{username}@example.com")

                # Generate test questions
                try:
                    questions, correct_answers = generate_interview_content()
                    questions_text = "\n\n".join([f"Question {i+1}: {q}" for i, q in enumerate(questions)])

                    candidate_added, generated_password = db.add_candidate(username, email, job_matching, questions_text, recruiter_id)

                    if candidate_added:
                        # Create test link with candidate email
                        test_link = f"http://localhost:8501/?email={email}"

                        subject = "Technical Interview Test Invitation"
                        body = f"""Hi {username},

Thank you for applying! You have been invited to take a technical interview test.

Your login credentials:
Email: {email}
Password: {generated_password}

Please click the link below to access your test:
{test_link}

After logging in, you will be able to view and complete your technical interview questions.

Best regards,
Recruitment Team"""

                        send_email(email, subject, body)
                        st.success(f"Processed {file_name}, candidate added, invitation sent to {email}")
                        st.info(f"Generated password for {username}: {generated_password}")
                    else:
                        st.warning(f"Processed {file_name}, candidate {email} already exists - no email sent")
                except Exception as e:
                    st.error(f"Error processing candidate: {e}")
                    st.write(f"Debug - User object: {st.session_state.user}")
                    st.write(f"Debug - User type: {type(st.session_state.user)}")
            else:
                st.error(f"Could not process {file_name}")
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
                submitted = st.form_submit_button("Add Recruiter")
                if submitted:
                    try:
                        db.add_recruiter(username, email, password)
                        st.success(f"Recruiter {username} added successfully!")
                        st.rerun()
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
                    if st.button(f"🗑️ Delete", key=f"delete_recruiter_{recruiter['id']}", use_container_width=True):
                        try:
                            db.delete_recruiter(recruiter['id'])
                            st.success(f"Recruiter {recruiter['username']} deleted successfully!")
                            st.rerun()
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