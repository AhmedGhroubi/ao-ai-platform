import os
import json
import base64
import uuid
import time
import shutil
import re
import fitz  # PyMuPDF
from groq import Groq
from dotenv import load_dotenv
from app.models.tender import Tender
from app.database.session import SessionLocal
from app.schemas import tender

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Modèles ───────────────────────────────────────────────────────────────────
TEXT_MODEL   = "llama-3.3-70b-versatile"         
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"  

MAX_IMAGES_PER_CALL = 4  
MAX_TEXT_CHARS      = 50000 


# ──────────────────────────────────────────────────────────────────────────────
# UTILITAIRES PDF
# ──────────────────────────────────────────────────────────────────────────────

def pdf_to_images(
    pdf_path: str,
    start_page: int = None,
    end_page: int = None,
    dpi: int = 100,
) -> tuple[str, list[str]]:
    """Convertit les pages sélectionnées du PDF en PNG."""
    doc       = fitz.open(pdf_path)
    image_paths = []
    output_dir  = os.path.splitext(pdf_path)[0] + "_pages"
    os.makedirs(output_dir, exist_ok=True)
    mat = fitz.Matrix(dpi / 72, dpi / 72)

    start_idx = (start_page - 1) if start_page else 0
    end_idx   = end_page if end_page else len(doc)

    for i in range(start_idx, min(end_idx, len(doc))):
        pix      = doc[i].get_pixmap(matrix=mat, alpha=False)
        img_path = os.path.join(output_dir, f"page_{i + 1:03d}.png")
        pix.save(img_path)
        image_paths.append(img_path)

    doc.close()
    print(f"[PDF] {len(image_paths)} pages converties en PNG à {dpi} DPI")
    return output_dir, image_paths


def pdf_to_text_by_page(
    pdf_path: str,
    start_page: int = None,
    end_page: int = None,
) -> list[dict]:
    """
    Extrait le texte brut de chaque page via PyMuPDF.
    Retourne une liste de dicts : {page_num (1-based), text}.
    Utilisé par l'Agent 1 (texte) à la place des images.
    """
    doc       = fitz.open(pdf_path)
    pages_text = []
    start_idx  = (start_page - 1) if start_page else 0
    end_idx    = end_page if end_page else len(doc)

    for i in range(start_idx, min(end_idx, len(doc))):
        text = doc[i].get_text("text").strip()
        pages_text.append({
            "page_num":  i - start_idx + 1,   # numéro relatif (1-based) dans la plage
            "page_real": i + 1,                # numéro réel dans le PDF
            "text":      text,
        })

    doc.close()
    return pages_text


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _safe_image_subset(image_paths: list[str]) -> list[str]:
    if len(image_paths) > MAX_IMAGES_PER_CALL:
        print(f"  [Safety] {len(image_paths)} images tronquées à {MAX_IMAGES_PER_CALL}")
        return image_paths[:MAX_IMAGES_PER_CALL]
    return image_paths


# ──────────────────────────────────────────────────────────────────────────────
# APPELS API : TEXTE (Agent 1) et VISION (Agents 2 & 3)
# ──────────────────────────────────────────────────────────────────────────────

def call_text_agent(
    system_prompt: str,
    user_prompt: str,
    max_retries: int = 3,
) -> dict:
    """
    Appel LLM texte pur — pas d'image, consommation ~20× moins élevée.
    Utilisé exclusivement par l'Agent 1.
    """
    for attempt in range(1, max_retries + 1):
        try:
            completion = client.chat.completions.create(
                model=TEXT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=2048,
            )
            return json.loads(completion.choices[0].message.content)

        except json.JSONDecodeError as e:
            print(f"  [Text Retry {attempt}/{max_retries}] JSON invalide : {e}")
            if attempt == max_retries:
                raise ValueError(f"JSON invalide après {max_retries} tentatives")
            time.sleep(2)

        except Exception as e:
            err_str = str(e).lower()
            if "rate_limit" in err_str or "429" in err_str:
                wait = 5 * attempt
                print(f"  [Rate limit texte] Attente {wait}s...")
                time.sleep(wait)
                if attempt == max_retries:
                    raise
            else:
                raise


