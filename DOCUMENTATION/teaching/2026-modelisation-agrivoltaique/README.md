# Modélisation agrivoltaïque — 2026-2027

Ce dossier rassemble les contributions des étudiant·es du cours *Modélisation agrivoltaïque : application de l'ingénierie des systèmes complexes* (Master 2 Bioingénieur, ULiège). Il vit sur la branche `develop-students`. Rien de ce qui s'y trouve n'est fusionné dans `develop` sans revue de l'équipe PASE.

Les règles du cours sont fixées dans le document d'évaluation déposé dans ce dossier. En cas de divergence entre ce README et ce document, **le document d'évaluation fait foi**.

## Contenu du dossier

```
docs/teaching/2026-modelisation-agrivoltaique/
├── README.md                          ce fichier
├── evaluation-et-livrables-v1.0.pdf   règles d'évaluation (gelées)
├── sujets-de-projet.pdf               description des sujets A, B, C
├── gabarit-note-de-conception.md      gabarit à copier, ne pas modifier
├── <nom>-<sujet>.md                   une note de conception par étudiant·e
└── l1-existant/                       documentation de l'existant (L1)
    └── README.md                      index de L1, tenu par l'encadrement
```

## Index des notes de conception

Chaque étudiant·e ajoute **une ligne** à ce tableau, dans la même MR que le squelette de sa note.

Règle : les lignes sont classées par **ordre alphabétique du nom de famille**.

| Étudiant·e | Sujet | Note de conception | Statut |
|---|---|---|---|
| Bouvry Arnaud | Sujet Z | `[bouvry-Z.md](bouvry-Z.md)` | squelette |

Valeurs admises pour la colonne *Statut* : `squelette`, `v1 en revue`, `v2 gelée`. Mettez-la à jour dans la MR qui fait changer le statut de votre note.

Le lien vers la note est relatif, par exemple `[dupont-B.md](dupont-B.md)`.

## Cycle de contribution
Voir le Wiki de PASE.

### Accès au dépôt en SSH

Le trafic SSH de l'instance GitLab ULiège passe par un hostname dédié, `ssh.gitlab.uliege.be`, et non `gitlab.uliege.be`. Si vous avez cloné en HTTPS, basculez le remote :

```bash
git remote set-url origin git@ssh.gitlab.uliege.be:deal-public/pase.git
git remote -v                       # vérification
ssh -T git@ssh.gitlab.uliege.be     # doit afficher « Welcome to GitLab, @<votre-identifiant>! »
```

### Nommage des branches

```
students/<nom>/<objet-court>
```

Exemples : `students/dupont/note-conception`, `students/dupont/l1-chaine-diffuse`.

Une branche correspond à un objet. Ne réutilisez pas une branche déjà fusionnée : repartez de `develop-students` à jour.

### Avant chaque session de travail

Synchronisez votre branche avec l'état courant de `develop-students`. Le faire uniquement au moment d'ouvrir la MR, c'est accumuler une semaine de divergence.

```bash
git fetch origin
git merge origin/develop-students
```

En cas de conflit, résolvez-le localement, puis `git add` des fichiers résolus et `git commit`. N'utilisez pas le bouton *Resolve conflicts* de l'interface GitLab.

### Règles

- Aucun push direct sur `develop-students`. Toute modification passe par une merge request.
- La cible de vos MR est toujours `develop-students`, jamais `develop` ni `main`.
- Une MR non terminée est ouverte en *Draft*. Retirez le statut *Draft* quand elle est prête à être relue.
- Vous ne fusionnez pas vos propres MR. La fusion est faite par l'encadrement après approbation.

## Revues

Chaque commentaire de revue commence par un préfixe qui indique sa portée :

| Préfixe | Signification | Effet sur la fusion |
|---|---|---|
| `[BLOQUANT]` | Erreur ou manque qui empêche la fusion | Doit être traité |
| `[RESERVE]` | Problème réel, mais qui peut être traité plus tard | À discuter, peut faire l'objet d'une issue |
| `[QUESTION]` | Demande d'explication, sans jugement | Appelle une réponse |
| `[SUGGESTION]` | Amélioration facultative | Libre à l'auteur·e |

L'auteur·e de la MR répond à chaque commentaire et résout le fil une fois le point traité. Le relecteur ou la relectrice vérifie que la résolution lui convient.

## Diagrammes

Utilisez **Mermaid**, dans un bloc de code ` ```mermaid `. GitLab le rend directement dans les fichiers et dans les diffs de MR, ce qui permet de relire les diagrammes en revue.

PlantUML n'est pas rendu par notre instance GitLab : un diagramme PlantUML y apparaît comme du texte brut.

Pour la prévisualisation locale dans PyCharm, activez le support Mermaid dans *Settings > Languages & Frameworks > Markdown*.

## Usage des outils d'IA

L'usage d'assistants IA est autorisé et encouragé. Les conditions (déclaration, vérification à l'oral) sont décrites dans le document d'évaluation.
