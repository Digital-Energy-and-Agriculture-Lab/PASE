<!--
GABARIT DE NOTE DE CONCEPTION — ne modifiez pas ce fichier.

Copiez-le sous le nom <nom>-<sujet>.md (par exemple dupont-B.md), dans ce même dossier.

Les commentaires HTML comme celui-ci ne s'affichent pas dans GitLab. Supprimez-les au fur et à mesure que vous remplissez les sections.

Longueur visée : deux pages une fois rendue, soit environ 900 à 1200 mots hors tableaux et références. Les longueurs indiquées dans chaque section sont des ordres de grandeur. Si une section déborde, c'est souvent le signe que le périmètre est trop large.

Contenu attendu selon l'étape :
- MR n° 1 (squelette) : en-tête rempli, tous les titres en place, section 1 en trois lignes maximum.
- v1 (09/10) : toutes les sections remplies, MR proposée à la revue.
- v2 (après la revue du 16/10) : commentaires de revue traités, section 10 à jour, puis note gelée.
-->

# Note de conception — <titre court de la contribution>

| | |
|---|---|
| **Auteur·e** | <Prénom Nom> |
| **Sujet** | <A / B / C> — <intitulé du sujet> |
| **Statut** | squelette |
| **Version** | 0 |
| **MR** | <lien vers la MR courante> |
| **Dernière mise à jour** | <AAAA-MM-JJ> |

## 1. Contexte

<!--
Trois à cinq lignes. Qui pose la question, dans quelle situation, pourquoi PASE ne permet pas d'y répondre aujourd'hui.

Au stade du squelette, cette section suffit : trois lignes, même imparfaites.
-->

## 2. Besoin

<!--
Cinq à dix lignes. Formulez la question à laquelle votre contribution doit permettre de répondre, du point de vue de l'utilisateur ou de l'utilisatrice de PASE, pas du point de vue du code.

Précisez qui utilise le résultat, sous quelle forme (grandeur, unité, résolution temporelle et spatiale) et pour quelle décision.
-->

## 3. Existant dans PASE

<!--
Cinq à dix lignes. Ce que PASE fait déjà et qui est pertinent pour votre sujet : quelles chaînes de calcul, quels modules, quelles grandeurs sont disponibles et à quelle résolution. Ensuite, ce qui manque précisément.

Appuyez-vous sur la documentation de l'existant (L1) et faites-y des liens plutôt que de la répéter.
-->

## 4. Périmètre

### 4.1 Périmètre retenu

<!--
La contribution minimale, celle qui sera évaluée. Formulez-la sous forme d'exigences numérotées et vérifiables, par exemple :
EX-1 : PASE calcule <grandeur> à partir de <entrées>, pour tout pas de temps fourni par l'utilisateur.
-->

- **EX-1** :
- **EX-2** :

### 4.2 Extension optionnelle

<!--
Ce que vous ferez si la contribution minimale est terminée avant l'échéance. Cette section n'engage pas l'évaluation.
-->

### 4.3 Hors périmètre

<!--
Ce que vous ne ferez pas, avec une justification d'une ligne pour chaque point. C'est souvent la section la plus utile en revue : elle montre que les limites sont choisies, pas subies.
-->

## 5. Conception envisagée

### 5.1 Formalisation

<!--
Le modèle retenu : équations, variables, paramètres et leur origine. Chaque équation issue de la littérature est accompagnée de sa source, qui figure dans la section 9.

Pour chaque phénomène modélisé, distinguez ce qui se passe physiquement ou biologiquement, comment vous le formalisez, ce que PASE implémentera effectivement, et la limite connue qui en résulte.
-->

### 5.2 Architecture

<!--
Où la contribution s'insère dans PASE : modules nouveaux ou modifiés, fonctions ou classes principales, et ce qu'elles échangent avec le reste du code.

Un diagramme Mermaid est bienvenu si l'enchaînement n'est pas évident.
-->

**Interfaces**

<!--
Entrées et sorties principales. L'unité et le domaine de validité sont obligatoires.
-->

| Nom | Entrée / sortie | Type | Unité | Domaine de validité |
|---|---|---|---|---|
| | | | | |

### 5.3 Hypothèses et limites connues

<!--
Les hypothèses de modélisation et d'implémentation, énoncées explicitement : résolution temporelle, résolution spatiale, régime stationnaire ou non, grandeurs négligées, etc. Pour chacune, la conséquence sur l'interprétation des résultats.

Une limite documentée n'est pas un défaut. Une limite découverte par le relecteur ou la relectrice en est un.
-->

## 6. Critères d'acceptation

<!--
Les conditions qui permettent de dire que la contribution est terminée. Chaque critère est vérifiable par quelqu'un d'autre que vous et renvoie à au moins une exigence de la section 4.1.
-->

| Critère | Exigence(s) | Vérification |
|---|---|---|
| **CA-1** | EX-1 | |
| **CA-2** | | |

## 7. Plan de tests

<!--
Les tests unitaires prévus, en trois catégories :

- Cas nominaux : un comportement attendu dans des conditions ordinaires, comparé à une valeur de référence dont vous citez la source (littérature, calcul analytique, cas publié).
- Cas limites : bornes du domaine de validité, valeurs nulles, entrées dégénérées, erreurs attendues.
- Invariants, au moins un : une propriété vérifiable pour toute entrée valide sans valeur de référence. Par exemple conservation, bornes physiques, monotonie, symétrie, ou réduction à un cas connu quand un paramètre s'annule.

Indiquez pour chaque test le critère d'acceptation qu'il couvre.
-->

| Test | Catégorie | Référence | Critère couvert |
|---|---|---|---|
| | nominal | | CA-1 |
| | limite | | |
| | invariant | — | |

## 8. Risques

<!--
Trois à cinq risques au maximum : techniques, liés aux données, liés aux dépendances ou au calendrier. Pour chacun, ce que vous ferez pour le réduire et, s'il se réalise, le repli prévu.

Si votre sujet comporte un jalon de faisabilité, placez-le ici avec sa date.
-->

| Risque | Probabilité | Impact | Réduction | Repli |
|---|---|---|---|---|
| | | | | |

## 9. Références

<!--
Toutes les sources citées dans la note, dans un format cohérent (auteur, année, titre, revue ou éditeur, DOI si disponible).
-->

## 10. Historique des révisions

<!--
Une ligne par version. À partir de la v2, résumez les changements faits en réponse à la revue et renvoyez aux fils de discussion de la MR concernés.
-->

| Version | Date | Changements |
|---|---|---|
| 0 | | Squelette |
