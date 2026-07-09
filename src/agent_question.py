"""
Agent formateur de question : nettoie et decompose la question de
l'utilisateur AVANT le retrieval, comme specifie dans le schema de
l'intervenant.

Combine en un seul appel LLM :
- suppression des mots parasites (formules de politesse, hesitations)
- decoupage en sous-questions atomiques si la question est composite

Usage : questions_nettoyees = former_question(question_brute)
"""

import os
from dotenv import load_dotenv
from groq import Groq

from src.config import LLM_MODEL

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

PROMPT_FORMATION = """Tu es un agent de pretraitement de questions pour un systeme de recherche juridique.

Etant donne une question utilisateur, effectue deux operations :
1. Supprime les mots parasites (formules de politesse, hesitations, tournures inutiles).
2. Si la question contient PLUSIEURS sujets distincts, decoupe-la en sous-questions atomiques, une par ligne. Si elle ne porte que sur UN seul sujet, renvoie-la telle quelle (nettoyee), sur une seule ligne.

Reponds UNIQUEMENT avec les questions resultantes, une par ligne, sans numerotation ni commentaire."""


def former_question(question_brute):
    """Retourne une liste de 1 a N sous-questions nettoyees et atomiques."""
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": PROMPT_FORMATION},
            {"role": "user", "content": question_brute},
        ],
        temperature=0,
    )
    lignes = resp.choices[0].message.content.strip().split("\n")
    return [l.strip() for l in lignes if l.strip()]