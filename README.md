# Assistant Code du travail — RAG juridique

Assistant conversationnel de questions-réponses sur le droit du travail français, fondé sur une architecture **RAG** (Retrieval-Augmented Generation). Le système répond en langage naturel à des questions juridiques en s'appuyant exclusivement sur les articles du Code du travail en vigueur, **cite systématiquement les articles** sur lesquels il fonde ses réponses, et **refuse de répondre** lorsque l'information ne figure pas dans sa base plutôt que d'inventer.

**Dépôt du projet :** https://github.com/justmarruecos/RAG-Assistantcodedutravail

---

## Objectif

Fournir un accès simplifié et traçable au droit du travail. Le système vise des questions telles que :

- « Quelle est la durée légale du préavis pour un CDI ? »
- « Combien d'heures supplémentaires peut-on faire par semaine ? »
- « Comment fonctionne la rupture conventionnelle ? »

Chaque réponse est accompagnée des références d'articles et d'un avertissement rappelant que l'assistant ne se substitue pas à un conseil juridique professionnel.

---

## Architecture

Le système suit une architecture RAG en deux phases strictement séparées :

**Phase d'indexation** (exécutée une fois, puis à chaque mise à jour du corpus)
Extraction du corpus → nettoyage → découpage (chunking) → vectorisation (embeddings) → persistance de la base vectorielle sur disque.

