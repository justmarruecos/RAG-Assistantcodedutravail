"""
Interface en ligne de commande : boucle interactive de questions-
reponses sur le Code du travail francais.

Usage : python -m src.cli
"""

from src.vector_db import VectorDB
from src.generation import repondre

COMMANDES_SORTIE = {"quit", "exit", "q", ":q"}


def afficher_reponse(resultat):
    print()
    print(resultat["reponse"])
    print()

    if resultat["articles_sources"]:
        print(f"Sources : {', '.join(resultat['articles_sources'])}")

    if resultat["avertissement_fraicheur"]:
        print(f"\n{resultat['avertissement_fraicheur']}")

    print(f"\n{resultat['avertissement_juridique']}")
    print("-" * 70)


def main():
    print("=" * 70)
    print("Assistant Code du travail francais")
    print("Posez une question sur le droit du travail (ou 'quit' pour sortir)")
    print("=" * 70)

    print("\nChargement de la base vectorielle...")
    db = VectorDB()
    print(f"Base chargee. Corpus mis a jour le : {db.date_fraicheur()}")
    print("-" * 70)

    while True:
        try:
            question = input("\nVotre question > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAu revoir.")
            break

        if not question:
            continue

        if question.lower() in COMMANDES_SORTIE:
            print("Au revoir.")
            break

        resultat = repondre(question, db)
        afficher_reponse(resultat)


if __name__ == "__main__":
    main()