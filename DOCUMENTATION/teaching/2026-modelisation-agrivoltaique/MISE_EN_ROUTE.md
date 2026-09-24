# Mise en route — environnement de développement

- **Cours :** Modélisation agrivoltaïque — application de l'ingénierie des systèmes complexes
- **Échéance :** vendredi **25 septembre 2026**, vérifié en séance
- **Statut :** livrable L0 — seuil éliminatoire, aucun point

> Ce document est votre référence pour installer et vérifier votre environnement.
> Les étapes 1 et 2 sont faites en séance le 18/09. L'étape 3 est à terminer chez vous.

<!-- À COMPLÉTER AVANT LE 18/09 (note pour l'encadrant) :
     - vérifier que ce fichier résout sur win-64 ET linux-64 (verrouiller les versions, PAS les builds)
     - chronométrer `mamba env create` sur une machine propre ; si > 30 min, revoir le déroulé de la séance
-->

---

## Ce dont vous avez besoin

| Outil | Rôle | Vérification |
|---|---|---|
| **Miniforge** (ou Conda/Miniconda) | gestionnaire d'environnements conda/mamba | `conda --version` |
| **git** | suivi de version | `git --version` |
| **Compte GitLab ULiège** | accès au dépôt et aux merge requests | connexion à `gitlab.uliege.be` |
| **Clé SSH** enregistrée sur GitLab | authentification pour `git push` | `ssh -T git@ssh.gitlab.uliege.be` |

**Le dépôt se clone en SSH, pas en HTTPS.**
Le dépôt PASE est public: un clone HTTPS fonctionnerait pour la lecture, mais bloquerait
au premier `git push`. Autant configurer l'accès SSH dès le départ (voir [Étape 2](#étape-2--cloner-le-dépôt-et-lancer-la-création-de-lenvironnement)).

---

## Étape 1 — Miniforge et git

*En séance, 20 minutes.*

### Windows

1. Télécharger l'installateur Miniforge pour Windows (`Miniforge3-Windows-x86_64.exe`)
   depuis <https://github.com/conda-forge/miniforge#download> et l'exécuter.
   Laisser les options par défaut.
2. Télécharger et installer **Git for Windows** depuis <https://git-scm.com/download/win>.
   L'assistant pose une dizaine de questions : **acceptez les valeurs par défaut**, en
   particulier pour la gestion des fins de ligne (`Checkout Windows-style, commit Unix-style`).
3. Ouvrir **Miniforge Prompt** (menu Démarrer) — c'est ce terminal que vous utiliserez
   pour tout ce qui suit, pas PowerShell ni `cmd`.

### macOS

```bash
# Miniforge (Apple Silicon ; pour un Mac Intel, remplacer arm64 par x86_64)
curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh
bash Miniforge3-MacOSX-arm64.sh

# git : déjà présent, ou via les outils en ligne de commande Xcode
git --version
```

Fermer et rouvrir le terminal après l'installation.

### Linux

```bash
curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh

sudo apt update && sudo apt install git   # Debian / Ubuntu
```

Fermer et rouvrir le terminal après l'installation.

### Vérification

Dans un terminal **neuf** :

```bash
conda --version
mamba --version
git --version
```

Les trois commandes doivent répondre par un numéro de version. 
Si l'une d'elles renvoie `command not found` ou `n'est pas reconnu`, voir la section [Dépannage](#dépannage).

---

## Étape 2 — Cloner le dépôt et lancer la création de l'environnement

*En séance, 10 minutes de manipulation, puis 15 à 25 minutes en arrière-plan.*

### 2.1 — Configurer l'authentification SSH

Référence complète: <https://docs.gitlab.com/user/ssh/>. L'essentiel:

1. **Générer une paire de clés** (sous Windows, dans Miniforge Prompt ou Git Bash):

   ```bash
   ssh-keygen -t ed25519 -C "prenom.nom@student.uliege.be"
   ```

   Acceptez l'emplacement par défaut (`~/.ssh/id_ed25519`). Une phrase de passe est
   recommandée. Si une clé existe déjà à cet emplacement, ne l'écrasez pas: réutilisez-la.

2. **Copier la clé publique** — le fichier qui se termine par `.pub`, jamais l'autre:

   ```bash
   cat ~/.ssh/id_ed25519.pub                 # macOS / Linux / Git Bash
   type %USERPROFILE%\.ssh\id_ed25519.pub    # Miniforge Prompt (Windows)
   ```

3. **L'ajouter sur GitLab**: sur `gitlab.uliege.be`, avatar → *Edit profile* → *SSH Keys*
   → *Add new key*, coller la clé, enregistrer.

4. **Vérifier la connexion**:

   ```bash
   ssh -T git@ssh.gitlab.uliege.be
   ```

   À la première connexion, SSH demande de confirmer l'empreinte du serveur: répondez `yes`.
   Vous devez obtenir `Welcome to GitLab, @votre_identifiant!`.

> **Attention à l'hôte:** le serveur SSH est `ssh.gitlab.uliege.be`, et non `gitlab.uliege.be`.

### 2.2 — Cloner le dépôt et créer l'environnement

Pour créer l'environnement virtuel à partir du fichier de configuration, placez-vous dans le dossier où vous voulez travailler (exemple : Documents/Cours/MA2/modelisation_agrivoltaique/), puis :

```bash
git clone git@ssh.gitlab.uliege.be:deal-public/pase.git
cd pase
git checkout develop-students
mamba env create -f environment_*_students.yml
```
Note : selon votre système d'exploitation, choisissez soit `environment_windows_students.yml`, soit `environment_unix_students.yml` (OS Mac ou GNU/Linux).

> **Vous avez déjà cloné en HTTPS?** Inutile de recloner. Après l'étape 2.1, basculez le
> remote vers SSH depuis le dossier `pase`:
>
> ```bash
> git remote set-url origin git@ssh.gitlab.uliege.be:deal-public/pase.git
> git remote -v    # les deux lignes doivent afficher l'URL SSH
> ```

La dernière commande télécharge et installe l'ensemble des dépendances. **C'est long.**
Laissez le terminal tourner et ne l'interrompez pas : on reprend le cours pendant ce temps.

> **Pourquoi `environment_*_students.yml` et pas le fichier d'environnement du projet ?**
> Parce qu'il est verrouillé sur des versions connues pour fonctionner ensemble. La chaîne
> VTK / PyVista / trimesh est sensible au mélange de canaux conda, et ce n'est pas le
> sujet du cours.

---

## Étape 3 — Vérifier

*À terminer chez vous si l'installation n'a pas abouti en séance.*

```bash
conda activate pase-students
python -c "import pase; print(pase.__version__)"
python -m pytest
```

Vous devez obtenir :

- un numéro de version affiché sans erreur d'import ;
- une suite de tests qui se termine sans échec.

Des tests ignorés (`skipped`) sont normaux. Des tests en échec (`failed`) ne le sont pas :
**signalez-le**.

**C'est cet état qui est vérifié en séance le 25 septembre.**

---

## Dépannage

### `conda` ou `mamba` n'est pas reconnu

Vous n'avez probablement pas rouvert votre terminal après l'installation, ou vous
n'utilisez pas le bon terminal. Sous Windows, utilisez **Miniforge Prompt**.

### La résolution de l'environnement ne se termine pas

Coupez (`Ctrl+C`), supprimez l'environnement partiel et recommencez :

```bash
conda env remove -n pase-students
mamba env create -f environment_*_students.yml
```

Si le problème persiste, envoyez la sortie complète du terminal — pas une capture d'écran
du message final, la sortie entière.

### Conflits de paquets, erreurs d'importation de bibliothèques compilées

C'est en général un problème de **mélange de canaux** : des paquets installés depuis
`defaults` cohabitent avec des paquets `conda-forge`, avec des incompatibilités binaires
à la clé. Pour diagnostiquer :

```bash
mamba list --show-channel-urls
```

Si vous voyez un mélange de `defaults` et `conda-forge`, la solution la plus rapide est de
repartir d'un environnement neuf plutôt que d'essayer de le réparer.

### `git clone` ou `git push` demande un identifiant et un mot de passe

Vous utilisez une URL HTTPS (`https://gitlab.uliege.be/...`). Passez en SSH:

```bash
git remote set-url origin git@ssh.gitlab.uliege.be:deal-public/pase.git
```

### `Permission denied (publickey)`

- Vérifiez l'hôte: `ssh.gitlab.uliege.be`, et non `gitlab.uliege.be`.
- Vérifiez que c'est bien la clé **publique** (`.pub`) qui a été ajoutée sur GitLab.
- Lancez `ssh -Tv git@ssh.gitlab.uliege.be` pour voir quelles clés sont proposées au serveur,
  et joignez cette sortie à votre message si le problème persiste.

Voir aussi la section dépannage de la [documentation GitLab](https://docs.gitlab.com/user/ssh/).

### Windows : avertissements sur les fins de ligne (`LF will be replaced by CRLF`)

C'est un avertissement, pas une erreur. Ne modifiez pas votre configuration `core.autocrlf`.

---

## Si vous êtes bloqué

Écrivez **avant mardi 22 septembre**, pas jeudi soir. 
Un environnement cassé le 25/09 bloque tout le reste du quadrimestre, et c'est exactement le genre de problème qui se
règle en dix minutes quand il est signalé tôt.

Dans votre message, indiquez :

1. votre système d'exploitation et sa version ;
2. la commande exacte que vous avez lancée ;
3. **la sortie complète du terminal**, copiée **en texte** (fichier .txt ou similaire) et non en capture d'écran.

Contact : abouvry@uliege.be

---

## Pour le 25 septembre

- [ ] `conda --version`, `git --version` répondent
- [ ] Clé SSH ajoutée sur GitLab, `ssh -T git@ssh.gitlab.uliege.be` répond `Welcome to GitLab`
- [ ] Dépôt cloné, `git remote -v` affiche l'URL SSH
- [ ] Environnement `pase-students` créé et activable
- [ ] `pytest` se termine sans échec
- [ ] Document **Évaluation et livrables** lu
- [ ] Document **Sujets de projet** lu, et une préférence en tête