def call_vision_agent(
    system_prompt: str,
    user_prompt: str,
    image_paths: list[str],
    max_retries: int = 3,
) -> dict:
    """Appel Vision avec retry, backoff rate-limit et récupération json_validate_failed."""
    safe_paths   = _safe_image_subset(image_paths)
    content_list = [{"type": "text", "text": f"{system_prompt}\n\n{user_prompt}"}]
    for path in safe_paths:
        content_list.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{encode_image(path)}"},
        })

    for attempt in range(1, max_retries + 1):
        try:
            completion = client.chat.completions.create(
                model=VISION_MODEL,
                messages=[{"role": "user", "content": content_list}],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=4096,
            )
            return json.loads(completion.choices[0].message.content)

        except json.JSONDecodeError as e:
            print(f"  [Vision Retry {attempt}/{max_retries}] JSON invalide : {e}")
            if attempt == max_retries:
                raise ValueError(f"JSON invalide après {max_retries} tentatives")
            time.sleep(3)

        except Exception as e:
            err_str = str(e).lower()
            if "rate_limit" in err_str or "429" in err_str or "too many" in err_str:
                # Vérifier si c'est un épuisement journalier (TPD)
                if "tokens per day" in err_str or "per day" in err_str:
                    raise   # inutile de retry — limite journalière atteinte
                wait = 5 * attempt
                print(f"  [Rate limit vision] Attente {wait}s...")
                time.sleep(wait)
                if attempt == max_retries:
                    raise
            elif "json_validate_failed" in err_str or "failed to generate json" in err_str:
                print(f"  [Vision Retry {attempt}/{max_retries}] json_validate_failed — récupération")
                try:
                    match = re.search(r"'failed_generation':\s*'(.*?)'(?:\s*\}|\s*$)", str(e), re.DOTALL)
                    if match:
                        raw_failed = match.group(1)
                        def _eval_expr(m):
                            try:
                                return str(round(eval(m.group(0)), 6))
                            except Exception:
                                return m.group(0)
                        fixed  = re.sub(r'[\d.]+(?:\s*\+\s*[\d.]+)+', _eval_expr, raw_failed)
                        fixed  = fixed.replace("\\n", "\n")
                        result = json.loads(fixed)
                        print(f"  [Recovery] JSON récupéré ✅")
                        return result
                except Exception as rec_err:
                    print(f"  [Recovery] Échec : {rec_err}")
                if attempt == max_retries:
                    raise ValueError("json_validate_failed non récupérable")
                time.sleep(3)
            else:
                raise


# ──────────────────────────────────────────────────────────────────────────────
# AGENT 1 — Identification des profils (TEXTE PUR — économie de ~200k tokens)
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_AGENT_1 = """
Tu es l'Agent 1 : Extracteur de profils pour un appel d'offres.
Tu reçois le texte brut de chaque page du document.

Ta tâche : identifier TOUS les profils/postes requis et sur quelle(s) page(s) ils apparaissent.

RÈGLES :
- Un profil peut s'étaler sur plusieurs pages consécutives (coupure de tableau).
- Si un profil commence sur une page et son tableau continue sur la suivante → inclure les deux.
- Sois généreux sur les pages : mieux vaut en inclure une de trop qu'en manquer une.
- Ne sauter AUCUN profil, même mentionné brièvement.
- pages = numéros RELATIFS fournis dans le texte (page_num, commençant à 1).

Réponds UNIQUEMENT en JSON valide :
{
  "contexte_mission_globale": "Description brève de l'objectif",
  "liste_profils_detectes": [
    {
      "nom": "Chef de mission",
      "code": "PC-1",
      "quantite": 1,
      "score_max_total": 15,
      "pages": [1, 2]
    }
  ]
}
"""


