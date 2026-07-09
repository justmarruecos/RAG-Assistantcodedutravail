"""
Recherche hybride : combine la recherche vectorielle (semantique) de
VectorDB avec une recherche lexicale BM25 (mots exacts), fusionnees par
Reciprocal Rank Fusion (RRF).

Motivation : la recherche semantique seule echoue sur les termes
juridiques exacts et les numeros d'articles (ex : "Que dit l'article
L3121-27 ?", "rupture conventionnelle"). BM25 retrouve ces
correspondances exactes que le vectoriel manque.

HybridSearch expose la MEME interface que VectorDB (retrieve renvoyant
documents/metadatas/distances, plus avertissement_fraicheur), donc il
est utilisable tel quel dans generation.repondre() sans rien modifier.
"""

import re
import unicodedata
from rank_bm25 import BM25Okapi
from src.vector_db import VectorDB
from src.config import TOP_K


def tokeniser(texte):
    """Decoupe en mots minuscules SANS accents, sans ponctuation.
    Retirer les accents permet a 'demission' de matcher 'demission',
    et normalise les references d'articles (l3121-27)."""
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return re.findall(r"\w+", texte.lower())


class HybridSearch:
    """Recherche hybride vectoriel + BM25. Reutilise VectorDB par
    composition (delegue le vectoriel et la fraicheur)."""

    def __init__(self, poids_lexical=1.5):
        self.vector_db = VectorDB()
        self.poids_lexical = poids_lexical

        # Recharge tous les chunks depuis ChromaDB pour l'index lexical
        data = self.vector_db.collection.get(include=["documents", "metadatas"])
        self.ids = data["ids"]
        self.documents = data["documents"]
        self.metadatas = data["metadatas"]
        self._index_par_id = {doc_id: i for i, doc_id in enumerate(self.ids)}

        # Construction de l'index BM25
        corpus_tokenise = [tokeniser(doc) for doc in self.documents]
        self.bm25 = BM25Okapi(corpus_tokenise)

    def _ids_vectoriel(self, question, n):
        res = self.vector_db.retrieve(question, n=n)
        return res["ids"][0]

    def _ids_lexical(self, question, n):
        scores = self.bm25.get_scores(tokeniser(question))
        meilleurs = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n]
        return [self.ids[i] for i in meilleurs]

    def _fusion_rrf(self, ids_vecto, ids_lexical, k=60):
        """Reciprocal Rank Fusion ponderee. Le lexical a un poids plus
        fort car fiable sur les termes juridiques exacts."""
        scores = {}
        for rang, doc_id in enumerate(ids_vecto):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rang)
        for rang, doc_id in enumerate(ids_lexical):
            scores[doc_id] = scores.get(doc_id, 0) + self.poids_lexical / (k + rang)
        return sorted(scores.keys(), key=lambda d: scores[d], reverse=True)

    def retrieve(self, question, n=TOP_K, n_candidats=20):
        """Recherche hybride. Renvoie le MEME format que VectorDB.retrieve
        (documents/metadatas/distances imbriques dans une liste), pour
        rester compatible avec generation.repondre() et sa fusion HyDE."""
        ids_v = self._ids_vectoriel(question, n_candidats)
        ids_l = self._ids_lexical(question, n_candidats)
        fusion = self._fusion_rrf(ids_v, ids_l)[:n]

        docs, metas, dists = [], [], []
        for rang, doc_id in enumerate(fusion):
            i = self._index_par_id[doc_id]
            docs.append(self.documents[i])
            metas.append(self.metadatas[i])
            # RRF ne produit pas de distance : on met le rang comme
            # pseudo-distance croissante (compatible avec le tri par distance
            # de fusionner_resultats dans generation.py).
            dists.append(float(rang))

        return {
            "ids": [fusion],
            "documents": [docs],
            "metadatas": [metas],
            "distances": [dists],
        }

    # --- Delegation a VectorDB pour rester compatible avec generation.py ---

    def avertissement_fraicheur(self, seuil_jours=90):
        return self.vector_db.avertissement_fraicheur(seuil_jours)

    def date_fraicheur(self):
        return self.vector_db.date_fraicheur()