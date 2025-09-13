#!/usr/bin/env python3
"""
🚀 DÉMARRAGE RAPIDE - Entretien Automatisé
==========================================

Ce script configure et lance l'application avec des paramètres minimaux
pour permettre un test rapide sans configuration complexe.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def print_header(text):
    """Affiche un en-tête"""
    print(f"\n{'='*60}")
    print(f"🚀 {text}")
    print('='*60)

def check_python_version():
    """Vérifie la version Python"""
    print("🐍 Vérification Python...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Minimum requis: 3.8")
        return False

def install_dependencies():
    """Installe les dépendances"""
    print_header("INSTALLATION DÉPENDANCES")

    requirements_file = "requirements.txt"
    if not os.path.exists(requirements_file):
        print(f"❌ Fichier {requirements_file} non trouvé")
        return False

    print("📦 Installation des dépendances...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])
        print("✅ Dépendances installées")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur installation: {e}")
        return False

def create_env_file():
    """Crée un fichier .env minimal"""
    print_header("CONFIGURATION .ENV")

    if os.path.exists('.env'):
        print("ℹ️  Fichier .env existe déjà")
        return True

    print("📝 Création du fichier .env minimal...")

    env_content = """# Configuration minimale pour test rapide
SECRET_KEY=quick-start-test-key-12345
DATABASE_URL=sqlite:///test.db
FLASK_ENV=development
DEBUG=True

# Optionnel - laissez vide pour utiliser les fallbacks
GOOGLE_API_KEY=
EMAIL_USER=
EMAIL_PASSWORD=
"""

    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Fichier .env créé")
        print("💡 Vous pouvez ajouter GOOGLE_API_KEY et EMAIL_USER plus tard")
        return True
    except Exception as e:
        print(f"❌ Erreur création .env: {e}")
        return False

def setup_database():
    """Configure la base de données"""
    print_header("CONFIGURATION BASE DE DONNÉES")

    # Pour le démarrage rapide, on utilise SQLite
    print("🗄️  Configuration SQLite pour test rapide...")

    # Modifier temporairement DATABASE_URL
    os.environ['DATABASE_URL'] = 'sqlite:///quick_start.db'

    try:
        # Tester l'import et la création des tables
        from db import create_tables
        create_tables()
        print("✅ Base de données SQLite configurée")
        return True
    except Exception as e:
        print(f"❌ Erreur base de données: {e}")
        print("   Essayez: pip install psycopg2-binary")
        return False

def create_test_data():
    """Crée des données de test"""
    print_header("CRÉATION DONNÉES TEST")

    try:
        from db import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()

        # Créer un recruteur de test
        cur.execute("""
            INSERT INTO recruiters (username, email, password, profile_picture)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
        """, ('Test Recruiter', 'recruiter@gmail.com', '123', None))

        # Créer une entreprise de test
        cur.execute("""
            INSERT INTO companies (name, url, remote_friendly, market, size)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (name) DO NOTHING
        """, ('TechCorp', 'https://techcorp.com', True, 'Technology', '50-200'))

        # Récupérer l'ID de l'entreprise
        cur.execute("SELECT id FROM companies WHERE name = %s", ('TechCorp',))
        company_id = cur.fetchone()[0]

        # Récupérer l'ID du recruteur
        cur.execute("SELECT id FROM recruiters WHERE email = %s", ('recruiter@gmail.com',))
        recruiter_id = cur.fetchone()[0]

        # Créer des offres d'emploi de test
        jobs_data = [
            {
                'title': 'Développeur Python Senior',
                'description': 'Nous recherchons un développeur Python expérimenté pour rejoindre notre équipe.',
                'skills': ['python', 'django', 'postgresql', 'api'],
                'location': 'Paris',
                'type': 'full-time',
                'salary_from': 45000,
                'salary_to': 65000
            },
            {
                'title': 'Data Scientist',
                'description': 'Poste de Data Scientist pour analyser nos données et créer des modèles prédictifs.',
                'skills': ['python', 'machine learning', 'pandas', 'scikit-learn'],
                'location': 'Remote',
                'type': 'full-time',
                'salary_from': 50000,
                'salary_to': 70000
            },
            {
                'title': 'Développeur Frontend React',
                'description': 'Recherche développeur frontend expérimenté en React pour notre application web.',
                'skills': ['javascript', 'react', 'typescript', 'css'],
                'location': 'Lyon',
                'type': 'full-time',
                'salary_from': 40000,
                'salary_to': 55000
            }
        ]

        for job in jobs_data:
            cur.execute("""
                INSERT INTO jobs (company_id, recruiter_id, title, description, skills, location, type,
                                salary_from, salary_to, salary_currency, posted)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_DATE)
                ON CONFLICT DO NOTHING
            """, (
                company_id, recruiter_id, job['title'], job['description'],
                job['skills'], job['location'], job['type'],
                job['salary_from'], job['salary_to'], 'EUR'
            ))

        conn.commit()
        cur.close()
        conn.close()

        print("✅ Données de test créées")
        print("   - 1 recruteur: recruiter@gmail.com / 123")
        print("   - 1 entreprise: TechCorp")
        print("   - 3 offres d'emploi")
        return True

    except Exception as e:
        print(f"❌ Erreur création données test: {e}")
        return False

def start_application():
    """Lance l'application"""
    print_header("LANCEMENT APPLICATION")

    print("🌐 Démarrage du serveur Flask...")
    print("📱 L'application sera accessible sur: http://127.0.0.1:5000")
    print("🛑 Appuyez sur Ctrl+C pour arrêter")
    print()

    try:
        # Importer et lancer l'application
        from flask_app import app

        # Forcer SQLite pour le démarrage rapide
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quick_start.db'

        print("✅ Application démarrée avec succès!")
        print("\n🔗 Liens importants:")
        print("   🏠 Accueil: http://127.0.0.1:5000")
        print("   💼 Offres: http://127.0.0.1:5000/jobs")
        print("   🔐 Login: http://127.0.0.1:5000/login")
        print("\n📧 Comptes de test:")
        print("   👔 Recruteur: recruiter@gmail.com / 123")
        print("   👑 Admin: admin@gmail.com / 123")

        app.run(host='127.0.0.1', port=5000, debug=True)

    except ImportError as e:
        print(f"❌ Erreur import: {e}")
        print("   Vérifiez que flask_app.py existe")
    except Exception as e:
        print(f"❌ Erreur démarrage: {e}")

