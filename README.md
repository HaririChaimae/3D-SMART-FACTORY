# 🚀 Entretien Automatisé - Plateforme de Recrutement IA

Une plateforme moderne de recrutement alimentée par l'intelligence artificielle pour connecter les meilleurs talents avec les entreprises innovantes.

## ✨ Fonctionnalités

### 🤖 Intelligence Artificielle Avancée
- **Analyse automatique de CV** : Extraction intelligente des compétences, expériences et formations
- **Matching prédictif** : Algorithme IA pour trouver les meilleurs candidats
- **Évaluation automatisée** : Tests techniques générés dynamiquement

### 🎯 Pour les Candidats
- Recherche d'emplois avec filtres avancés
- Upload de CV avec analyse instantanée
- Matching personnalisé basé sur les compétences
- Tests techniques interactifs

### 👔 Pour les Recruteurs
- Tableau de bord complet de gestion des offres
- Suivi des candidatures en temps réel
- Génération automatique de tests techniques
- Statistiques détaillées des performances

### 👑 Pour les Administrateurs
- Gestion complète des utilisateurs
- Supervision des recrutements
- Analytics et rapports détaillés

## 🛠️ Technologies Utilisées

- **Backend** : Python Flask
- **IA/ML** : Google Generative AI, LangChain, FAISS
- **Base de données** : PostgreSQL
- **Frontend** : HTML5, CSS3, JavaScript (ES6+)
- **UI/UX** : Design système professionnel avec animations

## 🚀 Installation & Démarrage

### Prérequis
- Python 3.8+
- PostgreSQL
- Git

### 1. Cloner le repository
```bash
git clone https://github.com/your-repo/entretien-automatise.git
cd entretien-automatise
```

### 2. Créer un environnement virtuel
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configuration de la base de données
```bash
# Créer une base de données PostgreSQL
createdb entretien_automatise

# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos paramètres
```

### 5. Initialiser la base de données
```bash
python -c "from db import create_tables; create_tables()"
```

### 6. Lancer l'application

#### 🚀 Option 1 : DÉMARRAGE RAPIDE (Recommandé)
Configuration automatique en 2 minutes :
```bash
python quick_start.py
```
Cette commande :
- ✅ Installe automatiquement les dépendances
- ✅ Configure une base de données SQLite
- ✅ Crée des données de test (offres, comptes)
- ✅ Lance l'application immédiatement

#### 🔧 Option 2 : Configuration manuelle
```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos paramètres

# 3. Initialiser la base de données
python -c "from db import create_tables; create_tables()"

# 4. Lancer l'application
python flask_app.py
```

#### 🔍 Option 3 : Diagnostic complet
```bash
# Vérifier la configuration avant lancement
python diagnostics.py

# Puis lancer
python flask_app.py
```

L'application sera accessible sur : http://127.0.0.1:5000

#### 📊 Comptes de test créés automatiquement :
- **Recruteur** : `recruiter@gmail.com` / `123`
- **Admin** : `admin@gmail.com` / `123`

### 7. Dépannage
Si vous rencontrez des problèmes :

```bash
# Vérifiez votre configuration
python diagnostics.py

# Consultez les logs détaillés
python flask_app.py  # Les erreurs sont affichées dans la console
```

#### Problèmes courants :

**❌ "Quota exceeded" Google API**
- Solution : Ajoutez une clé API Google dans `.env`
- Alternative : L'application fonctionne avec des questions prédéfinies

**❌ "Email not configured"**
- Solution : Configurez `EMAIL_USER` et `EMAIL_PASSWORD` dans `.env`
- Alternative : Les identifiants sont affichés dans les logs console

**❌ "Database connection failed"**
- Solution : Vérifiez PostgreSQL et `DATABASE_URL` dans `.env`

## 🔧 Corrections Fonctionnelles (Version 2.0)

### ✅ Problèmes Résolus

