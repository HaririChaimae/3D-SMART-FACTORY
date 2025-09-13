"""
Client OpenRouter pour remplacer Google Gemini
==============================================

Utilise l'API OpenRouter avec les modèles OpenAI pour :
- Extraction de compétences depuis les CV
- Génération de questions de test
- Évaluation des réponses des candidats
"""

# Forcer l'encodage UTF-8 pour éviter les problèmes de caractères
import sys
if sys.platform.startswith('win'):
    import locale
    if locale.getpreferredencoding() != 'utf-8':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import os
from openai import OpenAI
from dotenv import load_dotenv
import json
import logging

# Charger les variables d'environnement
load_dotenv()

logger = logging.getLogger(__name__)

class OpenRouterClient:
    """Client pour l'API OpenRouter"""

    def __init__(self):
        self.api_key = os.environ.get('OPENROUTER_API_KEY')
        self.model = "openai/gpt-4o-mini"  # Modèle économique et performant

        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not configured - fallback mode activated")
            self.client = None
        else:
            try:
                self.client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=self.api_key,
                )
                logger.info("✅ OpenRouter client initialized")
            except Exception as e:
                logger.error(f"❌ OpenRouter initialization error: {e}")
                self.client = None

    def is_available(self):
        """Vérifie si le client est disponible"""
        return self.client is not None

    def generate_content(self, prompt, max_tokens=1000):
        """Génère du contenu avec OpenRouter"""
        if not self.is_available():
            raise Exception("OpenRouter client not available - check OPENROUTER_API_KEY")

        try:
            # S'assurer que le prompt est en UTF-8
            if isinstance(prompt, str):
                prompt = prompt.encode('utf-8').decode('utf-8')

            completion = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://entretien-automatise.com",
                    "X-Title": "Entretien Automatisé",
                },
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )

            response = completion.choices[0].message.content

            # S'assurer que la réponse est en UTF-8
            if isinstance(response, str):
                response = response.encode('utf-8').decode('utf-8')

            return response

        except UnicodeEncodeError as e:
            logger.warning(f"⚠️  Erreur d'encodage UTF-8: {e}")
            # Essayer avec un prompt simplifié sans caractères spéciaux
            try:
                simple_prompt = prompt.encode('ascii', 'ignore').decode('ascii')
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": simple_prompt}],
                    max_tokens=max_tokens,
                    temperature=0.7
                )
                return completion.choices[0].message.content
            except Exception:
                raise Exception("Erreur d'encodage - caractères spéciaux non supportés")

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                logger.warning("⚠️  Quota OpenRouter dépassé")
                raise Exception("OpenRouter quota exceeded")
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                logger.error("❌ Clé API OpenRouter invalide")
                raise Exception("Invalid OpenRouter API key")
            else:
                logger.error(f"❌ Erreur OpenRouter: {e}")
                raise e

# Instance globale du client
openrouter_client = OpenRouterClient()

def extract_skills_from_cv(cv_text):
    """Extrait les compétences depuis le texte du CV"""
    if not openrouter_client.is_available():
        # Fallback: extraction basique
        return _basic_skill_extraction(cv_text)

    prompt = f"""
    Analyze this CV and extract the main technical skills.
    Return only a JSON object with this structure:
    {{
        "skills": ["skill1", "skill2", ...],
        "experience_years": number,
        "education_level": "level",
        "programming_languages": ["language1", "language2", ...],
        "frameworks": ["framework1", "framework2", ...],
        "tools": ["tool1", "tool2", ...]
    }}

    CV to analyze:
    {cv_text[:2000]}  # Limit size to avoid quota errors
    """

    try:
        response = openrouter_client.generate_content(prompt, max_tokens=500)
        # Nettoyer la réponse pour extraire le JSON
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        if response.endswith('```'):
            response = response[:-3]
        response = response.strip()

        cv_data = json.loads(response)
        logger.info(f"✅ Skills extracted: {len(cv_data.get('skills', []))} found")
        return cv_data

    except json.JSONDecodeError as e:
        logger.warning(f"⚠️  JSON parsing error: {e}")
        return _basic_skill_extraction(cv_text)
    except Exception as e:
        logger.warning(f"⚠️  AI extraction error: {e}")
        return _basic_skill_extraction(cv_text)

