# ===================== Streamlit-Friendly agent.py =====================

import os
import json
import logging
import re
import numpy as np
from PyPDF2 import PdfReader
import google.generativeai as genai
from openai import OpenAI
from sentence_transformers import SentenceTransformer, util

# ========== CONFIG ==========
UPLOAD_FOLDER = "mycv"
KNOWLEDGE_FOLDER = "data"
RESPONSES_FOLDER = "responses"

for folder in [UPLOAD_FOLDER, KNOWLEDGE_FOLDER, RESPONSES_FOLDER]:
    os.makedirs(folder, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔑 Gemini API (embeddings)
genai.configure(api_key="AIzaSyCklEhmeEUcgTtAww-DwH5lActIZ6XGd0c")

# 🔑 OpenRouter API (generation)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",
)

# Models
EMBED_MODEL = "models/embedding-001"
GEN_MODEL = "meta-llama/llama-4-maverick:free"
st_model = SentenceTransformer("all-mpnet-base-v2")

# ========== EMBEDDINGS ==========
def get_embedding(text: str):
    return np.array(st_model.encode(text), dtype="float32")

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

# ========== PDF HANDLING ==========
def extract_text_from_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF {file_path}: {e}")
        return ""

# ========== KNOWLEDGE BASE ==========
def build_vector_store():
    texts, embeddings = [], []
    pdf_files = [f for f in os.listdir(KNOWLEDGE_FOLDER) if f.lower().endswith('.pdf')]
    if not pdf_files:
        logger.warning("No PDF files found in knowledge folder")
        return None, []
    for file_name in pdf_files:
        path = os.path.join(KNOWLEDGE_FOLDER, file_name)
        text = extract_text_from_pdf(path)
        if text:
            emb = get_embedding(text)
            texts.append(text)
            embeddings.append(emb)
    if not embeddings:
        return None, []
    import faiss
    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings))
    logger.info(f"Vector store built with {len(texts)} documents")
    return index, texts

def search_knowledge(query, index, texts, top_k=3):
    try:
        query_emb = get_embedding(query)
        D, I = index.search(np.array([query_emb]), top_k)
        return [texts[i] for i in I[0] if i < len(texts)]
    except Exception as e:
        logger.error(f"Error searching knowledge: {e}")
        return []

# ========== QUESTION GENERATION ==========
def generate_questions(cv_text, knowledge_chunks, n=3):
    if not knowledge_chunks:
        return [
            "Pouvez-vous décrire votre expérience avec les technologies mentionnées dans votre CV?",
            "Quel projet récent êtes-vous le plus fier de et pourquoi?",
            "Comment abordez-vous la résolution de problèmes techniques complexes?"
        ]
    cv_excerpt = cv_text[:2000] if cv_text else "CV non disponible"
    context = "\n---\n".join(knowledge_chunks[:3])[:3000]
    prompt = f"""
    Voici un extrait du CV du candidat :
    {cv_excerpt}

    Et quelques extraits de la base de connaissances :
    {context}

    Génère {n} questions techniques pertinentes, en français,
    sous forme d'exercices pratiques qui testent les compétences et techniques mentionnées.
    """
    try:
        response = client.chat.completions.create(
            model=GEN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        generated_text = response.choices[0].message.content.strip()
        questions = []
        for line in generated_text.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                question_text = re.sub(r'^(\d+[\.\)]|\-|\•)\s*', '', line)
                if question_text:
                    questions.append(question_text)
        return questions[:n] if questions else generated_text.splitlines()[:n]
    except Exception as e:
        logger.error(f"Error generating questions: {e}")
        return []

# ========== ANSWER GENERATION ==========
def generate_answer_for_question(question, relevant_knowledge, max_context_length=1500):
    if not relevant_knowledge:
        return "Réponse non disponible - contexte technique manquant."
    context = "\n".join(relevant_knowledge)[:max_context_length]
    prompt = f"""
    Question d'entretien technique :
    {question}

    Contexte technique pertinent :
    {context}

    Génère une réponse correcte et détaillée en français, basée sur le contexte technique fourni.
    """
    try:
        response = client.chat.completions.create(
            model=GEN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        return "Réponse non disponible pour le moment."
    
def evaluate_answers(user_answers, correct_answers, threshold=0.75):
    results = {}
    for q, user_ans in user_answers.items():
        correct_ans = correct_answers.get(q, "")
        if not user_ans.strip() or not correct_ans.strip():
            results[q] = {"user": user_ans, "correct": correct_ans, "score": 0.0, "match": "false"}
            continue
        try:
            emb_user = st_model.encode(user_ans, convert_to_tensor=True)
            emb_correct = st_model.encode(correct_ans, convert_to_tensor=True)
            score = util.cos_sim(emb_user, emb_correct).item()  # entre 0 et 1
            results[q] = {
                "user": user_ans,
                "correct": correct_ans,
                "score": float(score),
                "match": "true" if score >= threshold else "false"
            }
        except Exception as e:
            results[q] = {"user": user_ans, "correct": correct_ans, "score": 0.0, "match": "false", "error": str(e)}
    return results

# ===================== Streamlit Integration =====================
def generate_questions_from_cv(cv_text, n=3):
    """For app.py: generate questions directly from CV text."""
    index, texts = build_vector_store()
    if not index:
        # fallback questions if no knowledge base
        return [
            "Pouvez-vous décrire votre expérience avec les technologies mentionnées dans votre CV?",
            "Quel projet récent êtes-vous le plus fier de et pourquoi?",
            "Comment abordez-vous la résolution de problèmes techniques complexes?"
        ]
    relevant_knowledge = search_knowledge(cv_text, index, texts)
    return generate_questions(cv_text, relevant_knowledge, n=n)

def verify_answer(user_answers):
    """For app.py: evaluates user answers against saved correct answers."""
    correct_answers_path = os.path.join(RESPONSES_FOLDER, "correct_answers.json")
    if os.path.exists(correct_answers_path):
        with open(correct_answers_path, "r", encoding="utf-8") as f:
            correct_answers = json.load(f)
    else:
        correct_answers = {}
    return evaluate_answers(user_answers, correct_answers)
