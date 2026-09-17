import re
from typing import Any, List, Tuple

from rapidfuzz import fuzz

from .constants import DIPLOME_DOMAINES, NIVEAUX_ACADEMIQUES
from .normalizers import normaliser_texte_langue

try:
    from sentence_transformers import SentenceTransformer, util

    SIMILARITY_MODEL = SentenceTransformer(
        "Lajavaness/sentence-camembert-base"
    )
except ImportError:
    SIMILARITY_MODEL = None


def extraire_niveau_numerique(texte: str) -> int:
    if not texte:
        return 0

    texte_norm = texte.lower()

    match_bac = re.search(
        r'bac\s*[\+\-]?\s*(\d+)',
        texte_norm
    )

    if match_bac:
        try:
            return int(match_bac.group(1))
        except ValueError:
            pass

    for pattern, niveau in NIVEAUX_ACADEMIQUES:
        if re.search(pattern, texte_norm):
            return niveau

    return 0


def evaluer_correspondance_domaine(texte_exigence: str, texte_cv: str) -> str:
    req_norm = normaliser_texte_langue(texte_exigence)
    cv_norm = normaliser_texte_langue(texte_cv)
    domaines_trouves = []
    for key_domaine, config in DIPLOME_DOMAINES.items():
        mots_cles = [normaliser_texte_langue(m) for m in config["synonymes"] + [key_domaine.replace("_", " ")]]
        if any(m in req_norm for m in mots_cles if m):
            domaines_trouves.append(key_domaine)

    if domaines_trouves:
        est_proche = False
        for dom_key in domaines_trouves:
            config = DIPLOME_DOMAINES[dom_key]
            syns_norm = [normaliser_texte_langue(s) for s in config["synonymes"]]
            if any(syn in cv_norm for syn in syns_norm if syn):
                return "EXACT"

            proches_norm = [normaliser_texte_langue(p) for p in config["domaines_proches"]]
            if any(proche in cv_norm for proche in proches_norm if proche):
                est_proche = True
        return "PROCHE" if est_proche else "NON_CONFORME"

    if SIMILARITY_MODEL:
        emb_req = SIMILARITY_MODEL.encode(req_norm, convert_to_tensor=True)
        emb_cv = SIMILARITY_MODEL.encode(cv_norm, convert_to_tensor=True)
        sim = float(util.cos_sim(emb_req, emb_cv)[0][0].item())

        if sim >= 0.75:
            return "EXACT"

        if sim >= 0.55:
            return "PROCHE"

        return "NON_CONFORME"
    ratio = fuzz.token_set_ratio(req_norm, cv_norm) / 100.0

    if ratio >= 0.80:
        return "EXACT"

    if ratio >= 0.65:
        return "PROCHE"

    return "NON_CONFORME"


def analyser_regle_diplome(
    regle_text: str,
    texte_exigence_complet: str,
    poids_max_defaut: float,
) -> Tuple[int, float, float]:
    regle_norm = regle_text.lower()
    texte_complet_norm = texte_exigence_complet.lower()

    m_pts_ge = re.search(
        r"(\d+(?:\.\d+)?)\s*pts?\s*(?:si|=)?\s*(?:>=|>|au moins|minimum)?\s*bac\s*[\+\-]?\s*(\d+)",
        regle_norm,
    )
    if m_pts_ge:
        pts_valide = float(m_pts_ge.group(1))
        niveau_req = int(m_pts_ge.group(2))

        m_pts_lt = re.search(r"(\d+(?:\.\d+)?)\s*pts?\s*si\s*<\s*bac", regle_norm)
        pts_invalide = float(m_pts_lt.group(1)) if m_pts_lt else 0.0

        return niveau_req, pts_valide, pts_invalide

    m_acquis = re.search(
        r"(?:acquis\s*[:=]?\s*(\d+(?:\.\d+)?)\s*pts?|(\d+(?:\.\d+)?)\s*pts?\s*(?:si|=)?\s*acquis)",
        regle_norm,
    )
    if m_acquis:
        pts_valide = float(m_acquis.group(1) or m_acquis.group(2))

        m_non_acquis = re.search(r"non\s*acquis\s*[:=]?\s*(\d+(?:\.\d+)?)\s*pts?", regle_norm)
        pts_invalide = float(m_non_acquis.group(1)) if m_non_acquis else 0.0

        niveau_req = extraire_niveau_numerique(texte_complet_norm)
        return niveau_req, pts_valide, pts_invalide

    niveau_req = extraire_niveau_numerique(texte_complet_norm)
    return niveau_req, poids_max_defaut, 0.0


