# ===================== Streamlit-Friendly agent.py =====================

import os
import json
import logging
import re
import numpy as np
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from openrouter_client import openrouter_client, generate_interview_questions, evaluate_candidate_answer

# ========== CONFIG ==========
UPLOAD_FOLDER = "mycv"
KNOWLEDGE_FOLDER = "data"       # PDF corrigé
RESPONSES_FOLDER = "responses"

for folder in [UPLOAD_FOLDER, KNOWLEDGE_FOLDER, RESPONSES_FOLDER]:
    os.makedirs(folder, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔑 OpenRouter API (remplace Gemini)
GEN_MODEL = "openai/gpt-4o-mini"
EVAL_MODEL = "openai/gpt-4o-mini"

# SentenceTransformer → uniquement pour FAISS (RAG)
st_model = SentenceTransformer("all-mpnet-base-v2")

# ========== EMBEDDINGS ==========
def get_embedding(text: str):
    return np.array(st_model.encode(text), dtype="float32")

# ========== PDF HANDLING ==========
def extract_text_from_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        return "\n".join([p.extract_text() or "" for p in reader.pages]).strip()
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return ""

# ========== KNOWLEDGE BASE (uniquement data/) ==========
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

def search_knowledge(query, index, texts, top_k=2):
    """Recherche dans le PDF corrigé (data/)"""
    try:
        query_emb = get_embedding(query)
        D, I = index.search(np.array([query_emb]), top_k)
        return [texts[i] for i in I[0] if i < len(texts)]
    except Exception as e:
        logger.error(f"Error searching knowledge: {e}")
        return []

# ========== QUESTION GENERATION (CV + PDF corrigé) ==========
def generate_questions_from_cv(cv_text, knowledge_chunks, n=3):
    """Génère des questions d'entretien en utilisant OpenRouter"""
    try:
        # Utiliser la fonction d'OpenRouter
        questions = generate_interview_questions(knowledge_chunks, n)
        logger.info(f"✅ {len(questions)} questions générées avec OpenRouter")
        return questions
    except Exception as e:
        logger.error(f"❌ Erreur génération questions OpenRouter: {e}")

        # Fallback: questions prédéfinies
        fallback_questions = [
            "Écrivez une fonction qui calcule la somme de deux nombres.",
            "Écrivez une fonction qui vérifie si un nombre est pair ou impair.",
            "Écrivez une fonction qui trouve le maximum de trois nombres."
        ]
        logger.info(f"🔄 Fallback: {len(fallback_questions[:n])} questions prédéfinies")
        return fallback_questions[:n]

# ========== ANSWER GENERATION (RAG depuis data/) ==========
def generate_answer_for_question(question, index=None, texts=None, max_context_length=1500):
    """Génère une réponse à une question en utilisant OpenRouter"""
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

        if openrouter_client.is_available():
            response = openrouter_client.generate_content(prompt, max_tokens=800)
            logger.info("✅ Réponse générée avec OpenRouter")
            return response.strip()
        else:
            logger.warning("⚠️ OpenRouter non disponible - réponse par défaut")
            return "Réponse par défaut - IA non disponible"

    except Exception as e:
        logger.error(f"❌ Erreur génération réponse: {e}")
        return "Réponse non disponible - erreur système."

# ========== ÉVALUATION (Gemini au lieu d'OpenRouter) - IMPROVED ==========
def extract_json_robust(text):
    """
    Extraction JSON très robuste avec plusieurs stratégies de fallback
    """
    if not text:
        return None
    
    # Stratégie 1: JSON direct
    try:
        return json.loads(text.strip())
    except:
        pass
    
    # Stratégie 2: Extraction par regex améliorée
    try:
        # Chercher un objet JSON complet
        json_patterns = [
            r'\{[^{}]*"score"[^{}]*"justification"[^{}]*\}',
            r'\{[\s\S]*?"score"[\s\S]*?"justification"[\s\S]*?\}',
            r'\{.*?\}',
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                json_str = match.group()
                # Nettoyage avancé
                json_str = json_str.replace("'", '"')  # quotes simples → doubles
                json_str = re.sub(r',\s*}', '}', json_str)  # virgules finales
                json_str = re.sub(r',\s*]', ']', json_str)
                
                # Correction des scores en string
                json_str = re.sub(r'"score"\s*:\s*"([\d\.]+)"', r'"score": \1', json_str)
                json_str = re.sub(r'"score"\s*:\s*([^\",}]+)', r'"score": \1', json_str)
                
                # Supprimer caractères invalides
                json_str = re.sub(r'[^\x20-\x7E\u00A0-\uFFFF]', '', json_str)
                
                return json.loads(json_str)
    except Exception as e:
        logger.debug(f"JSON regex extraction failed: {e}")
    
    # Stratégie 3: Parsing manuel avec regex
    try:
        score_match = re.search(r'(?:"score"|score)\s*[:=]\s*([\d\.]+)', text)
        justif_match = re.search(r'(?:"justification"|justification)\s*[:=]\s*["\']([^"\']+)["\']', text)
        
        if score_match:
            score = float(score_match.group(1))
            justification = justif_match.group(1) if justif_match else "Évaluation automatique"
            return {"score": score, "justification": justification}
    except Exception as e:
        logger.debug(f"Manual parsing failed: {e}")
    
    # Stratégie 4: Fallback avec analyse simple du texte
    try:
        # Chercher un nombre qui pourrait être un score
        number_matches = re.findall(r'(0\.\d+|\d\.\d+|0|1)', text)
        if number_matches:
            score = float(number_matches[0])
            return {"score": min(1.0, max(0.0, score)), "justification": "Score extrait du texte"}
    except:
        pass
    
    logger.error(f"Impossible d'extraire JSON de: {text[:200]}...")
    return None


import re
import json
import unicodedata
import difflib
import ast
import logging

logger = logging.getLogger(__name__)

EVAL_MODEL = "gemini-2.0-flash"

def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")  # enlever accents
    s = re.sub(r'\s+', ' ', s).strip().lower()
    return re.sub(r'[^\w\s]', ' ', s)

def text_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()

def extract_json_robust(text: str):
    if not text:
        return None
    # 1) try to find {...} blocks and parse
    candidates = re.findall(r'\{.*?\}', text, re.DOTALL)
    for cand in candidates:
        try:
            return json.loads(cand)
        except Exception:
            # try simple fixes: single quotes -> double, remove trailing commas
            fixed = cand.replace("'", '"')
            fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
            try:
                return json.loads(fixed)
            except Exception:
                pass
    # 2) fallback to ast.literal_eval (accepts Python dict syntax)
    for cand in candidates:
        try:
            return ast.literal_eval(cand)
        except Exception:
            pass
    # 3) try to extract key:value pairs like "score: 0.75" using regex
    m_score = re.search(r'score"\s*[:=]\s*([0-9]*\.?[0-9]+)', text) or re.search(r'score\s*[:=]\s*([0-9]*\.?[0-9]+)', text)
    m_just = re.search(r'justification"\s*[:=]\s*"(.*?)"', text, re.DOTALL) or re.search(r'justification\s*[:=]\s*"(.*?)"', text, re.DOTALL)
    if m_score:
        out = {"score": float(m_score.group(1))}
        if m_just:
            out["justification"] = m_just.group(1).strip()
        return out
    return None

def evaluate_single_answer_with_llm(user_answer, correct_answer, question, max_retries=3):
    """Évaluation utilisant OpenRouter au lieu de Gemini"""
    try:
        # Pré-check 1: copie de l'énoncé
        sim_with_question = text_similarity(user_answer, question)
        sim_with_expected = text_similarity(user_answer, correct_answer)
        logger.debug(f"Sim(question)={sim_with_question:.3f}, Sim(expected)={sim_with_expected:.3f}")

        # Vérification de copie
        COPY_THRESHOLD = 0.80
        if sim_with_question >= COPY_THRESHOLD or sim_with_expected >= COPY_THRESHOLD:
            return 0.0, "Réponse invalide : l'énoncé ou la réponse attendue a été recopiée."

        # Pré-check 2: présence de code
        expected_has_code = bool(re.search(r'```|input\s*\(|def\s+|print\s*\(|for\s+|while\s+|return\s+|:=', str(correct_answer)))
        candidate_has_code = bool(re.search(r'```|input\s*\(|def\s+|print\s*\(|for\s+|while\s+|return\s+|:=', str(user_answer)))

        if expected_has_code and not candidate_has_code:
            return 0.2, "Code attendu mais non fourni par le candidat."

        # Utilisation d'OpenRouter pour l'évaluation
        try:
            evaluation = evaluate_candidate_answer(user_answer, correct_answer, question)

            # Normalisation du score (OpenRouter retourne 0-10, on veut 0-1)
            score = evaluation.get('score', 0) / 10.0
            score = max(0.0, min(1.0, score))  # Clamp entre 0 et 1

            justification = evaluation.get('justification', 'Évaluation OpenRouter')

            logger.info(f"✅ Évaluation OpenRouter: score={score}, justification='{justification[:50]}...'")
            return score, justification

        except Exception as e:
            logger.warning(f"⚠️ Erreur OpenRouter: {e}")
            # Fallback local
            fallback_score = 0.5 if candidate_has_code else 0.1
            return fallback_score, "Évaluation par défaut - IA temporairement indisponible"

    except Exception as e:
        logger.exception("Erreur lors de l'évaluation")
        return 0.0, f"Erreur d'évaluation: {e}"

def evaluate_answers(user_answers, correct_answers, threshold=0.75):
    """
    Évaluation avec gestion d'erreur améliorée
    """
    results = {}
    total_questions = len(user_answers)
    
    logger.info(f"Début de l'évaluation de {total_questions} réponses")
    
    for i, (q, user_answer) in enumerate(user_answers.items(), 1):
        logger.info(f"Évaluation question {i}/{total_questions}")
        
        correct = correct_answers.get(q, "")
        
        # Vérification des réponses vides
        if not user_answer.strip() or not correct.strip():
            results[q] = {
                "user": user_answer,
                "correct": correct,
                "score": 0.0,
                "match": "false",
                "justification": "Réponse vide ou manquante",
                "evaluation_method": "empty"
            }
            continue
        
        # Évaluation par LLM avec retry
        try:
            score, justification = evaluate_single_answer_with_llm(user_answer, correct, q)
            results[q] = {
                "user": user_answer,
                "correct": correct,
                "score": score,
                "match": "true" if score >= threshold else "false",
                "justification": justification,
                "evaluation_method": "llm"
            }
        except Exception as e:
            logger.error(f"Erreur critique lors de l'évaluation de la question: {q}, erreur: {e}")
            results[q] = {
                "user": user_answer,
                "correct": correct,
                "score": 0.0,
                "match": "false",
                "justification": f"Erreur système: {str(e)[:100]}",
                "evaluation_method": "error"
            }
    
    logger.info(f"Évaluation terminée: {len(results)} résultats générés")
    return results


# ========== FONCTIONS UTILITAIRES SUPPLÉMENTAIRES ==========
def validate_evaluation_results(results):
    """
    Validation des résultats d'évaluation
    """
    if not results:
        logger.warning("Aucun résultat d'évaluation à valider")
        return False
    
    valid_count = 0
    for q, result in results.items():
        if isinstance(result.get("score"), (int, float)) and 0 <= result["score"] <= 1:
            valid_count += 1
        else:
            logger.warning(f"Score invalide pour la question '{q}': {result.get('score')}")
    
    logger.info(f"Validation: {valid_count}/{len(results)} résultats valides")
    return valid_count == len(results)


def get_evaluation_summary(results):
    """
    Résumé statistique de l'évaluation
    """
    if not results:
        return {"total": 0, "average_score": 0.0, "passed": 0, "failed": 0}
    
    scores = [r["score"] for r in results.values() if isinstance(r.get("score"), (int, float))]
    passed = sum(1 for r in results.values() if r.get("match") == "true")
    
    return {
        "total": len(results),
        "average_score": round(sum(scores) / len(scores) if scores else 0.0, 3),
        "passed": passed,
        "failed": len(results) - passed,
        "success_rate": round(passed / len(results) * 100, 1) if results else 0.0
    }