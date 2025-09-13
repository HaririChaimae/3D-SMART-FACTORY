#!/usr/bin/env python3
"""
Démarrage Rapide - Entretien Automatisé
=====================================

Script de démarrage automatique qui configure tout en 30 secondes.
"""

import os
import sys
import shutil
from pathlib import Path

def setup_environment():
    """Configure l'environnement automatiquement"""
    print("🚀 Configuration automatique - Entretien Automatisé")
    print("=" * 60)

    # 1. Vérifier/copier .env
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            print("📋 Copie du fichier de configuration...")
            shutil.copy('.env.example', '.env')
            print("✅ Fichier .env créé")
        else:
            print("❌ Fichier .env.example introuvable")
            return False

    # 2. Forcer SQLite pour éviter les problèmes PostgreSQL
    env_file = '.env'
    env_content = ""
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            env_content = f.read()

    # Remplacer PostgreSQL par SQLite si nécessaire
    if 'postgresql://' in env_content:
        print("🔄 Configuration SQLite pour simplicité...")
        env_content = env_content.replace(
            'postgresql://username:password@localhost/entretien_automatise',
            'sqlite:///entretien_automatise.db'
        )

        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("✅ Base de données configurée: SQLite")

    # 3. Créer les dossiers nécessaires
    folders = ['static/css', 'static/js', 'templates', 'mycv', 'data', 'responses']
    for folder in folders:
        Path(folder).mkdir(parents=True, exist_ok=True)
    print("✅ Dossiers créés")

    # 4. Tester OpenRouter
    try:
        from openrouter_client import openrouter_client
        if openrouter_client.is_available():
            print("✅ OpenRouter configuré et prêt")
        else:
            print("⚠️ OpenRouter non configuré - mode dégradé activé")
    except ImportError:
        print("⚠️ Module OpenRouter non trouvé")

    print("\n🎯 Configuration terminée!")
    return True

def start_application():
    """Démarre l'application Flask"""
    print("\n🚀 Démarrage de l'application...")
    print("=" * 40)

    try:
        # Importer et démarrer Flask
        from flask_app import app

        print("🌐 Application accessible sur: http://127.0.0.1:5000")
        print("📧 Comptes de test:")
        print("   👔 Recruteur: recruiter@gmail.com / 123")
        print("   👑 Admin: admin@gmail.com / 123")
        print("\n" + "=" * 60)

        # Démarrer le serveur
        app.run(host='127.0.0.1', port=5000, debug=True)

    except Exception as e:
        print(f"❌ Erreur de démarrage: {e}")
        print("\n🔧 Solutions possibles:")
        print("1. Vérifiez que tous les modules sont installés: pip install -r requirements.txt")
        print("2. Assurez-vous que le port 5000 n'est pas utilisé")
        print("3. Vérifiez la configuration dans .env")
        return False

def main():
    """Fonction principale"""
    print("🎯 Entretien Automatisé - Démarrage Rapide")
    print("Version Flask avec OpenRouter")
    print("=" * 60)

    # Configuration automatique
    if not setup_environment():
        print("❌ Échec de la configuration")
        sys.exit(1)

    # Démarrage de l'application
    if not start_application():
        print("❌ Échec du démarrage")
        sys.exit(1)

if __name__ == "__main__":
    main()