"""
Agent formateur de question : nettoie et decompose la question de
l'utilisateur AVANT le retrieval, comme specifie dans le schema de
l'intervenant.

Combine en un seul appel LLM :
- suppression des mots parasites (formules de politesse, hesitations)
- decoupage en sous-questions atomiques si la question est composite
- decomposition en sous-questions de definition si la question est
  une comparaison entre deux notions (prefixees "DEF: ")

Usage : questions_nettoyees = former_question(question_brute)
"""

import os
from dotenv import load_dotenv
from groq import Groq

from src.config import LLM_MODEL

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])


def _charger_prompt_formation():
    """Charge le prompt depuis prompts/formation_question_prompt.txt
    (isole du code, comme pour PROMPT_SYSTEME dans generation.py)."""
    chemin = os.path.join(
        os.path.dirname(__file__), "..", "prompts", "formation_question_prompt.txt"
    )
    with open(chemin, encoding="utf-8") as f:
        return f.read()


PROMPT_FORMATION = _charger_prompt_formation()


def former_question(question_brute):
    """Retourne une liste de 1 a N sous-questions nettoyees et
    atomiques. Les sous-questions issues d'une comparaison sont
    prefixees 'DEF: ' pour signaler ce contexte a la generation."""
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