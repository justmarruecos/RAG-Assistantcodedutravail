"""
Module de generation : assemble le contexte recupere, construit le
prompt, appelle le LLM, et assure les garanties non-negociables
(citations, avertissement juridique, refus hors-corpus) au niveau du
CODE plutot que de compter uniquement sur le prompt.
"""

import os
from dotenv import load_dotenv
from groq import Groq

from src.config import LLM_MODEL, TOP_K
from src.agent_question import former_question

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

AVERTISSEMENT_JURIDIQUE = (
    "Cet assistant ne fournit pas de conseil juridique. "
    "Consultez un avocat ou l'inspection du travail pour votre situation personnelle."
)

SENTINELLE_HORS_CORPUS = "JE_NE_TROUVE_PAS"

MESSAGE_HORS_CORPUS = (
    "Je ne trouve pas cette information dans ma base de donnees "
    "(le Code du travail francais). Je ne peux donc pas repondre "
    "avec certitude a cette question."
)

def _charger_prompt_systeme():
    """Charge le prompt systeme depuis prompts/system_prompt.txt
    (isole du code, comme demande : plus facile a relire, versionner
    et faire evoluer sans toucher a la logique Python)."""
    chemin = os.path.join(os.path.dirname(__file__), "..", "prompts", "system_prompt.txt")
    with open(chemin, encoding="utf-8") as f:
        template = f.read()
    return template.format(sentinelle=SENTINELLE_HORS_CORPUS)


PROMPT_SYSTEME = _charger_prompt_systeme()

import re

PATTERN_NUMERO_ARTICLE = re.compile(r"\b([LRD])\.?\s*(\d{1,4}(?:-\d+)*)\b")


def detecter_numero_article(question):
    """Detecte un numero d'article explicite dans la question
    (ex: 'L3121-27', 'L. 3121-27', 'article R4412-149').
    Retourne le numero normalise (ex: 'L3121-27') ou None."""
    match = PATTERN_NUMERO_ARTICLE.search(question)
    if match:
        lettre, chiffres = match.groups()
        return f"{lettre}{chiffres}"
    return None


def generer_hyde(question):
    """Genere un extrait fictif d'article de loi repondant a la question,
    utilise UNIQUEMENT pour ameliorer la recherche vectorielle.
    ATTENTION : ce texte est hallucine par construction (references,
    numeros d'articles potentiellement faux). Il ne sert JAMAIS a
    repondre a l'utilisateur."""
    prompt = (
        f"Redige un court extrait fictif d'article du Code du travail "
        f"francais (3-4 phrases) qui repondrait a cette question : {question}"
    )
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return resp.choices[0].message.content


def construire_contexte(resultats):
    """Transforme les resultats de VectorDB.retrieve() en un contexte
    numerote et lisible pour le prompt, avec metadonnees explicites."""
    documents = resultats["documents"][0]
    metadatas = resultats["metadatas"][0]

    blocs = []
    for i, (doc, meta) in enumerate(zip(documents, metadatas), start=1):
        bloc = (
            f"[Extrait {i}] Article {meta['numero_article']} "
            f"(section : {meta['section']})\n{doc}"
        )
        blocs.append(bloc)

    return "\n\n".join(blocs)


def extraire_articles_sources(resultats):
    """Liste unique et ordonnee des numeros d'articles presents dans
    le contexte fourni au LLM (pour affichage des sources)."""
    vus = []
    for meta in resultats["metadatas"][0]:
        num = meta["numero_article"]
        if num not in vus:
            vus.append(num)
    return vus

def fusionner_resultats(resultats_a, resultats_b, n):
    """Fusionne deux resultats de recherche (ex: HyDE + question brute),
    en gardant les documents uniques classes par leur meilleure distance,
    limite a n resultats. Reduit le risque qu'une seule recherche
    (HyDE parfois instable) fasse totalement rater le bon contexte."""
    vus = {}
    for resultats in (resultats_a, resultats_b):
        docs = resultats["documents"][0]
        metas = resultats["metadatas"][0]
        dists = resultats["distances"][0]
        for doc, meta, dist in zip(docs, metas, dists):
            cle = meta["numero_article"] + "__" + str(meta["segment"])
            if cle not in vus or dist < vus[cle][2]:
                vus[cle] = (doc, meta, dist)

    fusion = sorted(vus.values(), key=lambda x: x[2])[:n]
    return {
        "documents": [[f[0] for f in fusion]],
        "metadatas": [[f[1] for f in fusion]],
        "distances": [[f[2] for f in fusion]],
    }

def repondre(question, db, top_k=TOP_K, use_hyde=True):
    """Pipeline complet : (HyDE) -> recherche -> prompt -> generation ->
    assemblage final avec garanties de code (citations, avertissement,
    refus).

    use_hyde=True : la recherche vectorielle utilise un extrait fictif
    genere par LLM plutot que la question brute, ameliorant le
    retrieval sur les questions au vocabulaire eloigne du texte de loi
    (voir src/test_hyde.py pour la preuve chiffree de ce gain).
    La question ORIGINALE reste utilisee pour le prompt final envoye
    au LLM : seule la recherche est affectee par HyDE, pas la reponse.

    Retourne un dict :
    {
        "reponse": str,
        "articles_sources": list[str],
        "hors_corpus": bool,
        "avertissement_juridique": str,
        "avertissement_fraicheur": str | None,
    }
    """
    sous_questions = former_question(question)

    tous_documents, tous_metadatas, tous_distances = [], [], []
    for sq in sous_questions:
        numero_detecte = detecter_numero_article(sq)

        if numero_detecte:
            resultats_sq = db.rechercher_par_numero(numero_detecte, n=top_k)
        elif use_hyde:
            texte_hyde = generer_hyde(sq)
            resultats_hyde = db.retrieve(texte_hyde, n=top_k)
            resultats_brut = db.retrieve(sq, n=top_k)
            resultats_sq = fusionner_resultats(resultats_hyde, resultats_brut, n=top_k)
        else:
            resultats_sq = db.retrieve(sq, n=top_k)

        tous_documents.extend(resultats_sq["documents"][0])
        tous_metadatas.extend(resultats_sq["metadatas"][0])
        tous_distances.extend(resultats_sq["distances"][0])

    resultats = fusionner_resultats(
        {"documents": [tous_documents], "metadatas": [tous_metadatas], "distances": [tous_distances]},
        {"documents": [[]], "metadatas": [[]], "distances": [[]]},
        n=top_k,
    )

    contexte = construire_contexte(resultats)
    articles_sources = extraire_articles_sources(resultats)

    messages = [
        {"role": "system", "content": PROMPT_SYSTEME},
        {
            "role": "user",
            "content": f"CONTEXTE :\n{contexte}\n\nQUESTION : {question}",
        },
    ]

    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=0.1,
    )
    texte_brut = resp.choices[0].message.content.strip()

    hors_corpus = SENTINELLE_HORS_CORPUS in texte_brut

    if hors_corpus:
        reponse_finale = MESSAGE_HORS_CORPUS
        articles_sources = []  # aucune source pertinente si hors corpus
    else:
        reponse_finale = texte_brut

    return {
        "reponse": reponse_finale,
        "articles_sources": articles_sources,
        "hors_corpus": hors_corpus,
        "avertissement_juridique": AVERTISSEMENT_JURIDIQUE,
        "avertissement_fraicheur": db.avertissement_fraicheur(),
    }