**1. Extraction des Compétences lors de l'Upload CV**
- ✅ Analyse automatique du CV avec IA Google Generative AI
- ✅ Extraction précise des compétences techniques
- ✅ Affichage des compétences détectées en temps réel
- ✅ Matching prédictif basé sur les compétences extraites

**2. Filtrage des Jobs Fonctionnel**
- ✅ Filtres dynamiques par localisation et type de contrat
- ✅ Recherche en temps réel avec suggestions
- ✅ Interface responsive avec animations fluides
- ✅ Mise à jour automatique des résultats

**3. Formulaire d'Application Intégré**
- ✅ Redirection automatique vers formulaire d'application
- ✅ Validation des données côté client et serveur
- ✅ Upload sécurisé de CV avec vérifications
- ✅ Confirmation par email automatique
- ✅ Gestion des candidatures dupliquées

**4. Système d'Email Automatique**
- ✅ Email de confirmation de candidature
- ✅ Génération automatique de tests techniques
- ✅ Email d'invitation au test avec identifiants
- ✅ Notifications aux recruteurs des résultats
- ✅ Gestion complète du workflow candidat

### 🎯 Nouvelles Fonctionnalités

**Interface Utilisateur**
- ✅ Design professionnel avec animations CSS intégrées
- ✅ Composants interactifs avec JavaScript natif
- ✅ Interface responsive pour tous les appareils
- ✅ Palette de couleurs cohérente et moderne

**Fonctionnalités Avancées**
- ✅ Extraction IA des compétences depuis les CV
- ✅ Matching prédictif avec scores de compatibilité
- ✅ Tests techniques automatisés avec évaluation IA
- ✅ Tableau de bord recruteur complet
- ✅ Gestion administrative des utilisateurs

## 📋 Guide de Test

### 1. Test de l'Extraction CV
1. Allez sur la page des emplois : http://127.0.0.1:5000/jobs
2. Cliquez sur "📄 Choisir CV"
3. Sélectionnez un fichier PDF ou DOCX
4. Cliquez sur "🎯 Matcher"
5. Vérifiez l'extraction des compétences affichée

### 2. Test du Filtrage
1. Utilisez les filtres "Localisation" et "Type de contrat"
2. Observez la mise à jour en temps réel des résultats
3. Testez la recherche par mots-clés

### 3. Test du Formulaire d'Application
1. Cliquez sur "Postuler maintenant" pour une offre
2. Remplissez le formulaire d'application professionnel
3. Uploadez votre CV
4. Soumettez la candidature
5. **Vérifiez votre email** - vous recevrez automatiquement :
   - Un email de confirmation de candidature
   - Un email avec le lien vers le test technique
   - Vos identifiants de connexion (email + mot de passe généré)

### 4. Test du Système de Test Technique
1. Ouvrez l'email reçu avec le lien du test
2. Connectez-vous avec vos identifiants (email + mot de passe généré)
3. Résolvez les exercices de programmation dans l'éditeur intégré
4. Soumettez votre test
5. Les résultats sont automatiquement évalués par IA et envoyés au recruteur

### 5. Test de la Connexion Recruteur
1. Allez sur http://127.0.0.1:5000/login
2. Utilisez les identifiants : `recruteur@gmail.com` / `123`
3. Accédez au tableau de bord recruteur
4. Gérez les candidatures reçues

## 🎨 Design Professionnel

### Interface Utilisateur
- **Design System Cohérent** : Palette de couleurs professionnelle
- **Animations Fluides** : Transitions et effets visuels modernes
- **Responsive Design** : Optimisé pour tous les appareils
- **Accessibilité** : Conformité aux standards WCAG

### Composants Clés
- **Navigation Fixe** : Header professionnel avec animations
- **Cartes Interactives** : Design moderne avec hover effects
- **Formulaires Élégants** : Champs stylisés avec validation
- **Boutons Dynamiques** : États actifs avec micro-animations
- **Messages Contextuels** : Alerts stylisés pour les retours utilisateur