def main():
    """Fonction principale"""
    print("🚀 DÉMARRAGE RAPIDE - Entretien Automatisé")
    print("=" * 60)
    print("Configuration automatique pour test immédiat")
    print("Appuyez sur Ctrl+C à tout moment pour annuler\n")

    # Étape 1: Vérifications de base
    if not check_python_version():
        return

    # Étape 2: Installation dépendances
    if not install_dependencies():
        print("❌ Installation des dépendances échouée")
        print("   Essayez: pip install -r requirements.txt")
        return

    # Étape 3: Configuration .env
    if not create_env_file():
        return

    # Étape 4: Configuration base de données
    if not setup_database():
        print("❌ Configuration base de données échouée")
        print("   L'application peut quand même démarrer avec des limitations")
        input("Appuyez sur Entrée pour continuer...")

    # Étape 5: Création données test
    if not create_test_data():
        print("⚠️  Données de test non créées - l'application fonctionnera quand même")

    # Étape 6: Lancement
    print("\n" + "="*60)
    print("🎉 CONFIGURATION TERMINÉE!")
    print("="*60)
    print("Votre application est prête à être testée.")
    print("Elle inclut:")
    print("   ✅ Interface web moderne")
    print("   ✅ 3 offres d'emploi de test")
    print("   ✅ Compte recruteur de test")
    print("   ✅ Upload et analyse de CV")
    print("   ✅ Tests techniques automatisés")
    print()

    input("Appuyez sur Entrée pour lancer l'application...")

    try:
        start_application()
    except KeyboardInterrupt:
        print("\n\n👋 Application arrêtée")
        print("🔄 Pour relancer: python flask_app.py")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        print("🔄 Essayez: python flask_app.py")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Démarrage rapide annulé")
        print("💡 Vous pouvez toujours configurer manuellement et lancer:")
        print("   python flask_app.py")
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        print("🔧 Vérifiez votre installation Python et les permissions")