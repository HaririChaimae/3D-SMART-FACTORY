#!/usr/bin/env python3
"""
Debug Email Configuration - Entretien Automatisé
===============================================

Script de débogage pour diagnostiquer les problèmes d'email.
"""

import os
import sys
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

def debug_email_config():
    """Debug complet de la configuration email"""
    print("🔍 DEBUG COMPLET - Configuration Email")
    print("=" * 60)

    # Récupérer les variables d'environnement
    email_user = os.environ.get('EMAIL_USER')
    email_password = os.environ.get('EMAIL_PASSWORD')

    print("📋 Variables d'environnement actuelles :")
    print(f"   EMAIL_USER: '{email_user}'")
    print(f"   EMAIL_PASSWORD: '{email_password}'")

    print("\n🔎 Analyse des valeurs :")

    # Vérifications détaillées
    if not email_user:
        print("❌ EMAIL_USER est vide ou None")
        return False

    if not email_password:
        print("❌ EMAIL_PASSWORD est vide ou None")
        return False

    if email_user == "your_email@gmail.com":
        print("❌ EMAIL_USER utilise encore la valeur par défaut")
        print("   💡 Remplacez par votre vraie adresse Gmail")
        return False

    if email_password == "your_app_password_here":
        print("❌ EMAIL_PASSWORD utilise encore la valeur par défaut")
        print("   💡 Remplacez par votre mot de passe d'application Gmail")
        return False

    if email_user and not email_user.endswith('@gmail.com'):
        print(f"⚠️ EMAIL_USER ({email_user}) n'est pas une adresse Gmail")
        print("   💡 Gmail est recommandé pour une configuration simple")

    if email_password and len(email_password) != 16:
        print(f"⚠️ EMAIL_PASSWORD fait {len(email_password)} caractères (devrait être 16 pour Gmail)")
        print("   💡 Vérifiez que c'est bien un mot de passe d'application")

    print("\n✅ Configuration valide détectée !")
    print("   Les emails devraient fonctionner.")

    # Test de la fonction send_email
    print("\n🧪 Test de la fonction send_email...")
    try:
        from flask_app import send_email

        test_email = input("   Entrez votre email pour le test : ").strip()

        if test_email:
            subject = "Debug Test - Configuration Email"
            body = """Test de débogage - Configuration Email

Si vous recevez cet email, votre configuration Gmail fonctionne parfaitement !

Cordialement,
Système de Debug - Entretien Automatisé"""

            print(f"   📧 Tentative d'envoi à : {test_email}")
            success = send_email(test_email, subject, body)

            if success:
                print("✅ Test réussi ! Email envoyé avec succès.")
                print("   📬 Vérifiez votre boîte de réception (et spams)")
                return True
            else:
                print("❌ Test échoué ! Consultez les logs ci-dessus.")
                return False
        else:
            print("   ⚠️ Aucun email fourni - test annulé")
            return False

    except Exception as e:
        print(f"❌ Erreur lors du test : {e}")
        return False

if __name__ == "__main__":
    print("🚀 Debug Email - Entretien Automatisé")
    print("=" * 50)

    success = debug_email_config()

    print("\n" + "=" * 60)
    if success:
        print("🎉 Configuration email opérationnelle !")
        print("   Votre application peut maintenant envoyer des emails.")
    else:
        print("❌ Problème de configuration détecté")
        print("   Suivez les instructions ci-dessus pour corriger")
        print("   Ou consultez EMAIL_SETUP.md pour le guide complet")

    print("\n💡 Prochaines étapes :")
    print("   1. Corrigez la configuration si nécessaire")
    print("   2. Relancez l'application : python flask_app.py")
    print("   3. Testez une candidature complète")
    print("   4. Vérifiez la réception des emails")