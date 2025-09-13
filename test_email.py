#!/usr/bin/env python3
"""
Test Email Configuration - Entretien Automatisé
===============================================

Script pour tester la configuration des emails.
"""

import os
import sys
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

def test_email_config():
    """Test la configuration des emails"""
    print("📧 Test de Configuration Email - Entretien Automatisé")
    print("=" * 60)

    # Récupérer les variables d'environnement
    email_user = os.environ.get('EMAIL_USER')
    email_password = os.environ.get('EMAIL_PASSWORD')

    print("🔍 Configuration actuelle :")
    print(f"   EMAIL_USER: {email_user}")
    print(f"   EMAIL_PASSWORD: {'*' * len(email_password) if email_password else 'NOT SET'}")

    # Vérifications
    issues = []

    if not email_user:
        issues.append("❌ EMAIL_USER n'est pas défini")
    elif email_user == "your_email@gmail.com":
        issues.append("❌ EMAIL_USER utilise la valeur par défaut")

    if not email_password:
        issues.append("❌ EMAIL_PASSWORD n'est pas défini")
    elif email_password == "your_app_password_here":
        issues.append("❌ EMAIL_PASSWORD utilise la valeur par défaut")

    if email_user and email_user != "your_email@gmail.com":
        if not email_user.endswith('@gmail.com'):
            issues.append("⚠️ EMAIL_USER n'est pas une adresse Gmail (recommandé)")

    if email_password and email_password != "your_app_password_here":
        if len(email_password) != 16:
            issues.append(f"⚠️ EMAIL_PASSWORD fait {len(email_password)} caractères (devrait être 16 pour Gmail App Password)")

    if issues:
        print("\n❌ Problèmes détectés :")
        for issue in issues:
            print(f"   {issue}")

        print("\n🔧 Instructions pour corriger :")
        print("   1. Ouvrez votre fichier .env")
        print("   2. Remplacez les valeurs par défaut par vos vraies informations Gmail")
        print("   3. Exemple :")
        print("      EMAIL_USER=mon.email@gmail.com")
        print("      EMAIL_PASSWORD=abcd-efgh-ijkl-mnop")
        print("\n📖 Guide complet : consultez EMAIL_SETUP.md")

        return False
    else:
        print("\n✅ Configuration valide !")
        print("   Les emails devraient fonctionner correctement.")
        return True

def test_email_sending():
    """Test l'envoi d'un email de test"""
    print("\n📤 Test d'envoi d'email...")

    try:
        # Importer la fonction send_email
        from flask_app import send_email

        # Email de test
        test_email = input("   Entrez votre adresse email pour le test : ").strip()

        if not test_email:
            print("❌ Aucun email fourni")
            return False

        subject = "Test - Configuration Email Entretien Automatisé"
        body = """Bonjour,

Ceci est un email de test pour vérifier la configuration de votre système d'envoi d'emails.

Si vous recevez cet email, votre configuration Gmail fonctionne correctement !

Cordialement,
Système de Test - Entretien Automatisé"""

        success = send_email(test_email, subject, body)

        if success:
            print(f"✅ Email de test envoyé avec succès à {test_email}")
            print("   Vérifiez votre boîte de réception (et vos spams)")
            return True
        else:
            print("❌ Échec de l'envoi de l'email de test")
            print("   Consultez les logs ci-dessus pour les détails")
            return False

    except Exception as e:
        print(f"❌ Erreur lors du test d'envoi : {e}")
        return False

if __name__ == "__main__":
    print("🚀 Test de Configuration Email")
    print("=" * 40)

    # Test de configuration
    config_ok = test_email_config()

    if config_ok:
        # Demander si on veut tester l'envoi
        test_send = input("\n   Voulez-vous tester l'envoi d'un email ? (y/n) : ").strip().lower()

        if test_send in ['y', 'yes', 'oui']:
            test_email_sending()
        else:
            print("   Test d'envoi annulé")

    print("\n" + "=" * 60)
    print("📧 Pour plus d'aide, consultez EMAIL_SETUP.md")
    print("🔧 Ou visitez : https://myaccount.google.com/security")