# Génération d'Exercices Techniques

Ce guide explique comment utiliser le système de génération automatique d'exercices techniques basé sur l'Intelligence Artificielle.

## Vue d'ensemble

Le système utilise Google Gemini AI pour générer des exercices techniques personnalisés basés sur :
- Le contenu d'un CV candidat
- Une base de connaissances technique (PDFs)
- Des algorithmes de recherche sémantique (FAISS + Sentence Transformers)

## Prérequis

### 1. Configuration de l'API Google Gemini
```bash
# Définir la clé API dans les variables d'environnement
export GOOGLE_API_KEY="votre_clé_api_google"
```

### 2. Préparation de la base de connaissances
- Placer les documents PDF techniques dans le dossier `data/`
- Les PDFs doivent contenir des concepts techniques pertinents
- Formats supportés : PDF

### 3. Installation des dépendances
```bash
pip install -r requirements.txt
```

## Utilisation

### Génération d'exercices

Le processus principal se déroule dans `agent.py` :

```python
from agent import generate_questions_from_cv, build_vector_store

# 1. Construire la base de connaissances
index, texts = build_vector_store()

# 2. Texte du CV (exemple)
cv_text = """
Expérience en développement Python, machine learning...
"""

# 3. Générer des exercices
exercises = generate_questions_from_cv(cv_text, texts, n=3)

for exercise in exercises:
    print(exercise)
```

### Format des exercices générés

Chaque exercice suit ce format standard :

```
Exercice : [Titre clair et court]
Description : [Explication complète de la tâche avec détails sur les entrées,
sorties attendues et contraintes. Rédigez comme une consigne d'énoncé.]
```

### Exemple de sortie

```
Exercice : Calcul de la factorielle
Description : Écrivez une fonction récursive qui calcule la factorielle d'un nombre entier positif n.
La fonction doit prendre un paramètre n et retourner n!. Par exemple, factorielle(5) doit retourner 120.
N'utilisez pas de boucles, uniquement la récursion.
```

## Fonctionnement technique

### 1. Extraction de texte des PDFs
```python
def extract_text_from_pdf(file_path):
    # Utilise PyPDF2 pour extraire le texte
```

### 2. Construction des embeddings
```python
# Utilise SentenceTransformer pour créer des vecteurs
st_model = SentenceTransformer("all-mpnet-base-v2")
```

### 3. Recherche sémantique
```python
# FAISS pour la recherche rapide dans les documents
index = faiss.IndexFlatL2(dim)
```

### 4. Génération avec Gemini
```python
model = genai.GenerativeModel("gemini-1.5-flash")
response = model.generate_content(prompt)
```

## Évaluation des réponses

Le système peut également évaluer les réponses des candidats :

```python
from agent import evaluate_single_answer_with_llm

score, justification = evaluate_single_answer_with_llm(
    user_answer="def factorielle(n): return n * factorielle(n-1) if n > 0 else 1",
    correct_answer="def factorielle(n): return 1 if n == 0 else n * factorielle(n-1)",
    question="Écrivez une fonction récursive pour calculer la factorielle"
)

print(f"Score: {score}")  # Entre 0 et 1
print(f"Justification: {justification}")
```

## Configuration avancée

### Variables d'environnement
```bash
# Modèle de génération
GEN_MODEL="gemini-1.5-flash"

# Modèle d'évaluation
EVAL_MODEL="gemini-1.5-flash"

# Dossiers
UPLOAD_FOLDER="mycv"
KNOWLEDGE_FOLDER="data"
RESPONSES_FOLDER="responses"
```

### Personnalisation des prompts
Modifier le prompt dans `generate_questions_from_cv()` pour :
- Changer le nombre d'exercices
- Modifier le format de sortie
- Adapter le niveau de difficulté
- Spécifier le langage de programmation

## Dépannage

### Erreurs communes

1. **GOOGLE_API_KEY manquante**
   ```
   ❌ GOOGLE_API_KEY not found in environment variables
   ```
   Solution : Définir la variable d'environnement

2. **Aucun PDF dans data/**
   ```
   No PDF files found in knowledge folder
   ```
   Solution : Ajouter des PDFs techniques

3. **Quota API dépassé**
   ```
   Quota exceeded
   ```
   Solution : Attendre la réinitialisation du quota ou utiliser des questions prédéfinies

4. **Erreur d'extraction JSON**
   ```
   Impossible d'extraire JSON
   ```
   Solution : Vérifier le format de réponse de Gemini

### Mode de secours
Si Gemini n'est pas disponible, le système utilise des questions prédéfinies :
- Calcul de somme
- Vérification pair/impair
- Maximum de trois nombres

## Intégration dans l'application

L'agent est intégré dans `flask_app.py` pour :
- Générer des tests lors de l'inscription candidat
- Évaluer automatiquement les réponses
- Stocker les résultats en base de données

## Métriques et monitoring

Le système loggue :
- Nombre d'exercices générés
- Temps de réponse de l'API
- Taux de succès des évaluations
- Erreurs et fallbacks utilisés

## Sécurité

- Validation des entrées utilisateur
- Sanitisation des données
- Gestion des erreurs robuste
- Logs d'audit

## Support et contribution

Pour des questions ou contributions :
- Vérifier les logs détaillés
- Tester avec `python agent.py`
- Consulter la documentation API Google Gemini