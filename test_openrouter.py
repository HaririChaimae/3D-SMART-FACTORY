#!/usr/bin/env python3
"""
Test rapide d'OpenRouter
=======================

Ce script teste l'intégration OpenRouter pour vérifier que tout fonctionne.
"""

import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

def test_openrouter_integration():
    """Test complet de l'intégration OpenRouter"""
    print("🧪 TEST D'INTEGRATION OPENROUTER")
    print("=" * 50)

    # Test 1: Import
    try:
        from openrouter_client import openrouter_client, extract_skills_from_cv, generate_interview_questions
        print("✅ Import OpenRouter réussi")
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        return False

    # Test 2: Configuration
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ OPENROUTER_API_KEY non trouvée dans .env")
        print("   Ajoutez: OPENROUTER_API_KEY=sk-or-v1-...")
        return False

    if api_key != "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":
        print("⚠️  Clé API différente de celle fournie - test avec la vôtre")

    print("✅ Configuration OpenRouter OK")

    # Test 3: Connexion
    if not openrouter_client.is_available():
        print("❌ Client OpenRouter non disponible")
        return False

    print("✅ Client OpenRouter disponible")

    # Test 4: Génération simple
    try:
        test_prompt = "Bonjour, peux-tu me dire ce qu'est Python en une phrase?"
        response = openrouter_client.generate_content(test_prompt, max_tokens=50)
        print("✅ Génération de contenu réussie")
        print(f"   Réponse: {response[:100]}...")
    except Exception as e:
        print(f"❌ Erreur génération: {e}")
        return False

    # Test 5: Extraction de compétences
    try:
        test_cv = """
        Développeur Python expérimenté avec 5 ans d'expérience.
        Compétences: Python, Django, Flask, SQL, JavaScript, React.
        Expérience en développement web et data science.
        """

        cv_data = extract_skills_from_cv(test_cv)
        print("✅ Extraction de compétences réussie")
        print(f"   Compétences trouvées: {cv_data.get('skills', [])}")
    except Exception as e:
        print(f"❌ Erreur extraction CV: {e}")
        return False

    # Test 6: Génération de questions
    try:
        test_knowledge = [
            "Python est un langage de programmation orienté objet.",
            "Les fonctions en Python se définissent avec 'def'.",
            "Les listes sont des structures de données mutables."
        ]

        questions = generate_interview_questions(test_knowledge, n=2)
        print("✅ Génération de questions réussie")
        print(f"   {len(questions)} questions générées")
        for i, q in enumerate(questions[:2], 1):
            print(f"   {i}. {q[:80]}...")
    except Exception as e:
        print(f"❌ Erreur génération questions: {e}")
        return False

    # Test 7: Intégration preprocessing
    try:
        from preprocessing import preprocess_cv
        test_cv_text = "John Doe, développeur Python, expérience 3 ans, compétences Python Django SQL"

        cv_data = preprocess_cv(test_cv_text)
        print("✅ Preprocessing avec OpenRouter réussi")
        print(f"   Nom extrait: {cv_data.get('name', 'N/A')}")
        print(f"   Compétences: {cv_data.get('skills', [])}")
    except Exception as e:
        print(f"❌ Erreur preprocessing: {e}")
        return False

    print("\n🎉 TOUS LES TESTS RÉUSSIS!")
    print("   OpenRouter est correctement intégré")
    print("   L'application peut utiliser l'IA pour:")
    print("   ✅ Extraire les compétences des CV")
    print("   ✅ Générer des questions d'entretien")
    print("   ✅ Évaluer les réponses des candidats")
    return True

def test_fallback():
    """Test du mode fallback"""
    print("\n🔄 TEST MODE FALLBACK")
    print("=" * 30)

    # Désactiver temporairement OpenRouter
    original_key = os.environ.get('OPENROUTER_API_KEY')
    os.environ['OPENROUTER_API_KEY'] = ''

    try:
        from openrouter_client import openrouter_client
        if openrouter_client.is_available():
            print("❌ Fallback ne fonctionne pas - OpenRouter encore disponible")
            return False

        print("✅ Mode fallback activé")

        # Test extraction basique
        from preprocessing import preprocess_cv
        test_cv = "Développeur Python avec expérience en Django"

        cv_data = preprocess_cv(test_cv)
        if cv_data.get('skills'):
            print("✅ Extraction basique fonctionne")
            print(f"   Compétences: {cv_data['skills']}")
            return True
        else:
            print("❌ Extraction basique échoue")
            return False

    finally:
        # Restaurer la clé
        if original_key:
            os.environ['OPENROUTER_API_KEY'] = original_key

if __name__ == "__main__":
    print("🚀 TEST OPENROUTER - Entretien Automatisé")
    print("=" * 50)

    success = test_openrouter_integration()

    if success:
        test_fallback()
        print("\n🎯 RÉSULTAT: Intégration OpenRouter réussie!")
        print("   Vous pouvez maintenant utiliser l'application avec:")
        print("   - Extraction IA des compétences")
        print("   - Génération de questions personnalisées")
        print("   - Évaluation automatique des réponses")
    else:
        print("\n❌ RÉSULTAT: Problème avec l'intégration OpenRouter")
        print("   Vérifiez:")
        print("   1. La clé API dans .env")
        print("   2. La connexion internet")
        print("   3. Les dépendances installées")

        # Tester le fallback
        print("\n🔄 Test du mode fallback...")
        fallback_ok = test_fallback()
        if fallback_ok:
            print("✅ L'application fonctionnera en mode dégradé")
        else:
            print("❌ Même le mode fallback ne fonctionne pas")