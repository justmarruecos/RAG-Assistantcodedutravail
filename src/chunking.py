import re
from src.config import CHUNK_MAX_CHARS, CHUNK_OVERLAP


def _phrases(texte):
    """Decoupe un texte en phrases, en protegeant les abreviations
    juridiques (L. R. D. art.) pour ne pas casser les references."""
    protege = re.sub(r'\b([LRD])\.\s', r'\1@ ', texte)
    protege = re.sub(r'\bart\.\s', 'art@ ', protege)
    morceaux = re.split(r'(?<=[.;])\s+', protege)
    return [m.replace('@', '.').strip() for m in morceaux if m.strip()]


def decouper_texte(texte, max_chars=CHUNK_MAX_CHARS, overlap=CHUNK_OVERLAP):
    """Decoupe un texte long SANS couper au milieu d'une phrase.
    - Court (<= max_chars) : renvoye tel quel (1 chunk).
    - Long : accumule des phrases entieres, clot sur une phrase complete.
    - Overlap : la derniere phrase est reprise au debut du segment suivant.
    """
    if len(texte) <= max_chars:
        return [texte]

    phrases = _phrases(texte)
    segments = []
    courant = []
    taille = 0

    for phrase in phrases:
        if taille + len(phrase) > max_chars and courant:
            segments.append(" ".join(courant))
            if overlap > 0:
                courant = [courant[-1]]
                taille = len(courant[-1]) + 1
            else:
                courant = []
                taille = 0
        courant.append(phrase)
        taille += len(phrase) + 1

    if courant:
        segments.append(" ".join(courant))

    return segments


def construire_chunks(articles):
    """Transforme une liste d'articles en chunks.
    Retourne (ids, textes, metadatas) : trois listes paralleles."""
    ids, textes, metadatas = [], [], []

    for art in articles:
        numero = art["numero_article"]
        segments = decouper_texte(art["texte"])

        for i, seg in enumerate(segments):
            chunk_id = f"{numero}__{i}"
            texte_embed = f"Article {numero} : {seg}"

            ids.append(chunk_id)
            textes.append(texte_embed)
            metadatas.append({
                "numero_article": numero,
                "section": art["section"],
                "source": art["source"],
                "segment": i,
                "nb_segments": len(segments),
            })

    return ids, textes, metadatas