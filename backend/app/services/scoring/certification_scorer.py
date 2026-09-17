import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

from .constants import CERTIFICATION_DOMAINES, ORGANISMES_RECONNUS
from .normalizers import normaliser_texte_langue


def analyser_exigence_certification(libelle: str, regle: str) -> Dict[str, Any]:
    texte_combine = f"{libelle} {regle}".lower()
    texte_norm = normaliser_texte_langue(texte_combine)

    domaine_trouve = None
    for dom_key, config in CERTIFICATION_DOMAINES.items():
        mots = [normaliser_texte_langue(m) for m in config["mots_cles"] + config["exactes"] + config["proches"]]
        if any(m in texte_norm for m in mots if m):
            domaine_trouve = dom_key
            break

    certifs_explicites = []
    if domaine_trouve:
        config = CERTIFICATION_DOMAINES[domaine_trouve]
        toutes_certifs = config["exactes"] + config["proches"]
        for cert in toutes_certifs:
            cert_norm = normaliser_texte_langue(cert)
            if cert_norm in texte_norm:
                certifs_explicites.append(cert)

    equivalent_accepte = bool(re.search(r"\b(ou autre|autre|équivalent|equivalent|assimilé|similaire)\b", texte_combine))
    if not certifs_explicites:
        equivalent_accepte = True

    validite_requise = bool(
        re.search(r"\b(en cours de validité|en cours de validite|valide|non expirée?)\b", texte_combine)
    )
    organisme_reconnu_requis = bool(
        re.search(
            r"\b(organisme\s+(?:international\s+)?reconnu|éditeur|editeur|certifié par|internationalement)\b",
            texte_combine,
        )
    )

    mots_souhaite = [
        "souhaitée",
        "souhaitee",
        "souhaité",
        "souhaite",
        "appréciée",
        "appreciee",
        "un plus",
        "optionnel",
        "optionnelle",
    ]
    obligatoire = not any(w in texte_combine for w in mots_souhaite)

    return {
        "domaine": domaine_trouve,
        "certifications_explicitement_demandees": certifs_explicites,
        "equivalent_accepte": equivalent_accepte,
        "validite_requise": validite_requise,
        "organisme_reconnu_requis": organisme_reconnu_requis,
        "obligatoire": obligatoire,
    }

def verifier_validite_certification(cert_obj: Dict[str, Any]) -> Tuple[bool, str]:
    date_exp_raw = cert_obj.get("date_expiration") or cert_obj.get("expiration") or cert_obj.get("date_fin")
    if not date_exp_raw:
        return True, "Validité supposée conforme (pas de date d'expiration spécifiée)."

    date_str = str(date_exp_raw).strip()
    match_annee = re.search(r"(19\d{2}|20\d{2})", date_str)
    if match_annee:
        annee_exp = int(match_annee.group(1))
        annee_actuelle = datetime.now().year
        if annee_exp < annee_actuelle:
            return False, f"Certification expirée en {annee_exp} (Année courante : {annee_actuelle})."

    return True, "Certification en cours de validité."

def verifier_organisme_reconnu(cert_nom: str, organisme_raw: str) -> bool:
    combined = f"{cert_nom} {organisme_raw}".lower()
    return any(org in combined for org in ORGANISMES_RECONNUS)

def extraire_seuil_certifications(texte: str) -> int:
    if not texte:
        return 1

    texte_norm = texte.lower()
    lettres_vers_chiffres = {
        " un ": " 1 ",
        " une ": " 1 ",
        " deux ": " 2 ",
        " trois ": " 3 ",
        " quatre ": " 4 ",
        " cinq ": " 5 ",
    }
    for key, val in lettres_vers_chiffres.items():
        texte_norm = texte_norm.replace(key, val)

    match_ge = re.search(r"(?:>=|>|au moins|minimum|min|sup[ée]rieur\s+à)\s*(\d+)", texte_norm)
    if match_ge:
        return int(match_ge.group(1))

    match_cert = re.search(r"(\d+)\s*(?:certifications?|certifs?)", texte_norm)
    if match_cert:
        return int(match_cert.group(1))

    return 1


