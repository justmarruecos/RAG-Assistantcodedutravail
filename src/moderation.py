"""
Agent moderateur : filtre les tentatives de prompt injection ou de
detournement AVANT tout traitement de la question, comme demande
par le sujet (jalon 6) et deja configure dans config.py
(MODERATION_MODEL, jamais utilise jusqu'ici).

Usage : ok, raison = moderer(question)
"""

import os
from dotenv import load_dotenv
from groq import Groq

from src.config import MODERATION_MODEL

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])


def _charger_prompt_moderation():
    chemin = os.path.join(
        os.path.dirname(__file__), "..", "prompts", "moderation_prompt.txt"
    )
    with open(chemin, encoding="utf-8") as f:
        return f.read()


PROMPT_MODERATION = _charger_prompt_moderation()


def moderer(question):
    """Retourne (True, None) si la question est sure, ou
    (False, raison) si elle doit etre bloquee."""
    resp = client.chat.completions.create(
        model=MODERATION_MODEL,
        messages=[
            {"role": "system", "content": PROMPT_MODERATION},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    texte = resp.choices[0].message.content.strip()

    if texte.startswith("SAFE"):
        return True, None
    return False, texte.replace("BLOQUE:", "").strip()