#!/usr/bin/env python3
"""
🔍 Script de Diagnostic - Entretien Automatisé
==============================================

Ce script vérifie la configuration de votre application Flask
et identifie les problèmes potentiels.
"""

import os
import sys
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
import psycopg2
import requests

# Charger les variables d'environnement
load_dotenv()

def print_header(text):
    """Affiche un en-tête formaté"""
    print(f"\n{'='*60}")
    print(f"🔍 {text}")
    print('='*60)

def check_database():
    """Vérifie la connexion à la base de données"""
    print_header("VÉRIFICATION BASE DE DONNÉES")

    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL non configurée")
        print("   Ajoutez DATABASE_URL=postgresql://user:password@localhost/dbname dans .env")
        return False

    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        cur.close()
        conn.close()

        print("✅ Connexion PostgreSQL réussie")
        print(f"   Version: {version[0][:50]}...")
        return True

    except psycopg2.Error as e:
        print(f"❌ Erreur de connexion PostgreSQL: {e}")
        print("   Vérifiez que PostgreSQL est installé et que la base existe")
        print("   Commandes utiles:")
        print("   - sudo apt install postgresql postgresql-contrib  # Ubuntu/Debian")
        print("   - brew install postgresql                    # macOS")
        print("   - createdb entretien_automatise              # Créer la DB")
        return False

def check_google_api():
    """Vérifie la clé API Google"""
    print_header("VÉRIFICATION API GOOGLE")

    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        print("❌ GOOGLE_API_KEY non configurée")
        print("   Obtenez une clé sur: https://makersuite.google.com/app/apikey")
        print("   Ajoutez GOOGLE_API_KEY=votre_clé dans .env")
        return False

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        # Test simple
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Test", generation_config={'max_output_tokens': 10})

        print("✅ API Google configurée et fonctionnelle")
        print(f"   Modèle: gemini-1.5-flash")
        return True

    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "quota" in error_str.lower():
            print("⚠️  Quota Google API dépassé")
            print("   Le service fonctionne mais avec des limitations")
            print("   Attendez la réinitialisation du quota (généralement 24h)")
            print("   Ou passez à un plan payant")
            return True  # Le service existe mais quota dépassé
        else:
            print(f"❌ Erreur API Google: {e}")
            print("   Vérifiez votre clé API")
            return False

def check_email():
    """Vérifie la configuration email"""
    print_header("VÉRIFICATION EMAIL")

    email_user = os.environ.get('EMAIL_USER')
    email_password = os.environ.get('EMAIL_PASSWORD')

    if not email_user or not email_password:
        print("❌ Configuration email manquante")
        print("   Ajoutez dans .env:")
        print("   EMAIL_USER=votre_email@gmail.com")
        print("   EMAIL_PASSWORD=votre_app_password")
        print("\n   📧 Pour Gmail App Password:")
        print("   1. Allez sur: https://myaccount.google.com/security")
        print("   2. Activez la vérification en 2 étapes")
        print("   3. Générez un App Password pour 'Mail'")
        return False

    try:
        # Test de connexion SMTP
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(email_user, email_password)

        print("✅ Configuration email Gmail valide")
        print(f"   Compte: {email_user}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("❌ Erreur d'authentification Gmail")
        print("   Vérifiez votre App Password")
        print("   Rappel: utilisez un App Password, PAS votre mot de passe normal")
        return False

    except Exception as e:
        print(f"❌ Erreur de connexion email: {e}")
        return False

def check_flask_app():
    """Vérifie que l'application Flask peut démarrer"""
    print_header("VÉRIFICATION APPLICATION FLASK")

    try:
        from flask_app import app

        # Test de configuration de base
        with app.app_context():
            print("✅ Application Flask configurée")
            print(f"   Debug mode: {app.debug}")
            print(f"   Secret key: {'✅ Configurée' if app.secret_key != 'your-secret-key-here' else '❌ Défaut'}")

        return True

    except ImportError as e:
        print(f"❌ Erreur d'import Flask: {e}")
        print("   Vérifiez que flask_app.py existe et que les dépendances sont installées")
        return False

    except Exception as e:
        print(f"❌ Erreur Flask: {e}")
        return False

def check_dependencies():
    """Vérifie les dépendances Python"""
    print_header("VÉRIFICATION DÉPENDANCES")

    dependencies = [
        ('flask', 'Flask'),
        ('psycopg2', 'PostgreSQL adapter'),
        ('google.generativeai', 'Google AI'),
        ('python-dotenv', 'Environment variables'),
    ]

    all_ok = True

    for module, description in dependencies:
        try:
            __import__(module)
            print(f"✅ {description}")
        except ImportError:
            print(f"❌ {description} - Module '{module}' manquant")
            all_ok = False

    if not all_ok:
        print("\n   Installez les dépendances manquantes:")
        print("   pip install -r requirements.txt")

    return all_ok

def generate_report():
    """Génère un rapport de diagnostic"""
    print_header("RAPPORT DE DIAGNOSTIC")

    results = {
        'Dépendances': check_dependencies(),
        'Base de données': check_database(),
        'API Google': check_google_api(),
        'Email': check_email(),
        'Flask': check_flask_app(),
    }

    print("\n📊 RÉSULTATS:")
    for test, result in results.items():
        status = "✅" if result else "❌"
        print(f"   {status} {test}")

    success_count = sum(results.values())
    total_count = len(results)

    print(f"\n🎯 SCORE: {success_count}/{total_count}")

    if success_count == total_count:
        print("\n🎉 Toutes les vérifications sont passées!")
        print("   Votre application devrait fonctionner correctement.")
        print("   Lancez avec: python flask_app.py")

    elif success_count >= total_count - 1:
        print("\n⚠️  Presque prêt!")
        print("   Il reste un petit problème à résoudre.")

    else:
        print("\n❌ Configuration incomplète")
        print("   Résolvez les problèmes ci-dessus avant de lancer l'application.")

    return results

def main():
    """Fonction principale"""
    print("🚀 DIAGNOSTIC - Entretien Automatisé")
    print("=" * 60)
    print("Ce script vérifie la configuration de votre application Flask")
    print("et vous aide à identifier les problèmes.\n")

    # Vérifier si .env existe
    if not os.path.exists('.env'):
        print("⚠️  Fichier .env non trouvé")
        print("   Copiez .env.example vers .env et configurez-le:")
        print("   cp .env.example .env\n")

    results = generate_report()

    # Conseils spécifiques
    if not results.get('Email', True):
        print("\n💡 CONSEIL EMAIL:")
        print("   L'email est optionnel mais recommandé pour les tests techniques.")
        print("   Sans email, les candidats recevront leurs identifiants dans les logs.")

    if not results.get('API Google', True):
        print("\n💡 CONSEIL API GOOGLE:")
        print("   Sans API Google, l'application utilise un traitement basique des CV.")
        print("   Les tests techniques auront des questions prédéfinies.")

    print("\n🔗 Liens utiles:")
    print("   📧 Gmail App Password: https://support.google.com/accounts/answer/185833")
    print("   🤖 Google AI API Key: https://makersuite.google.com/app/apikey")
    print("   📚 Documentation: Lisez le README.md pour plus de détails")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Diagnostic interrompu")
    except Exception as e:
        print(f"\n❌ Erreur lors du diagnostic: {e}")
        print("Vérifiez que Python et les dépendances de base sont installés")