def run_agent1(pdf_path: str, start_page: int = None, end_page: int = None) -> dict:
    """
    Agent 1 en mode TEXTE PUR.
    Lit le texte brut de chaque page via PyMuPDF → envoie au LLM texte.
    Coût : ~3k tokens au lieu de ~200k tokens en mode Vision.
    """
    pages_text = pdf_to_text_by_page(pdf_path, start_page, end_page)
    total      = len(pages_text)
    print(f"[Agent 1 TEXTE] Analyse de {total} page(s) — modèle : {TEXT_MODEL}")

    # Construction du contexte textuel paginé
    pages_content = ""
    for p in pages_text:
        pages_content += f"\n\n=== PAGE {p['page_num']} (page réelle {p['page_real']}) ===\n"
        pages_content += p["text"]

    # Tronquage si trop long (évite de dépasser le contexte du modèle texte)
    if len(pages_content) > MAX_TEXT_CHARS:
        print(f"  [Agent 1] Texte tronqué à {MAX_TEXT_CHARS} chars (original : {len(pages_content)})")
        pages_content = pages_content[:MAX_TEXT_CHARS] + "\n\n[... texte tronqué ...]"

    result = call_text_agent(
        system_prompt=SYSTEM_AGENT_1,
        user_prompt=f"Identifie TOUS les profils dans ce document :\n{pages_content}",
    )

    # Normalisation du format de sortie
    if "profils_dans_ce_lot" in result and "liste_profils_detectes" not in result:
        result["liste_profils_detectes"] = result.pop("profils_dans_ce_lot")

    nb = len(result.get("liste_profils_detectes", []))
    print(f"[Agent 1 TEXTE] {nb} profil(s) détecté(s) ✅")
    return result


# ──────────────────────────────────────────────────────────────────────────────
# AGENT 2 — Extraction des critères (VISION — tableaux complexes)
# ──────────────────────────────────────────────────────────────────────────────

def _build_system_agent2(nom_profil: str, autres_profils: list[str]) -> str:
    liste_autres = ", ".join(f"'{p}'" for p in autres_profils if p != nom_profil)
    return f"""
Tu es l'Agent 2 : Spécialiste de l'extraction de critères RH.
Tu extrais les critères pour UNIQUEMENT le profil : '{nom_profil}'.

RÈGLES STRICTES :
1. Lis uniquement les lignes/cellules appartenant à '{nom_profil}'.
2. ARRÊT OBLIGATOIRE : Arrête dès que tu vois un autre profil : [{liste_autres}].
3. Extrais les seuils numériques EXACTS (ex: "< 7 ans", ">= 7 ans").
4. Capture TOUS les sous-critères, même ceux à faible barème (0.375 pt, 0.5 pt).
5. Si le tableau continue sur la page suivante → lis toutes les pages fournies.
6. NOTATION CONDITIONNELLE : S'il y a des colonnes ou des sous-lignes indiquant des conditions de niveau ou de durée (ex: "< Bac + 5", ">= Bac + 5", "< 3 ans"), la 'regle_notation' DOIT expliquer la mécanique exacte. Exemple : "1.5 pts si >= Bac + 5, 0 pt si < Bac + 5".
7. NOTATION BINAIRE : Si le critère n'a aucune condition détaillée (ex: posséder une certification ou une langue), la 'regle_notation' DOIT être strictement structurée ainsi : "Acquis = maximum des points, Non acquis = 0 pt". N'écris JAMAIS juste "1 pt" ou "0.75 pt".


Format JSON strict :
{{
  "titre_du_poste": "{nom_profil}",
  "quantite_demandee": 1,
  "score_total_poste": 0,
  "criteres_evaluation": [
    {{
      "type_critere": "qualification | experience | certification | region | langue",
      "libelle_exigence": "Texte exact",
      "regle_notation": "Application stricte de la règle 6 ou 7. Interdit de laisser vide ou d'inventer.",
      "points_maximum": 2.0
    }}
  ],
  "observations": ""
}}
"""


