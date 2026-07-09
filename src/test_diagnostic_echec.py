"""
Diagnostic : pour chaque essai en echec, affiche le CONTEXTE REEL
envoye au LLM (avant que articles_sources soit vide par la logique
de generation.py), pour savoir si le probleme vient du retrieval
(mauvais articles retrouves) ou de la generation (bon contexte mais
LLM refuse quand meme).

Usage : python -m src.test_diagnostic_echec
"""

from src.vector_db import VectorDB
from src.generation import generer_hyde, construire_contexte, extraire_articles_sources
from src.config import TOP_K

QUESTION = "Comment fonctionne la rupture conventionnelle ?"
NB_ESSAIS = 10


def main():
    db = VectorDB()

    for i in range(NB_ESSAIS):
        texte_hyde = generer_hyde(QUESTION)
        resultats = db.retrieve(texte_hyde, n=TOP_K)
        articles = extraire_articles_sources(resultats)

        pertinent = any(a.startswith("L1237-1") for a in articles)
        statut = "CONTEXTE OK" if pertinent else "CONTEXTE MAUVAIS (probleme HyDE/retrieval)"

        print(f"Essai {i+1}/{NB_ESSAIS} : {statut}")
        print(f"  Articles retrouves : {articles}")
        print()


if __name__ == "__main__":
    main()