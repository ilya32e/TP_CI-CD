# Créer la VM sur un compte Azure for Students

Procédure complète, du compte vide à l'application déployée.
Durée : environ 20 minutes, dont 3 d'attente pendant la création de la VM.

---

## 1. Activer Azure for Students

https://azure.microsoft.com/fr-fr/free/students/ → **Commencer gratuitement**

- Connectez-vous avec votre **adresse e-mail universitaire**.
- **Aucune carte bancaire n'est demandée.**
- Vous recevez **100 $ de crédit valables 12 mois**.

Une fois activé, tout se passe sur https://portal.azure.com.

> Si le portail affiche « aucun abonnement », vérifiez en haut à droite que vous
> êtes bien connecté avec le compte universitaire et non un compte personnel.

---

## 2. Créer la machine virtuelle

Portail Azure → barre de recherche → **Virtual machines** → **+ Create** →
**Azure virtual machine**.

### Onglet *Basics*

| Champ | Valeur | Pourquoi |
|---|---|---|
| Subscription | `Azure for Students` | celle qui porte le crédit |
| Resource group | **Create new** → `rg-tp-cicd` | tout supprimer en une fois à la fin |
| Virtual machine name | `vm-tp-cicd` | |
| Region | `France Central` (ou `West Europe`) | proche, et disponible en student |
| Availability options | `No infrastructure redundancy required` | inutile ici |
| Security type | `Standard` | `Trusted launch` complique l'accès SSH |
| Image | **Ubuntu Server 24.04 LTS - x64 Gen2** | |
| Size | **Standard_B1s** (1 vCPU, 1 Gio) | ~8 $/mois sur le crédit, largement suffisant |
| Authentication type | **SSH public key** | exigé par la section 8 du sujet |
| Username | `azureuser` | notez-le, il ira dans un secret |
| SSH public key source | **Generate new key pair** | |
| Key pair name | `cle-tp-cicd` | |

### Onglet *Networking*

| Champ | Valeur |
|---|---|
| Public IP | **Create new** (laisser le nom par défaut) |
| NIC network security group | `Basic` |
| Public inbound ports | **Allow selected ports** |
| Select inbound ports | cocher **HTTP (80)** *et* **SSH (22)** |

> Cocher HTTP (80) **ici** évite d'avoir à créer la règle NSG à la main
> après coup. C'est l'oubli le plus fréquent : sans elle, l'application
> tourne sur la VM mais reste injoignable depuis Internet.

### Créer

**Review + create** → **Create**.

Une fenêtre **Generate new key pair** apparaît → **Download private key and
create resource**. Le fichier `cle-tp-cicd.pem` est téléchargé.

⚠️ **Il n'est téléchargeable qu'une seule fois.** Rangez-le, par exemple dans
`~/.ssh/cle-tp-cicd.pem`.

Attendez la fin du déploiement (2 à 3 minutes) → **Go to resource** →
notez l'**IP publique** affichée dans *Overview*.

---

## 3. Première connexion

Dans Git Bash :

```bash
# Ranger la clé et restreindre ses permissions (SSH refuse une clé trop ouverte)
mkdir -p ~/.ssh
mv ~/Downloads/cle-tp-cicd.pem ~/.ssh/
chmod 600 ~/.ssh/cle-tp-cicd.pem

# Se connecter (remplacez par votre IP publique)
ssh -i ~/.ssh/cle-tp-cicd.pem azureuser@VOTRE_NOUVELLE_IP
```

---

## 4. Installer Docker

Depuis `~/Desktop/TP_CI-CD`, sur votre poste :

```bash
scp -i ~/.ssh/cle-tp-cicd.pem scripts/setup-vm.sh azureuser@VOTRE_NOUVELLE_IP:~/
ssh -i ~/.ssh/cle-tp-cicd.pem azureuser@VOTRE_NOUVELLE_IP
```

Puis, **sur la VM** :

```bash
bash setup-vm.sh
exit                 # obligatoire : le groupe docker ne s'applique qu'à la session suivante
```

Vérification, depuis votre poste :

```bash
ssh -i ~/.ssh/cle-tp-cicd.pem azureuser@VOTRE_NOUVELLE_IP "docker ps"
```

Un tableau vide avec ses en-têtes = c'est bon. Si vous voyez
`permission denied ... docker daemon socket`, la reconnexion n'a pas été faite.

---

## 5. Mettre à jour les secrets GitHub

https://github.com/ilya32e/TP_CI-CD/settings/secrets/actions

| Secret | Action | Valeur |
|---|---|---|
| `AZURE_VM_HOST` | **modifier** | la nouvelle IP publique |
| `AZURE_VM_USER` | **modifier** | `azureuser` |
| `AZURE_SSH_PRIVATE_KEY` | **créer** | contenu entier de `~/.ssh/cle-tp-cicd.pem` |
| `SSH_PASSWORD` | supprimer | plus utilisé |
| `DOCKERHUB_USERNAME` | inchangé | |
| `DOCKERHUB_TOKEN` | inchangé | |

Pour la clé privée :

```bash
cat ~/.ssh/cle-tp-cicd.pem      # copier TOUT, y compris les lignes BEGIN et END
```

Collez le contenu complet, avec la première ligne `-----BEGIN RSA PRIVATE KEY-----`,
la dernière `-----END RSA PRIVATE KEY-----`, **et le saut de ligne final**.

---

## 6. Relancer le pipeline

GitHub → **Actions** → *CI/CD* → **Run workflow** → branche `main`.

Puis ouvrez `http://VOTRE_NOUVELLE_IP` dans le navigateur.

---

## Préserver le crédit étudiant

Une VM B1s consomme environ **8 $ par mois** tant qu'elle tourne — soit un an
de crédit si vous la laissez allumée en permanence. Deux réflexes :

**Arrêter la VM quand vous ne l'utilisez pas.** Portail → VM → **Stop**.
Attention : *Stop* depuis le portail libère bien la facturation (état
*Stopped (deallocated)*), alors qu'un `sudo shutdown` depuis l'intérieur de
la VM continue de facturer.

**Programmer un arrêt automatique.** VM → menu *Operations* → **Auto-shutdown**
→ activer, par exemple à 22h00.

> Si la VM est arrêtée puis redémarrée, **l'IP publique change** (sauf si vous
> la passez en *Static* dans les paramètres de l'IP). Pensez alors à mettre à
> jour le secret `AZURE_VM_HOST`. Pour éviter ça : VM → *Networking* → cliquez
> sur l'IP publique → **Static** → *Save*.

**À la fin du TP**, supprimez le groupe de ressources `rg-tp-cicd` : cela
supprime la VM, le disque, l'IP et le réseau en une seule opération, et la
facturation s'arrête complètement.