def generate_interview_questions(knowledge_chunks, n=3):
    """Génère des questions d'entretien à partir des connaissances"""
    if not openrouter_client.is_available():
        return _fallback_questions(n)

    context = "\n---\n".join(knowledge_chunks[:3])[:3000]

    prompt = f"""
    Here is an excerpt from the technical knowledge base:
    {context}

    Generate {n} practical exercises in English based only on this content.

    Each exercise must follow exactly this format:

    Exercise: [Clear and short title]
    Description: [Complete explanation of the task, with details on expected inputs, outputs,
    and any constraints. Write as an assignment instruction.]

    ⚠️ Constraints:
    - Do not use automatic numbering (no 1., 2., etc.).
    - Respond only with the exercises, nothing else.
    - Do not use input() calls. Exercises must define input values as variables or parameters
    already provided, never through user interaction.
    """

    try:
        response = openrouter_client.generate_content(prompt, max_tokens=1000)
        text = response.text.strip()

        # Split on "Exercice :" and keep everything together
        raw_exercises = re.split(r"(?=Exercice\s*:)", text)
        questions = [ex.strip() for ex in raw_exercises if ex.strip()]

        logger.info(f"✅ {len(questions)} questions generated")
        return questions[:n]

    except Exception as e:
        logger.warning(f"⚠️  AI question generation error: {e}")
        return _fallback_questions(n)

def evaluate_candidate_answer(user_answer, correct_answer, question):
    """Évalue la réponse d'un candidat"""
    if not openrouter_client.is_available():
        # Évaluation basique
        return _basic_evaluation(user_answer, correct_answer)

    prompt = f"""
    Evaluate this candidate's answer to a programming question.

    Question: {question}

    Expected answer: {correct_answer}

    Candidate's answer: {user_answer}

    Return a JSON object with this structure:
    {{
        "score": number_between_0_and_10,
        "correct": true_or_false,
        "justification": "detailed explanation of the evaluation",
        "feedback": "improvement suggestions"
    }}
    """

    try:
        response = openrouter_client.generate_content(prompt, max_tokens=500)
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        if response.endswith('```'):
            response = response[:-3]
        response = response.strip()

        evaluation = json.loads(response)
        logger.info(f"✅ Answer evaluated - Score: {evaluation.get('score', 0)}")
        return evaluation

    except Exception as e:
        logger.warning(f"⚠️  AI evaluation error: {e}")
        return _basic_evaluation(user_answer, correct_answer)