def run_agent2_for_profile(
    profil: dict,
    targeted_images: list[str],
    autres_profils: list[str],
) -> dict:
    nom = profil["nom"]

    if len(targeted_images) <= MAX_IMAGES_PER_CALL:
        print(f"[Agent 2] '{nom}' — {len(targeted_images)} page(s)")
        return call_vision_agent(
            system_prompt=_build_system_agent2(nom, autres_profils),
            user_prompt=f"Extrais TOUS les critères pour '{nom}'.",
            image_paths=targeted_images,
        )

    # Chunking si trop de pages ciblées
    chunks       = [targeted_images[i:i + MAX_IMAGES_PER_CALL] for i in range(0, len(targeted_images), MAX_IMAGES_PER_CALL)]
    all_criteres = []
    base_data    = {}
    print(f"[Agent 2] '{nom}' — {len(targeted_images)} pages → {len(chunks)} lot(s)")

    for i, chunk in enumerate(chunks):
        print(f"[Agent 2] '{nom}' lot {i+1}/{len(chunks)}")
        time.sleep(2.5)
        chunk_result = call_vision_agent(
            system_prompt=_build_system_agent2(nom, autres_profils),
            user_prompt=f"Lot {i+1}/{len(chunks)} — critères de '{nom}' sur ces pages uniquement.",
            image_paths=chunk,
        )
        if i == 0:
            base_data = chunk_result.copy()
        libelles = {c.get("libelle_exigence", "").lower().strip() for c in all_criteres}
        for c in chunk_result.get("criteres_evaluation", []):
            if c.get("libelle_exigence", "").lower().strip() not in libelles:
                all_criteres.append(c)
                libelles.add(c.get("libelle_exigence", "").lower().strip())

    base_data["criteres_evaluation"] = all_criteres
    return base_data


# ──────────────────────────────────────────────────────────────────────────────
# AGENT 2 BIS — Continuation coupure de page
# ──────────────────────────────────────────────────────────────────────────────

def _build_system_agent2_continuation(nom_profil: str, autres_profils: list[str], criteres_deja: list) -> str:
    liste_autres = ", ".join(f"'{p}'" for p in autres_profils if p != nom_profil)
    return f"""
Tu es l'Agent 2 en mode CONTINUATION pour '{nom_profil}'.
Critères déjà extraits (ne PAS répéter) :
{json.dumps(criteres_deja, ensure_ascii=False, indent=2)}

Cherche sur CES NOUVELLES PAGES les critères supplémentaires non encore extraits.
ARRÊT si tu vois un autre profil : [{liste_autres}].
Si aucun critère supplémentaire → retourne liste vide.

Format JSON :
{{
  "criteres_supplementaires": [],
  "continuation_detectee": false
}}
"""


def run_agent2_continuation(profil, continuation_images, autres_profils, criteres_deja):
    nom = profil["nom"]
    safe = continuation_images[:MAX_IMAGES_PER_CALL]
    print(f"[Agent 2 CONTINUATION] '{nom}' — {len(safe)} page(s)")
    return call_vision_agent(
        system_prompt=_build_system_agent2_continuation(nom, autres_profils, criteres_deja),
        user_prompt=f"Critères supplémentaires pour '{nom}' ?",
        image_paths=safe,
    )


# ──────────────────────────────────────────────────────────────────────────────
# AGENT 3 — Auditeur IA (VISION)
# ──────────────────────────────────────────────────────────────────────────────

def _build_system_agent3(nom_profil: str, score_max: float) -> str:
    return f"""
Tu es l'Agent 3 : Auditeur Qualité IA pour '{nom_profil}'.
Compare visuellement les images et le JSON de l'Agent 2.

CHECKLIST :
1. COMPLÉTUDE : Aucune ligne oubliée.
2. EXACTITUDE : Seuils et points exacts.
3. VÉRIFICATION MATHÉMATIQUE : somme des points_maximum = {score_max} pts.
   Écart > 0.5 pt → critère manquant.
4. IMPORTANT : Dans "somme_calculee", écris le résultat NUMÉRIQUE (ex: 3.5),
   JAMAIS une expression arithmétique (ex: "1.0 + 0.5").
5. COUPURE : Si écart persiste → necessite_verification_humaine=true.

Format JSON :
{{
  "titre_du_poste": "{nom_profil}",
  "quantite_demandee": 1,
  "score_total_poste": {score_max},
  "criteres_evaluation": [],
  "verification_mathematique": {{
    "somme_calculee": 0.0,
    "somme_attendue": {score_max},
    "ecart": 0.0,
    "ok": true
  }},
  "validation": {{
    "necessite_verification_humaine": false,
    "motif_doute": ""
  }},
  "corrections_apportees": [],
  "observations": ""
}}
"""