**Phase d'interrogation** (exécutée à chaque question)
Modération de la requête → formation/décomposition de la question → recherche des passages pertinents (HyDE, lookup exact par numéro d'article, ou mode comparaison selon le cas) → construction du prompt → génération de la réponse avec citations.

Le code sépare ces responsabilités : un module d'indexation (`chunking.py`, `vector_db.py`, `index.py`), un module de prétraitement de la question (`agent_question.py`), un module de modération (`moderation.py`), et un module de génération (`generation.py`). La base vectorielle est persistée et rechargée au démarrage, sans réindexation.

---

## Jeu de données

| | |
|---|---|
| **Source des données brutes** | Dépôt GitHub `SocialGouv/legi-data` |
| **URL source** | https://github.com/SocialGouv/legi-data |
| **Fichier utilisé** | `data/LEGITEXT000006072050.json` (Code du travail consolidé) |
| **Origine des données** | Base LEGI — Légifrance (données publiques françaises consolidées) |
| **Format source** | JSON hiérarchique (arborescence Partie > Livre > Titre > Chapitre > Article) |
| **Périmètre** | Code du travail intégral, parties législative (L) et réglementaire (R, D) |
| **Volume** | 11 486 articles en vigueur |
| **Licence** | Données publiques réutilisables |

Le corpus est constitué uniquement des articles en statut **VIGUEUR** au moment de l'extraction ; les articles abrogés, modifiés ou périmés sont exclus. Chaque article conserve son numéro et sa position hiérarchique complète, exploitée comme métadonnée.

**Répartition :** 4 410 articles législatifs (L), 5 549 réglementaires (R), 1 527 décrets (D).

---

## Structure du dépôt

```
.
├── data/
│   ├── corpus_code_travail.csv     # corpus extrait (11 486 articles)
│   └── corpus_meta.json            # date de mise a jour DILA + date d'extraction
├── prompts/
│   ├── system_prompt.txt              # prompt de generation (citations, refus, comparaison)
│   ├── formation_question_prompt.txt  # prompt de l'agent de formation de question
│   └── moderation_prompt.txt          # prompt de l'agent moderateur
├── src/
│   ├── extract_corpus.py           # Jalon 1 : extraction, nettoyage, metadonnees fraicheur
│   ├── stats.py                    # controle qualite Jalon 1
│   ├── chunking.py                 # Jalon 2 : decoupage par article + overlap + sous-decoupage
│   ├── vector_db.py                # Jalon 2 : ChromaDB, ajout incremental, lookup exact, fraicheur
│   ├── index.py                    # Jalon 2 : script d'indexation complete
│   ├── audit_chunks.py             # controle qualite Jalon 2 (doublons, longueurs, troncature)
│   ├── controle_chunks.py          # controle qualite Jalon 2 (overlap, coupures)
│   ├── test_retrieval.py           # Jalon 3 : jeu d'evaluation (8 questions)
│   ├── test_hyde.py                # preuve chiffree du gain HyDE
│   ├── test_ajout_incrementel.py   # preuve de l'ajout incremental
│   ├── test_comparaison.py         # preuve de la detection du mode comparaison
│   ├── test_moderation.py          # preuve du filtrage par l'agent moderateur
│   ├── test_stabilite_generation.py   # diagnostic non-determinisme HyDE
│   ├── test_diagnostic_echec.py       # diagnostic retrieval en echec
│   ├── test_generation.py          # Jalon 4 : garanties structurelles (citations, refus)
│   ├── agent_question.py           # Jalon 6 : nettoyage + decomposition + mode comparaison
│   ├── moderation.py               # Jalon 6 : agent moderateur (anti prompt-injection)
│   ├── generation.py               # Jalon 4+6 : prompt, HyDE, fusion, lookup, garanties de code
│   └── cli.py                      # Jalon 5 : interface interactive
├── .env.example                    # variables d'environnement attendues
├── .gitattributes                  # normalise les fins de ligne (CRLF/LF) entre environnements
├── requirements.txt
└── README.md
```

---

## Installation

Prérequis : Python 3.10+.

```bash
# 1. Environnement virtuel
python -m venv venv
source venv/Scripts/activate      # Windows (Git Bash)
# source venv/bin/activate        # Linux / macOS

# 2. Dépendances
pip install -r requirements.txt

# 3. Clé API
cp .env.example .env
# renseigner GROQ_API_KEY dans le fichier .env
```

### Régénérer le corpus depuis la source

Le fichier source JSON (~54 Mo) n'est pas versionné. Il provient du dépôt GitHub `SocialGouv/legi-data`. Pour régénérer le corpus :

```bash
curl -L "https://raw.githubusercontent.com/SocialGouv/legi-data/master/data/LEGITEXT000006072050.json" -o data/code_travail.json
python -m src.extract_corpus
```

### Construire la base vectorielle

La base ChromaDB (`chroma/`) n'est pas versionnée (fichiers binaires volumineux, régénérable). À construire une fois en local :

```bash
python -m src.index
```

### Lancer l'assistant

```bash
python -m src.cli
```

---

## Décisions de conception (questions de réflexion)

### Q1 — Granularité du découpage

Le corpus est constitué d'articles courts (≈ 450 caractères en moyenne), denses, déjà délimités et numérotés. La structure juridique fournit un découpage naturel : nous adoptons une stratégie **par structure**, où **un article constitue un chunk**, en conservant sa hiérarchie (Partie > Livre > Titre > Chapitre) en métadonnée.

Ce choix garantit des unités de sens complètes et autonomes, jamais coupées en milieu de phrase, et une correspondance directe entre un chunk et une référence d'article. Les rares articles longs (> 1 500 caractères) sont découpés en sous-segments avec un chevauchement de 10–20 %, chaque segment conservant le numéro d'article d'origine pour préserver la traçabilité. Le regroupement par section entière a été écarté : il produirait des segments trop volumineux, diluant la précision de la recherche. Une approche hybride est donc retenue : article unique par défaut, sous-découpage pour les articles longs.

**Mise à jour :** un bug a confirmé concrètement ce risque en cours de développement — 5 chunks dépassaient la limite du modèle d'embedding (jusqu'à 4654 caractères), la logique de sous-découpage n'étant pas branchée dans la boucle principale de `chunking.py`. Diagnostiqué via `audit_chunks.py` (0,04 % des chunks du corpus concernés) et corrigé par un sous-découpage par mots en filet de sécurité (`_sous_decouper_si_trop_long`), vérifié avant/après (max observé : 4654 → 1674 caractères).

### Q2 — Traçabilité des sources

Le numéro d'article est conservé **à la fois dans les métadonnées et dans le texte vectorisé**, chacun servant un objectif distinct. La métadonnée constitue la **source de vérité** pour la citation ; le numéro intégré au texte permet à une recherche lexicale de retrouver un article par sa référence exacte.

La garantie contre l'invention de références repose sur un principe : **la liste des articles cités est construite par le code à partir des métadonnées des passages récupérés, et non extraite de la sortie du modèle**. Le modèle de langage n'est jamais la source des références affichées ; il rédige la réponse, le code fournit les citations vérifiées.

