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

**Vous n'avez pas besoin de clé SSH ni de jeton d'accès GitLab aujourd'hui.** 
Le dépôt PASE est public : le clone se fait en HTTPS, sans authentification. 
La configuration des accès en écriture est prévue plus tard.

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

*En séance, 5 minutes de manipulation, puis 15 à 25 minutes en arrière-plan.*

Placez-vous dans le dossier où vous voulez travailler (exemple : Documents/Cours/MA2/modelisation_agrivoltaique/), puis :

```bash
git clone https://gitlab.uliege.be/deal-public/pase.git
cd pase
mamba env create -f environment_*_students.yml
```

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

### `git clone` demande un identifiant

Vous avez probablement utilisé une URL SSH (`git@gitlab.uliege.be:...`). Utilisez l'URL
HTTPS donnée plus haut.

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
- [ ] Dépôt cloné
- [ ] Environnement `pase-students` créé et activable
- [ ] `pytest` se termine sans échec
- [ ] Document **Évaluation et livrables** lu
- [ ] Document **Sujets de projet** lu, et une préférence en tête