def run_agent3_for_profile(profil_info, agent2_data, targeted_images):
    nom       = profil_info["nom"]
    score_max = profil_info.get("score_max_total", 0)
    safe      = targeted_images[:MAX_IMAGES_PER_CALL]

    if len(targeted_images) > MAX_IMAGES_PER_CALL:
        print(f"[Agent 3] '{nom}' — tronqué à {MAX_IMAGES_PER_CALL} pages")

    print(f"[Agent 3] Audit '{nom}' (score attendu : {score_max} pts)")
    result = call_vision_agent(
        system_prompt=_build_system_agent3(nom, score_max),
        user_prompt=f"Données Agent 2 :\n{json.dumps(agent2_data, ensure_ascii=False, indent=2)}",
        image_paths=safe,
    )
    result["id"] = str(uuid.uuid4())
    return result


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _get_score_ecart(profil_valide: dict) -> float:
    verif = profil_valide.get("verification_mathematique", {})
    return abs(verif.get("ecart", 0)) if not verif.get("ok", True) else 0.0


def _get_continuation_images(pages_idx, all_image_paths, nb=2):
    max_idx = max(pages_idx) if pages_idx else 0
    return [all_image_paths[i] for i in range(max_idx + 1, min(max_idx + 1 + nb, len(all_image_paths)))]


def _merge_criteres(originaux, supplementaires):
    libelles = {c.get("libelle_exigence", "").lower().strip() for c in originaux}
    nouveaux = [c for c in supplementaires if c.get("libelle_exigence", "").lower().strip() not in libelles]
    if nouveaux:
        print(f"  [Merge] {len(nouveaux)} critère(s) ajouté(s)")
    return originaux + nouveaux


# ──────────────────────────────────────────────────────────────────────────────
# ORCHESTRATEUR PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────

