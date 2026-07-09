"""
Teste le pipeline de generation sur quelques questions : verifie la
presence systematique de l'avertissement juridique, la citation
d'articles, et le refus correct sur une question hors-corpus.

Usage : python -m src.test_generation
"""

from src.vector_db import VectorDB
from src.generation import repondre


def afficher(resultat):
    print(f"Reponse : {resultat['reponse']}")
    print(f"Articles sources : {resultat['articles_sources']}")
    print(f"Hors corpus : {resultat['hors_corpus']}")
    if resultat["avertissement_fraicheur"]:
        print(f"Fraicheur : {resultat['avertissement_fraicheur']}")
    print(f"Avertissement juridique present : {'Oui' if resultat['avertissement_juridique'] else 'Non'}")
    print()


def main():
    db = VectorDB()

    print("=== Question dans le corpus ===")
    r1 = repondre("Comment fonctionne la rupture conventionnelle ?", db)
    afficher(r1)

    print("=== Question clairement hors-sujet (test du refus) ===")
    r2 = repondre("Quelle est la recette de la tarte tatin ?", db)
    afficher(r2)

    # Verifications automatiques
    assert r1["avertissement_juridique"], "L'avertissement juridique doit TOUJOURS etre present"
    assert r2["avertissement_juridique"], "L'avertissement juridique doit TOUJOURS etre present"
    assert r2["hors_corpus"], "La question hors-sujet doit etre detectee comme hors corpus"
    assert len(r1["articles_sources"]) > 0, "Une question du corpus doit citer au moins un article"

    print("=== Toutes les verifications automatiques sont passees ===")


if __name__ == "__main__":
    main()