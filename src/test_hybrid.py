"""
Compare le retrieval vectoriel seul a la recherche hybride sur les cas
que le semantique seul echoue (termes juridiques exacts, numeros d'articles).

Usage : python -m src.test_hybrid
"""

from src.vector_db import VectorDB
from src.hybrid_search import HybridSearch

CAS = [
    ("Que dit l'article L3121-27 ?", "L3121-27"),
    ("rupture conventionnelle", "L1237-11"),
    ("preavis de demission", "L1237-1"),
]


def main():
    vecto = VectorDB()
    hybride = HybridSearch()

    for question, attendu in CAS:
        v = vecto.retrieve(question, n=5)
        nums_v = [m["numero_article"] for m in v["metadatas"][0]]

        h = hybride.retrieve(question, n=5)
        nums_h = [m["numero_article"] for m in h["metadatas"][0]]

        print(f"Q: {question}  (attendu: {attendu})")
        print(f"   VECTORIEL : {nums_v}  {'OK' if attendu in nums_v else 'RATE'}")
        print(f"   HYBRIDE   : {nums_h}  {'OK' if attendu in nums_h else 'RATE'}")
        print()


if __name__ == "__main__":
    main()