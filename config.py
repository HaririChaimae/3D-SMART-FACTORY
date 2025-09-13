"""
Configuration de l'application Entretien Automatisé
==================================================

Ce fichier définit les paramètres de configuration par défaut
et gère les variables d'environnement.
"""

import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

class Config:
    """Configuration de base"""

    # Sécurité
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Base de données
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://localhost/entretien_automatise')

    # Google AI
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

    # Email
    EMAIL_USER = os.environ.get('EMAIL_USER')
    EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')

    # Flask
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')

    # Paramètres par défaut pour le développement
    DEFAULT_RECRUITER_EMAIL = 'recruiter@gmail.com'
    DEFAULT_RECRUITER_PASSWORD = '123'
    DEFAULT_ADMIN_EMAIL = 'admin@gmail.com'
    DEFAULT_ADMIN_PASSWORD = '123'

class DevelopmentConfig(Config):
    """Configuration pour le développement"""
    DEBUG = True
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    """Configuration pour la production"""
    DEBUG = False
    FLASK_ENV = 'production'

# Configuration active selon l'environnement
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Retourne la configuration active"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])()

# Instance de configuration active
current_config = get_config()

def print_config_status():
    """Affiche le statut de la configuration"""
    print("🔧 CONFIGURATION STATUS:")
    print(f"   Environment: {current_config.FLASK_ENV}")
    print(f"   Debug: {current_config.DEBUG}")
    print(f"   Database: {'✅' if current_config.DATABASE_URL else '❌'}")
    print(f"   Google API: {'✅' if current_config.GOOGLE_API_KEY else '❌'}")
    print(f"   Email: {'✅' if current_config.EMAIL_USER and current_config.EMAIL_PASSWORD else '❌'}")

    if not current_config.GOOGLE_API_KEY:
        print("   💡 Tip: Add GOOGLE_API_KEY for AI-powered CV analysis")

    if not (current_config.EMAIL_USER and current_config.EMAIL_PASSWORD):
        print("   💡 Tip: Add EMAIL_USER/EMAIL_PASSWORD for email notifications")

if __name__ == "__main__":
    print_config_status()