def evaluer_diplome_algo(
    etudes_expert: List[Any],
    criterion_libelle: str,
    criterion_regle: str,
    poids_max: float,
) -> Tuple[float, str, bool]:
    if not etudes_expert or not isinstance(etudes_expert, list):
        return 0.0, "Aucun diplôme renseigné sur le CV (0 pt).", False

    texte_exigence = f"{criterion_libelle} {criterion_regle}".lower()
    niveau_requis, pts_si_valide, pts_si_invalide = analyser_regle_diplome(
        criterion_regle,
        texte_exigence,
        poids_max,
    )

    meilleur_diplome_exact = None
    niveau_max_exact = -1
    meilleur_diplome_proche = None
    niveau_max_proche = -1

    for etude in etudes_expert:
        if isinstance(etude, dict):
            intitule = str(
                etude.get("diplome")
                or etude.get("titre")
                or etude.get("intitule")
                or etude.get("domaine")
                or ""
            )
            ecole = str(etude.get("etablissement") or etude.get("ecole") or "")
            text_etude = f"{intitule} {ecole}".strip()
        else:
            text_etude = str(etude).strip()

        if not text_etude:
            continue

        niveau_expert = extraire_niveau_numerique(text_etude)
        niveau_valide = (niveau_expert >= niveau_requis) if niveau_requis > 0 else True
        statut_domaine = evaluer_correspondance_domaine(texte_exigence, text_etude)

        if statut_domaine == "EXACT":
            if niveau_expert > niveau_max_exact:
                niveau_max_exact = niveau_expert
                meilleur_diplome_exact = text_etude

            if niveau_valide:
                explication = (
                    f"Diplôme validé (Domaine exact) : '{text_etude}' "
                    f"(Niveau Bac+{niveau_expert}"
                    + (f" >= Bac+{niveau_requis} requis" if niveau_requis > 0 else "")
                    + f", Domaine conforme -> {pts_si_valide}/{poids_max} pts)."
                )
                return pts_si_valide, explication, True

        elif statut_domaine == "PROCHE":
            if niveau_expert > niveau_max_proche:
                niveau_max_proche = niveau_expert
                meilleur_diplome_proche = text_etude

    if meilleur_diplome_proche and (niveau_max_proche >= niveau_requis or niveau_requis == 0):
        pts_proche = round(pts_si_valide, 2) if pts_si_valide > 0 else 0.0
        explication = (
            f"Diplôme partiellement conforme (Domaine connexe/proche) : '{meilleur_diplome_proche}' "
            f"(Niveau Bac+{niveau_max_proche}"
            + (f" >= Bac+{niveau_requis} requis" if niveau_requis > 0 else "")
            + f", Domaine connexe -> {pts_proche}/{poids_max} pts)."
        )
        return pts_proche, explication, True

    if meilleur_diplome_exact and niveau_requis > 0:
        explication_echec = (
            f"Niveau insuffisant : diplôme en domaine exact trouvé ('{meilleur_diplome_exact}', Bac+{niveau_max_exact}), "
            f"mais le niveau requis est Bac+{niveau_requis} ({pts_si_invalide}/{poids_max} pt)."
        )
    elif meilleur_diplome_proche and niveau_requis > 0:
        explication_echec = (
            f"Niveau insuffisant : diplôme en domaine connexe trouvé ('{meilleur_diplome_proche}', Bac+{niveau_max_proche}), "
            f"mais le niveau requis est Bac+{niveau_requis} ({pts_si_invalide}/{poids_max} pt)."
        )
    else:
        explication_echec = (
            "Critère non satisfait : aucun diplôme ne valide le domaine d'études exigé "
            f"(exact ou connexe) ou le niveau requis ({pts_si_invalide}/{poids_max} pt)."
        )

    return pts_si_invalide, explication_echec, True


# Backward-compatible aliases for existing imports.
_extraire_niveau_numerique = extraire_niveau_numerique
_evaluer_correspondance_domaine = evaluer_correspondance_domaine
_analyser_regle_diplome = analyser_regle_diplome
_evaluer_diplome_algo = evaluer_diplome_algo