def _basic_skill_extraction(cv_text):
    """Extraction basique des compétences (fallback)"""
    # Liste de compétences communes à rechercher
    common_skills = [
        'python', 'javascript', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust',
        'react', 'angular', 'vue', 'django', 'flask', 'spring', 'laravel',
        'sql', 'mysql', 'postgresql', 'mongodb', 'redis',
        'docker', 'kubernetes', 'aws', 'azure', 'gcp',
        'git', 'linux', 'windows', 'html', 'css', 'sass', 'bootstrap',
        'machine learning', 'ai', 'data science', 'pandas', 'numpy', 'tensorflow'
    ]

    cv_lower = cv_text.lower()
    found_skills = []

    for skill in common_skills:
        if skill in cv_lower:
            found_skills.append(skill)

    return {
        "skills": found_skills[:10],  # Limiter à 10 compétences
        "experience_years": 2,  # Valeur par défaut
        "education_level": "Bachelor",
        "programming_languages": [s for s in found_skills if s in ['python', 'javascript', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust']],
        "frameworks": [s for s in found_skills if s in ['react', 'angular', 'vue', 'django', 'flask', 'spring', 'laravel']],
        "tools": [s for s in found_skills if s in ['docker', 'kubernetes', 'git', 'aws', 'azure', 'gcp']]
    }

def _fallback_questions(n=3):
    """Questions prédéfinies (fallback)"""
    questions = [
        """Exercice : Calcul de la somme de deux nombres
Description : Écrivez une fonction en Python qui calcule la somme de deux nombres donnés. Définissez les valeurs des deux nombres comme des variables au début de votre code (par exemple, nombre1 = 5 et nombre2 = 3). La fonction doit retourner la somme de ces deux nombres. Testez votre fonction en affichant le résultat avec print().""",

        """Exercice : Vérification de parité d'un nombre
Description : Écrivez une fonction en Python qui détermine si un nombre donné est pair ou impair. Définissez le nombre à vérifier comme une variable au début de votre code (par exemple, nombre = 7). La fonction doit retourner une chaîne de caractères indiquant si le nombre est "pair" ou "impair". Testez votre fonction en affichant le résultat avec print().""",

        """Exercice : Recherche du plus grand nombre parmi trois
Description : Écrivez une fonction en Python qui trouve le plus grand nombre parmi trois nombres donnés. Définissez les trois nombres comme des variables au début de votre code (par exemple, a = 10, b = 25, c = 15). La fonction doit retourner le plus grand des trois nombres. Testez votre fonction en affichant le résultat avec print()."""
    ]

    return questions[:n]

def _basic_evaluation(user_answer, correct_answer):
    """Évaluation basique (fallback)"""
    # Vérification simple : la réponse contient-elle des éléments corrects ?
    user_lower = user_answer.lower()
    correct_lower = correct_answer.lower()

    score = 0
    if 'def' in user_lower:
        score += 3  # Fonction définie
    if 'return' in user_lower:
        score += 3  # Return statement
    if 'print' in user_lower:
        score += 2  # Affichage du résultat
    if len(user_answer.strip()) > 50:
        score += 2  # Longueur minimale

    return {
        "score": min(score, 10),
        "correct": score >= 8,
        "justification": f"Automatic evaluation - Score based on presence of correct code elements",
        "feedback": "Your code contains the basic elements. Make sure you have a function, return and print."
    }

# Fonctions de compatibilité pour remplacer Google Gemini
def generate_answer_for_question(question, index=None, texts=None):
    """Fonction de compatibilité pour remplacer generate_answer_for_question de agent.py"""
    if not openrouter_client.is_available():
        return "Réponse par défaut - IA non disponible"

    prompt = f"""
    Answer this programming question in a clear and educational way:

    Question: {question}

    Provide a complete answer with:
    1. Explanation of the concept
    2. Code example if applicable
    3. Best practices
    """

    try:
        return openrouter_client.generate_content(prompt, max_tokens=800)
    except Exception as e:
        logger.warning(f"Answer generation error: {e}")
        return f"Answer based on best practices for the question: {question[:50]}..."

def search_knowledge(query, index=None, texts=None, top_k=3):
    """Fonction de compatibilité pour remplacer search_knowledge de agent.py"""
    # Pour l'instant, retourne des chunks basés sur la requête
    if "python" in query.lower():
        return [
            "Python est un langage de programmation interprété, orienté objet et haut niveau.",
            "Les concepts fondamentaux de Python incluent les variables, les boucles, les conditions et les fonctions.",
            "La programmation orientée objet en Python utilise des classes et des objets."
        ]
    else:
        return [
            "La programmation consiste à écrire des instructions pour résoudre des problèmes.",
            "Les algorithmes sont des séquences d'étapes pour résoudre un problème.",
            "Le débogage consiste à identifier et corriger les erreurs dans le code."
        ]

# Test du client
if __name__ == "__main__":
    print("🧪 Test du client OpenRouter")
    print("=" * 40)

    if openrouter_client.is_available():
        print("✅ Client OpenRouter configuré")

        # Test simple
        try:
            response = openrouter_client.generate_content("Hello, can you tell me what Python is in one sentence?", max_tokens=100)
            print(f"📝 Test successful: {response[:100]}...")
        except Exception as e:
            print(f"❌ Test failed: {e}")
    else:
        print("❌ OpenRouter client not configured")
        print("   Add OPENROUTER_API_KEY to your .env file")