**Mise à jour :** cette séparation reste vraie même avec les améliorations ajoutées ensuite (HyDE, décomposition, recherche hybride) : quel que soit le chemin de recherche emprunté pour une sous-question donnée (lookup exact par numéro, ou HyDE + fusion), les métadonnées des chunks réellement retrouvés restent l'unique source des citations affichées — jamais le texte généré par le LLM, et jamais le texte hypothétique généré par HyDE (qui peut contenir des numéros d'article inventés, voir `generer_hyde` dans `src/generation.py`).

### Q3 — Fraîcheur des données

Le droit du travail évolue régulièrement. Le corpus est daté à l'extraction et ne contient que les articles en vigueur à cette date. Chaque réponse rappelle la date de référence du corpus et le risque d'évolution législative postérieure, et oriente l'utilisateur vers une source officielle à jour pour toute vérification.

**Mise à jour (implémentation) :** la date officielle de mise à jour du Code du travail (champ `dateModif` du JSON source DILA) est capturée à l'extraction dans `data/corpus_meta.json`, puis stockée dans les métadonnées de la collection ChromaDB au même titre que le modèle d'embedding — elle persiste donc avec la base et ne dépend pas d'un fichier externe après l'indexation. `VectorDB.avertissement_fraicheur(seuil_jours=90)` compare cette date à la date du jour et génère un message d'avertissement si le corpus dépasse le seuil (paramétrable) ; ce message est inclus dans chaque réponse retournée par `repondre()` lorsqu'applicable.

### Q4 — Réponses conditionnelles

De nombreuses règles dépendent de la taille de l'entreprise, de l'ancienneté du salarié ou de la convention collective applicable. Le système est conçu pour restituer la règle générale **assortie explicitement de ses conditions d'application**, plutôt qu'une réponse unique tranchée, et pour signaler qu'une convention collective peut déroger au cadre légal — le corpus ne couvrant que la loi. Les questions couvrant plusieurs notions font l'objet d'une décomposition en sous-questions afin de récupérer les articles propres à chaque volet.

**Mise à jour :** au-delà de la décomposition multi-sujets, un cas particulier a nécessité un traitement dédié : les questions de comparaison entre deux notions (« différence entre CDI et CDD ? ») diluaient la recherche si traitées comme une décomposition classique ou comme une recherche unique. Un mode comparaison dédié décompose désormais ces questions en deux sous-questions de définition distinctes avant retrieval (voir « Améliorations implémentées » ci-dessous).

### Q5 — Périmètre du conseil juridique

