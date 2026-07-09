"""
Mesure le taux d'echec (faux refus hors-corpus) sur une question du
corpus, repetee plusieurs fois, pour quantifier le non-determinisme
residuel de HyDE + generation a temperature basse.

Usage : python -m src.test_stabilite_generation
"""

from src.vector_db import VectorDB
from src.generation import repondre

QUESTION = "Comment fonctionne la rupture conventionnelle ?"
NB_ESSAIS = 10


def main():
    db = VectorDB()
    echecs = 0

    for i in range(NB_ESSAIS):
        resultat = repondre(QUESTION, db)
        statut = "ECHEC (faux refus)" if resultat["hors_corpus"] else "OK"
        if resultat["hors_corpus"]:
            echecs += 1
        print(f"Essai {i+1}/{NB_ESSAIS} : {statut} - sources : {resultat['articles_sources']}")

    print(f"\n=== Taux d'echec : {echecs}/{NB_ESSAIS} ===")


if __name__ == "__main__":
    main()