def evaluer_certification_algo(
    certifications_expert: List[Any],
    criterion_libelle: str,
    criterion_regle: str,
    poids_max: float,
) -> Tuple[float, str, bool]:
    texte_combine = f"{criterion_libelle} {criterion_regle}"
    seuil_requis = extraire_seuil_certifications(texte_combine)
    exigence = analyser_exigence_certification(criterion_libelle, criterion_regle)

    if not certifications_expert or not isinstance(certifications_expert, list):
        if not exigence["obligatoire"]:
            return 0.0, "Certification souhaitée non renseignée sur le CV (0 pt).", False
        return 0.0, f"Aucune certification renseignée sur le CV (0/{poids_max} pt, seuil requis : {seuil_requis}).", False

    domaine_cible = exigence["domaine"]
    certifs_explicites = exigence["certifications_explicitement_demandees"]
    certifications_retenues = []
    certs_deja_comptees = set()

    for cert_item in certifications_expert:
        if isinstance(cert_item, dict):
            cert_nom = str(cert_item.get("nom") or cert_item.get("intitule") or cert_item.get("titre") or "")
            organisme = str(cert_item.get("organisme") or cert_item.get("editeur") or cert_item.get("emetteur") or "")
            cert_obj = cert_item
        else:
            cert_nom = str(cert_item)
            organisme = ""
            cert_obj = {}

        if not cert_nom.strip():
            continue

        cert_nom_norm = normaliser_texte_langue(cert_nom)
        if cert_nom_norm in certs_deja_comptees:
            continue

        if exigence["validite_requise"]:
            est_valide, _ = verifier_validite_certification(cert_obj)
            if not est_valide:
                continue

        if exigence["organisme_reconnu_requis"] and not verifier_organisme_reconnu(cert_nom, organisme):
            continue

        est_conforme = False
        if certifs_explicites:
            for c_exp in certifs_explicites:
                c_exp_norm = normaliser_texte_langue(c_exp)
                if c_exp_norm in cert_nom_norm or cert_nom_norm in c_exp_norm:
                    est_conforme = True
                    break

        if not est_conforme and domaine_cible:
            config_dom = CERTIFICATION_DOMAINES[domaine_cible]
            toutes_certifs_domaine = config_dom["exactes"]
            if exigence["equivalent_accepte"]:
                toutes_certifs_domaine = toutes_certifs_domaine + config_dom["proches"]

            certifs_norm = [normaliser_texte_langue(x) for x in toutes_certifs_domaine]
            if any(x in cert_nom_norm or cert_nom_norm in x for x in certifs_norm if x):
                est_conforme = True
            else:
                mots_norm = [normaliser_texte_langue(x) for x in config_dom["mots_cles"]]
                if any(x in cert_nom_norm for x in mots_norm if x):
                    est_conforme = True

        if est_conforme:
            certifications_retenues.append(cert_nom)
            certs_deja_comptees.add(cert_nom_norm)

    nb_valides = len(certifications_retenues)
    if nb_valides >= seuil_requis:
        list_certifs = ", ".join([f"'{c}'" for c in certifications_retenues])
        explication = (
            f"Certifications validées ({nb_valides}/{seuil_requis} requise(s)) : [{list_certifs}] "
            f"correspondent au domaine requis [{domaine_cible or 'général'}] -> Note maximale attribuée ({poids_max}/{poids_max} pts)."
        )
        return poids_max, explication, True

    list_certifs = ""
    if certifications_retenues:
        quoted = ", ".join(["'" + c + "'" for c in certifications_retenues])
        list_certifs = f" [{quoted}]"
    if not exigence["obligatoire"]:
        explication = (
            f"Certification souhaitée non satisfaite ({nb_valides}/{seuil_requis} trouvée(s)){list_certifs} "
            f"(0/{poids_max} pt)."
        )
    else:
        explication = (
            f"Critère non satisfait : {nb_valides} certification(s) valide(s) trouvée(s){list_certifs}, "
            f"alors qu'un seuil de {seuil_requis} est requis (0/{poids_max} pt)."
        )
    return 0.0, explication, True


# Backward-compatible aliases for existing imports.
_analyser_exigence_certification = analyser_exigence_certification
_verifier_validite_certification = verifier_validite_certification
_verifier_organisme_reconnu = verifier_organisme_reconnu
_extraire_seuil_certifications = extraire_seuil_certifications
_evaluer_certification_algo = evaluer_certification_algo