def run_tender_multi_agent_pipeline(
    pdf_path: str,
    tender_id: str,
    reference: str,
    start_page: int = None,
    end_page: int = None,
    dpi: int = 100,
    ecart_seuil: float = 0.5,
    nb_pages_continuation: int = 2,
) -> dict:
    """
    Pipeline IA multi-agents optimisé :
    - Agent 1 : LLM texte (llama-3.3-70b) → ~3k tokens au lieu de ~200k
    - Agents 2 & 3 : Vision (llama-4-scout) → tableaux uniquement
    """
    # Étape 0a : images PNG pour Agents 2 & 3
    output_dir, all_image_paths = pdf_to_images(pdf_path, start_page, end_page, dpi=dpi)

    try:
        # ── Étape 1 : Agent 1 TEXTE ───────────────────────────────────────────
        agent1_result    = run_agent1(pdf_path, start_page, end_page)
        profils_detectes = agent1_result.get("liste_profils_detectes", [])
        contexte_global  = agent1_result.get("contexte_mission_globale", "")
        noms_profils     = [p["nom"] for p in profils_detectes]

        print(f"[Pipeline] {len(profils_detectes)} profil(s) à traiter")

        if not profils_detectes:
            return {
                "tender_id": tender_id, "reference": reference,
                "error": "Aucun profil détecté",
                "extracted_data": {"contexte_mission_globale": contexte_global, "profils": []},
            }

        final_profils_list = []

        # ── Étapes 2+3 : Agents 2 & 3 VISION par profil ──────────────────────
        for profil_info in profils_detectes:
            nom = profil_info["nom"]
            print(f"\n[Pipeline] ── {nom} ──")

            pages     = profil_info.get("pages") or list(range(1, len(all_image_paths) + 1))
            pages_idx = set()
            for p in pages:
                for delta in [0, 1]:
                    idx = p - 1 + delta
                    if 0 <= idx < len(all_image_paths):
                        pages_idx.add(idx)

            if not pages_idx:
                print(f"  ⚠ Aucune page assignée → fallback toutes pages")
                pages_idx = set(range(len(all_image_paths)))

            targeted_images = [all_image_paths[i] for i in sorted(pages_idx)]
            print(f"  Pages ciblées (idx 0-based) : {sorted(pages_idx)}")

            try:
                time.sleep(2.0)

                db_session = SessionLocal()
                try:
                    current_tender = db_session.query(Tender).filter(Tender.id == int(tender_id)).first() 
                    # Si le statut est repassé "En attente" (ou "Annulé"), on stoppe le pipeline
                    if not current_tender or current_tender.status == "En attente":
                        print(f"🛑 [Pipeline] Analyse annulée par l'utilisateur pour le profil {nom}.")
                        return {
                            "tender_id": tender_id,
                            "reference": reference,
                            "error": "Analyse interrompue par l'utilisateur",
                            "extracted_data": None
                        }
                finally:
                    db_session.close()

                agent2_data = run_agent2_for_profile(
                    profil=profil_info,
                    targeted_images=targeted_images,
                    autres_profils=noms_profils,
                )

                time.sleep(2.0)

                profil_valide = run_agent3_for_profile(
                    profil_info=profil_info,
                    agent2_data=agent2_data,
                    targeted_images=targeted_images,
                )

                # Fallback coupure de page
                ecart = _get_score_ecart(profil_valide)
                if ecart > ecart_seuil:
                    print(f"  [Fallback] Écart {ecart:.1f} pts → pages suivantes")
                    cont_images = _get_continuation_images(pages_idx, all_image_paths, nb_pages_continuation)
                    if cont_images:
                        time.sleep(2.0)
                        cont_result = run_agent2_continuation(
                            profil=profil_info,
                            continuation_images=cont_images,
                            autres_profils=noms_profils,
                            criteres_deja=profil_valide.get("criteres_evaluation", []),
                        )
                        if cont_result.get("continuation_detectee") and cont_result.get("criteres_supplementaires"):
                            agent2_data["criteres_evaluation"] = _merge_criteres(
                                profil_valide.get("criteres_evaluation", []),
                                cont_result["criteres_supplementaires"],
                            )
                            time.sleep(2.0)
                            profil_valide = run_agent3_for_profile(
                                profil_info=profil_info,
                                agent2_data=agent2_data,
                                targeted_images=(targeted_images + cont_images)[:MAX_IMAGES_PER_CALL],
                            )
                            profil_valide["fallback_applique"] = True

                if profil_valide.get("corrections_apportees"):
                    print(f"  [Agent 3] Corrections : {profil_valide['corrections_apportees']}")

                verif = profil_valide.get("verification_mathematique", {})
                if not verif.get("ok", True):
                    print(f"  [Agent 3] ⚠ Écart résiduel : {verif.get('ecart')} pts")

                final_profils_list.append(profil_valide)

            except Exception as e:
                import traceback
                print(f"  [ERREUR PROFIL] {nom} : {e}")
                print(traceback.format_exc())
                final_profils_list.append({
                    "titre_du_poste": nom,
                    "id":             str(uuid.uuid4()),
                    "error":          str(e),
                    "criteres_evaluation": [],
                    "validation": {
                        "necessite_verification_humaine": True,
                        "motif_doute": f"Erreur pipeline : {e}",
                    },
                })

        fields_for_review = [
            {"profil": p.get("titre_du_poste"), "motif": p.get("validation", {}).get("motif_doute")}
            for p in final_profils_list
            if p.get("validation", {}).get("necessite_verification_humaine")
        ]

        print(f"\n[Pipeline] ✅ {len(final_profils_list)} profil(s), {len(fields_for_review)} à réviser")

        return {
            "tender_id":             tender_id,
            "reference":             reference,
            "requires_human_review": len(fields_for_review) > 0,
            "fields_for_review":     fields_for_review,
            "extracted_data": {
                "contexte_mission_globale": contexte_global,
                "profils":                 final_profils_list,
            },
        }

    finally:
        if output_dir and os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            print(f"[Système] Nettoyage : {output_dir} supprimé")