## 📁 Structure du Projet

```
entretien-automatise/
├── flask_app.py              # Application Flask principale
├── db.py                     # Gestion de la base de données
├── requirements.txt          # Dépendances Python
├── .env                      # Variables d'environnement
├── templates/                # Templates HTML
│   ├── base.html            # Template de base professionnel
│   ├── index.html           # Page d'accueil
│   ├── jobs.html            # Recherche d'emplois
│   ├── login.html           # Connexion
│   └── recruiter_profile.html
├── static/                  # Assets statiques
│   ├── css/
│   │   └── style.css        # Styles professionnels
│   └── js/
│       └── main.js          # JavaScript interactif
├── agent.py                 # IA et traitement de documents
├── matching.py              # Algorithmes de matching
├── preprocessing.py         # Prétraitement des données
├── parsing.py               # Parsing de CV
└── data/                    # Documents et ressources
```

## 🔧 Configuration

### Variables d'Environnement (.env)
```env
# Base de données
DATABASE_URL=postgresql://user:password@localhost/entretien_automatise

# IA Google
GOOGLE_API_KEY=your_google_api_key

# Email
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Sécurité
SECRET_KEY=your_secret_key
```

### Base de Données
Le système utilise PostgreSQL avec les tables suivantes :
- `candidates` : Candidats et leurs informations
- `recruiters` : Recruteurs et entreprises
- `jobs` : Offres d'emploi
- `resumes` : CV uploadés et analysés
- `applications` : Candidatures

## 🎯 Utilisation

### Pour les Candidats
1. **Inscription** : Créer un compte candidat
2. **Upload CV** : Importer votre CV (PDF/DOCX)
3. **Recherche** : Utiliser les filtres pour trouver des offres
4. **Matching** : Recevoir des recommandations personnalisées
5. **Tests** : Passer des évaluations techniques

### Pour les Recruteurs
1. **Connexion** : Accéder au tableau de bord
2. **Créer des Offres** : Publier de nouvelles opportunités
3. **Gérer les Candidatures** : Suivre les applications
4. **Tests Automatisés** : Générer des évaluations personnalisées
5. **Analytics** : Consulter les statistiques de recrutement

## 🔒 Sécurité

- **Authentification Sécurisée** : Sessions Flask avec encryption
- **Validation des Données** : Sanitisation des inputs utilisateur
- **Protection CSRF** : Tokens anti-falsification
- **Chiffrement** : Données sensibles encryptées
- **Logs d'Audit** : Traçabilité des actions importantes

## 📊 Métriques & Analytics

### Pour les Recruteurs
- Taux de conversion des candidatures
- Temps moyen de recrutement
- Score de matching moyen
- Statistiques des tests techniques

### Pour l'Admin
- Utilisation globale de la plateforme
- Performance des algorithmes IA
- Métriques de satisfaction utilisateur
- Rapports détaillés d'activité

## 🚀 Déploiement

### Production
```bash
# Utiliser Gunicorn pour le serveur WSGI
pip install gunicorn
gunicorn -w 4 flask_app:app

# Ou avec Docker
docker build -t entretien-automatise .
docker run -p 5000:5000 entretien-automatise
```

### Variables de Production
```env
FLASK_ENV=production
DEBUG=False
SECRET_KEY=your_production_secret_key
DATABASE_URL=your_production_db_url
```

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📝 Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 📞 Support

Pour toute question ou support :
- 📧 Email : support@entretien-automatise.com
- 💬 Discord : [Rejoindre notre communauté](https://discord.gg/entretien-ai)
- 📖 Documentation : [docs.entretien-automatise.com](https://docs.entretien-automatise.com)

---

<div align="center">
  <p><strong>Entretien Automatisé</strong> - Révolutionner le recrutement avec l'IA</p>
  <p>
    <a href="#demo">🎬 Démo</a> •
    <a href="#docs">📚 Documentation</a> •
    <a href="#support">🆘 Support</a>
  </p>
</div>