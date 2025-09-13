#!/usr/bin/env python3
"""
🚀 Entretien Automatisé - Démonstration Rapide
===============================================

Ce script lance l'application Flask avec le nouveau design professionnel
et les corrections apportées pour les problèmes fonctionnels.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """Vérifier si les dépendances sont installées"""
    try:
        import flask
        import psycopg2
        import google.generativeai
        print("✅ Dépendances vérifiées avec succès")
        return True
    except ImportError as e:
        print(f"❌ Dépendance manquante : {e}")
        print("Installation automatique des dépendances...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        return True

def setup_database():
    """Configuration de base de données de démonstration"""
    try:
        from db import create_tables
        create_tables()
        print("✅ Base de données initialisée")
    except Exception as e:
        print(f"⚠️  Note : Base de données non configurée : {e}")
        print("   L'application fonctionnera en mode démo limité")

def show_corrections():
    """Afficher les corrections apportées"""
    print("\n🔧 CORRECTIONS APPORTÉES")
    print("-" * 25)
    print("✅ Extraction des compétences lors de l'upload CV")
    print("✅ Filtrage des jobs fonctionnel")
    print("✅ Redirection vers formulaire d'application")
    print("✅ Routes Flask optimisées")
    print("✅ Gestion d'erreurs améliorée")
    print("✅ Interface utilisateur responsive")

def launch_app():
    """Lancer l'application Flask"""
    print("\n" + "="*60)
    print("🚀 LANCEMENT DE L'APPLICATION")
    print("="*60)
    print("📱 Application accessible sur : http://127.0.0.1:5000")
    print("🎨 Nouveau design professionnel intégré")
    print("⚡ Fonctionnalités IA activées")
    print("🔧 Corrections appliquées")
    print("="*60)
    print("Appuyez sur Ctrl+C pour arrêter le serveur")
    print("="*60 + "\n")

    # Lancer Flask
    os.system("python flask_app.py")

def main():
    """Fonction principale"""
    print("🎯 Entretien Automatisé - Plateforme de Recrutement IA")
    print("="*55)
    print("Version avec corrections fonctionnelles")

    # Vérifier les prérequis
    if not check_requirements():
        return

    # Configuration de la base de données
    setup_database()

    # Afficher les corrections
    show_corrections()

    # Informations sur le nouveau design
    print("\n🎨 DESIGN PROFESSIONNEL")
    print("-" * 22)
    print("✅ Interface moderne et élégante")
    print("✅ Animations fluides et transitions")
    print("✅ Design responsive pour tous appareils")
    print("✅ Composants professionnels intégrés")
    print("✅ CSS et JavaScript intégrés directement")
    print("✅ Palette de couleurs cohérente")
    print("✅ Typographie optimisée")

    print("\n🔧 FONCTIONNALITÉS DISPONIBLES")
    print("-" * 32)
    print("✅ Recherche d'emplois avec filtres dynamiques")
    print("✅ Upload et analyse de CV avec extraction IA")
    print("✅ Matching prédictif des compétences")
    print("✅ Tests techniques automatisés")
    print("✅ Formulaire d'application intégré")
    print("✅ Tableau de bord recruteur")
    print("✅ Interface d'administration")

    print("\n📋 COMMENT TESTER")
    print("-" * 16)
    print("1. Ouvrez http://127.0.0.1:5000 dans votre navigateur")
    print("2. Uploadez un CV pour tester l'extraction des compétences")
    print("3. Utilisez les filtres de recherche")
    print("4. Cliquez sur 'Postuler' pour tester le formulaire")
    print("5. Testez la connexion recruteur (recruteur@gmail.com / 123)")

    # Lancer l'application
    launch_app()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Application arrêtée par l'utilisateur")
        print("Merci d'avoir testé Entretien Automatisé avec les corrections !")
    except Exception as e:
        print(f"\n❌ Erreur lors du lancement : {e}")
        print("Vérifiez la configuration et réessayez.")