Le système distingue les questions **factuelles**, auxquelles le Code répond directement (le système cite l'article et énonce la règle), des questions **interprétatives**, qui appellent une appréciation au cas par cas (le système expose le cadre légal applicable puis renvoie à un professionnel, sans se prononcer sur la situation individuelle).

L'avertissement juridique est **ajouté par le code à chaque réponse avant affichage**, et non confié au prompt : une consigne de prompt peut être occasionnellement ignorée par le modèle, une concaténation applicative ne l'est jamais. Cette garantie est structurelle.

**Mise à jour :** un agent modérateur (`src/moderation.py`) a été ajouté en amont de tout le pipeline, complétant cette logique de garde-fous structurels : il filtre les tentatives de détournement du prompt (prompt injection) avant même que la question atteigne l'agent de formation de question ou le retrieval, indépendamment de la fiabilité du prompt de génération final.

---

## Sécurité

Un agent de modération (`src/moderation.py`) analyse chaque requête **en amont du pipeline**, avant même l'agent de formation de question, afin de détecter et bloquer les tentatives de détournement (prompt injection) avant tout appel au modèle de génération — évitant aussi de consommer des appels inutiles sur une requête déjà jugée illégitime. Testé sur des cas légitimes (y compris des sujets juridiques sensibles : harcèlement, licenciement) qui passent normalement, et des tentatives d'injection correctement bloquées avec une raison explicite (`src/test_moderation.py`).

Aucune clé d'API n'est stockée dans le code ou l'historique du dépôt ; les secrets sont chargés depuis un fichier `.env` exclu du versionnement.

---

## Améliorations implémentées (Jalon 6)

Six améliorations ont été implémentées, au-delà du minimum requis par le sujet :

**HyDE (Hypothetical Document Embedding).** Avant la recherche vectorielle, un appel LLM génère un extrait fictif d'article qui répondrait à la question ; c'est cet extrait qui est vectorisé pour la recherche, pas la question brute. Ce texte hypothétique n'est jamais montré à l'utilisateur. Gain mesuré sur le jeu de test (`src/test_hyde.py`) : la majorité des questions voient l'article attendu remonter à une meilleure position (ex : rupture conventionnelle, position 6 → 1). Un diagnostic a montré que HyDE seul introduit un risque de non-déterminisme (3 échecs sur 10 essais répétés de la même question) ; corrigé en fusionnant les résultats HyDE et question brute plutôt que de dépendre d'une seule recherche (`fusionner_resultats`), ramenant le taux d'échec à 0/10.

**Décomposition de requête.** Un agent de formation de question (`src/agent_question.py`) nettoie la question (suppression des mots parasites) et la décompose en sous-questions atomiques si elle porte sur plusieurs sujets distincts, avant le retrieval. Chaque sous-question fait sa propre recherche, les résultats sont ensuite fusionnés.

**Mode comparaison.** Intégré au même agent : une question de comparaison entre deux notions (« différence entre CDI et CDD ») est décomposée en deux sous-questions de définition plutôt que traitée comme une seule recherche diluant les deux concepts. Une première implémentation par expression régulière a été écartée après avoir révélé un faux positif sur les formulations d'alternative (« puis-je refuser une mutation ou dois-je démissionner ? », qui n'est pas une comparaison de notions) ; remplacée par une détection intégrée au prompt de l'agent, avec exemples positifs et négatifs explicites.

**Recherche hybride.** Les numéros d'article explicites (« Que dit l'article L3121-27 ? ») ne sont pas traités comme une clé de recherche par la similarité sémantique seule. Une expression régulière détecte un numéro d'article dans la question ; si détecté, un lookup exact par métadonnée ChromaDB est utilisé (`VectorDB.rechercher_par_numero`) au lieu de la recherche vectorielle. Une approche alternative (BM25 + fusion RRF) a été explorée en parallèle avant d'être écartée au profit de cette solution plus simple et sans dépendance supplémentaire.

**Ajout incrémental.** `VectorDB.ajouter_article()` permet d'insérer une nouvelle loi ou de mettre à jour un article existant sans réindexer l'ensemble du corpus (11 486 articles). Un article modifié voit ses anciens chunks supprimés avant réinsertion, pour éviter les chunks orphelins si le nouveau texte se redécoupe en moins de segments que l'ancien.

**Agent modérateur.** Voir section « Sécurité » ci-dessus.

Tous les prompts (génération, formation de question, modération) sont isolés dans des fichiers `.txt` sous `prompts/`, chargés dynamiquement — aucun texte de prompt n'est codé en dur dans les fichiers `.py`.

---

## État d'avancement

| Étape | Statut |
|---|---|
| Préparation et extraction du corpus | ✅ Terminé |
| Découpage (chunking) et indexation | ✅ Terminé |
| Validation du retrieval | ✅ Terminé |
| Génération avec citations | ✅ Terminé |
| Interface en ligne de commande | ✅ Terminé |
| Ajout incrémental à la base vectorielle | ✅ Terminé |
| Fraîcheur du corpus (date DILA + avertissement) | ✅ Terminé |
| Amélioration — HyDE | ✅ Terminé |
| Amélioration — Décomposition de requête | ✅ Terminé |
| Amélioration — Mode comparaison | ✅ Terminé |
| Amélioration — Recherche hybride | ✅ Terminé |
| Amélioration — Agent modérateur | ✅ Terminé |

---

## Méthodologie de développement

Le projet suit un workflow Git structuré : branche `main` (versions stables), branche `dev` (intégration), et branches `feature/*` par fonctionnalité, fusionnées via pull requests. Les secrets et fichiers volumineux (source brute, base vectorielle) sont exclus du versionnement.

---

## Stack technique

Python · sentence-transformers (embeddings) · ChromaDB (base vectorielle) · Groq (inférence LLM + modération) · pandas
