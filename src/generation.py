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

PROMPT_SYSTEME = f"""Tu es un assistant qui repond a des questions sur le droit du travail francais, en te basant EXCLUSIVEMENT sur les extraits d'articles du Code du travail fournis ci-dessous.

REGLES STRICTES :
1. Reponds UNIQUEMENT a partir des extraits fournis. N'utilise aucune connaissance juridique en dehors de ce contexte.
2. Chaque affirmation de ta reponse doit etre rattachee a un numero d'article present dans le contexte (ex: "selon l'article L1234-5...").
3. Si les extraits fournis ne permettent PAS de repondre a la question, reponds EXACTEMENT et UNIQUEMENT par : {SENTINELLE_HORS_CORPUS}
4. Si la reponse depend de conditions non precisees dans la question (taille de l'entreprise, convention collective applicable), signale cette dependance explicitement plutot que de supposer une situation.
5. Ne donne jamais d'avis sur le caractere abusif ou legal d'une situation personnelle precise (ex: "mon licenciement est-il abusif ?") : rappelle ce que dit la loi de maniere generale et invite a consulter un professionnel pour une analyse du cas particulier.
6. Sois concis et precis. Pas de formules d'introduction inutiles."""

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
    if use_hyde:
        texte_hyde = generer_hyde(question)
        resultats_hyde = db.retrieve(texte_hyde, n=top_k)
        resultats_brut = db.retrieve(question, n=top_k)
        resultats = fusionner_resultats(resultats_hyde, resultats_brut, n=top_k)
    else:
        resultats = db.retrieve(question, n=top_k)

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