# 📧 Configuration des Emails - Guide Complet

## 🚨 Problème Actuel
Les emails ne s'envoient pas après la soumission du formulaire de candidature.

## ✅ Solution - Configuration Gmail

### Étape 1 : Activer la Vérification en 2 Étapes
1. Allez sur [https://myaccount.google.com/security](https://myaccount.google.com/security)
2. Dans la section "Connexion à Google", cliquez sur "Vérification en 2 étapes"
3. Suivez les instructions pour activer la vérification en 2 étapes

### Étape 2 : Créer un Mot de Passe d'Application
1. Toujours sur [https://myaccount.google.com/security](https://myaccount.google.com/security)
2. Dans la section "Connexion à Google", cliquez sur "Mots de passe d'application"
3. Vous devrez peut-être vous reconnecter
4. Sélectionnez "Mail" comme application
5. Sélectionnez "Autre (nom personnalisé)" comme appareil
6. Entrez "Entretien Automatise" comme nom
7. Cliquez sur "Générer"
8. **COPIEZ LE MOT DE PASSE GÉNÉRÉ** (16 caractères)

### Étape 3 : Configurer le fichier .env
Modifiez votre fichier `.env` avec vos vraies informations :

```env
# === EMAIL (Gmail recommandé) ===
EMAIL_USER=votre.email@gmail.com
EMAIL_PASSWORD=abcd-efgh-ijkl-mnop  # Le mot de passe d'application (pas votre mot de passe Gmail)
```

### ⚠️ IMPORTANT
- **NE JAMAIS** utiliser votre mot de passe Gmail normal
- Utilisez **UNIQUEMENT** le mot de passe d'application généré
- Le mot de passe d'application contient 16 caractères avec des tirets

## 🧪 Tester la Configuration

Après avoir configuré le `.env`, redémarrez l'application :

```bash
python flask_app.py
```

Puis testez en postulant pour une offre d'emploi. Vous devriez recevoir :
1. ✅ Email de confirmation de candidature
2. ✅ Email avec invitation au test technique

## 🔧 Dépannage

### Si les emails ne s'envoient toujours pas :

1. **Vérifiez les logs de l'application** - regardez les messages d'erreur dans le terminal
2. **Vérifiez les identifiants** - assurez-vous que EMAIL_USER et EMAIL_PASSWORD sont corrects
3. **Vérifiez Gmail** - allez dans vos paramètres Gmail > onglet "Transfert IMAP/POP" > assurez-vous que POP est activé
4. **Attendez** - Gmail peut prendre quelques minutes pour activer le nouveau mot de passe d'application

### Messages d'erreur courants :

- **"Authentication failed"** → Vérifiez le mot de passe d'application
- **"Less secure app blocked"** → Activez l'accès aux applications moins sécurisées (déconseillé, préférez les mots de passe d'application)
- **"Connection failed"** → Vérifiez votre connexion internet

## 📧 Alternative : Autres Fournisseurs d'Email

Si Gmail ne fonctionne pas, vous pouvez utiliser :

### Outlook/Hotmail :
```env
EMAIL_USER=votre.email@outlook.com
EMAIL_PASSWORD=votre_mot_de_passe_outlook
```

### Yahoo :
```env
EMAIL_USER=votre.email@yahoo.com
EMAIL_PASSWORD=votre_mot_de_passe_yahoo
```

**Note :** Pour Outlook et Yahoo, utilisez votre mot de passe normal (pas de mot de passe d'application).

## 🎯 Test Final

Une fois configuré, testez avec une vraie candidature :

1. Allez sur `http://127.0.0.1:5000/jobs`
2. Cliquez sur "Apply Now" pour une offre
3. Remplissez le formulaire avec une vraie adresse email
4. Soumettez la candidature
5. Vérifiez votre boîte email

## 📞 Support

Si vous rencontrez toujours des problèmes :
1. Vérifiez les logs de l'application pour les messages d'erreur détaillés
2. Assurez-vous que votre fournisseur d'email autorise l'envoi SMTP
3. Essayez avec un autre fournisseur d'email si Gmail ne fonctionne pas

---

**🎉 Une fois configuré, votre système d'email fonctionnera parfaitement !**