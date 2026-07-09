"""
Teste detecter_comparaison() : vrais positifs (questions de
comparaison a decomposer) et faux positifs potentiels (questions
normales contenant 'ou'/'et' qui ne doivent pas etre mal decoupees).

Usage : python -m src.test_comparaison
"""

from src.generation import detecter_comparaison

CAS_POSITIFS = [
    "Quelle est la différence entre un CDI et un CDD ?",
    "CDI ou CDD, lequel choisir ?",
]

CAS_NEGATIFS = [
    "Puis-je refuser une mutation ou dois-je démissionner ?",
    "Comment fonctionne le licenciement et quelles sont les indemnités ?",
    "Comment fonctionne la rupture conventionnelle ?",
]


def main():
    print("=== Cas qui DOIVENT etre detectes comme comparaison ===")
    for q in CAS_POSITIFS:
        res = detecter_comparaison(q)
        statut = "OK" if res else "RATE (non detecte)"
        print(f"[{statut}] {q} -> {res}")

    print("\n=== Cas qui NE DOIVENT PAS etre detectes (risque de faux positif) ===")
    for q in CAS_NEGATIFS:
        res = detecter_comparaison(q)
        statut = "OK (non detecte)" if res is None else f"RATE (faux positif : {res})"
        print(f"[{statut}] {q}")


if __name__ == "__main__":
    main()