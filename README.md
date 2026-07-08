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
Modération de la requête → vectorisation de la question → recherche des passages pertinents (top-k) → construction du prompt → génération de la réponse avec citations.

Le code sépare ces deux responsabilités : un module d'indexation et un module d'interrogation distincts. La base vectorielle est persistée et rechargée au démarrage, sans réindexation.

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
│   └── corpus_code_travail.csv     # corpus extrait (11 486 articles)
├── src/
│   └── extract_corpus.py           # extraction et nettoyage depuis la source JSON
├── prompts/                        # prompts système (à venir)
├── .env.example                    # variables d'environnement attendues
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
python src/extract_corpus.py
```

---

## Décisions de conception (questions de réflexion)

### Q1 — Granularité du découpage

Le corpus est constitué d'articles courts (≈ 450 caractères en moyenne), denses, déjà délimités et numérotés. La structure juridique fournit un découpage naturel : nous adoptons une stratégie **par structure**, où **un article constitue un chunk**, en conservant sa hiérarchie (Partie > Livre > Titre > Chapitre) en métadonnée.

Ce choix garantit des unités de sens complètes et autonomes, jamais coupées en milieu de phrase, et une correspondance directe entre un chunk et une référence d'article. Les rares articles longs (> 1 500 caractères) sont découpés en sous-segments avec un chevauchement de 10–20 %, chaque segment conservant le numéro d'article d'origine pour préserver la traçabilité. Le regroupement par section entière a été écarté : il produirait des segments trop volumineux, diluant la précision de la recherche. Une approche hybride est donc retenue : article unique par défaut, sous-découpage pour les articles longs.

### Q2 — Traçabilité des sources

Le numéro d'article est conservé **à la fois dans les métadonnées et dans le texte vectorisé**, chacun servant un objectif distinct. La métadonnée constitue la **source de vérité** pour la citation ; le numéro intégré au texte permet à une recherche lexicale de retrouver un article par sa référence exacte.

La garantie contre l'invention de références repose sur un principe : **la liste des articles cités est construite par le code à partir des métadonnées des passages récupérés, et non extraite de la sortie du modèle**. Le modèle de langage n'est jamais la source des références affichées ; il rédige la réponse, le code fournit les citations vérifiées.

### Q3 — Fraîcheur des données

Le droit du travail évolue régulièrement. Le corpus est daté à l'extraction et ne contient que les articles en vigueur à cette date. Chaque réponse rappelle la date de référence du corpus et le risque d'évolution législative postérieure, et oriente l'utilisateur vers une source officielle à jour pour toute vérification.

### Q4 — Réponses conditionnelles

De nombreuses règles dépendent de la taille de l'entreprise, de l'ancienneté du salarié ou de la convention collective applicable. Le système est conçu pour restituer la règle générale **assortie explicitement de ses conditions d'application**, plutôt qu'une réponse unique tranchée, et pour signaler qu'une convention collective peut déroger au cadre légal — le corpus ne couvrant que la loi. Les questions couvrant plusieurs notions font l'objet d'une décomposition en sous-questions afin de récupérer les articles propres à chaque volet.

### Q5 — Périmètre du conseil juridique

Le système distingue les questions **factuelles**, auxquelles le Code répond directement (le système cite l'article et énonce la règle), des questions **interprétatives**, qui appellent une appréciation au cas par cas (le système expose le cadre légal applicable puis renvoie à un professionnel, sans se prononcer sur la situation individuelle).

L'avertissement juridique est **ajouté par le code à chaque réponse avant affichage**, et non confié au prompt : une consigne de prompt peut être occasionnellement ignorée par le modèle, une concaténation applicative ne l'est jamais. Cette garantie est structurelle.

---

## Sécurité

Un agent de modération analyse chaque requête **en amont du pipeline** afin de détecter et bloquer les tentatives de détournement (prompt injection) avant tout appel au modèle de génération. Aucune clé d'API n'est stockée dans le code ou l'historique du dépôt ; les secrets sont chargés depuis un fichier `.env` exclu du versionnement.

---

## État d'avancement

| Étape | Statut |
|---|---|
| Préparation et extraction du corpus | ✅ Terminé |
| Découpage (chunking) et indexation | 🔜 À venir |
| Validation du retrieval | 🔜 À venir |
| Génération avec citations | 🔜 À venir |
| Interface en ligne de commande | 🔜 À venir |
| Améliorations (recherche hybride, décomposition, modération) | 🔜 À venir |

---

## Méthodologie de développement

Le projet suit un workflow Git structuré : branche `main` (versions stables), branche `dev` (intégration), et branches `feature/*` par fonctionnalité, fusionnées via pull requests. Les secrets et fichiers volumineux (source brute, base vectorielle) sont exclus du versionnement.

---

## Stack technique

Python · sentence-transformers (embeddings) · ChromaDB (base vectorielle) · Groq (inférence LLM) · pandas