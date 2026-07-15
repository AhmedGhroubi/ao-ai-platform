import os
import json
import re
import time
from groq import Groq
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.expert import Expert
from app.utils.docx_reader import extract_text_from_docx
from unicodedata import normalize

load_dotenv()

client     = Groq(api_key=os.getenv("GROQ_API_KEY"))
TEXT_MODEL = "openai/gpt-oss-120b"

CHUNK_SIZE = 8000


# ──────────────────────────────────────────────────────────────────────────────
# UTILITAIRES
# ──────────────────────────────────────────────────────────────────────────────

def generate_expert_slug(nom: str, date_naissance: str = None) -> str:
    # 1. Sécurité si le nom est vide
    if not nom or "nom et prenom" in nom.lower():
        nom = "expert_inconnu"
        
    # 2. Nettoyage de base (minuscules, suppression des accents et caractères spéciaux)
    nom_clean = normalize('NFKD', nom).encode('ascii', 'ignore').decode('utf-8').lower()
    nom_clean = re.sub(r"[^a-z\s]", "", nom_clean) # Garde uniquement lettres et espaces
    
    # 3. On trie les mots alphabétiquement
    mots = [m.strip() for m in nom_clean.split() if m.strip()]
    mots_tries = sorted(mots) 
    nom_ordonne = "-".join(mots_tries)
    
    # 4. Normalisation de la date de naissance 
    date_str = "sans-date"
    if date_naissance and isinstance(date_naissance, str):
        chiffres_date = "".join(re.findall(r'\d+', date_naissance))
        if chiffres_date and len(chiffres_date) >= 4:
            date_str = chiffres_date

    return f"{nom_ordonne}-{date_str}"


def parse_llm_json(response_text: str) -> dict:
    try:
        start = response_text.find('{')
        end   = response_text.rfind('}')
        if start != -1 and end != -1:
            return json.loads(response_text[start:end+1])
        return json.loads(response_text)
    except json.JSONDecodeError:
        print(f"  [JSON] Erreur parsing : {response_text[:120]}...")
        return {}


def call_llm(prompt: str, max_tokens: int = 2048) -> dict:
    """
    Appel LLM avec mode JSON natif et retry automatique sur rate limit d'une minute (3 tentatives).
    Lève une exception si le quota journalier (Daily Limit) est atteint après ces tentatives.
    """
    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(
                model=TEXT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            return parse_llm_json(response.choices[0].message.content)

        except Exception as e:
            err = str(e).lower()
            # On détecte les Rate Limits à court terme
            if "rate_limit" in err or "429" in err or "413" in err:
                wait = 10 * attempt   # 10s, 20s, 30s
                print(f"  [Rate limit] Tentative {attempt}/3 — attente {wait}s")
                time.sleep(wait)
                if attempt == 3:
                    raise e
            else:
                raise e
    return {}


def split_cv_sections(cv_text: str) -> tuple[str, str]:
    marker = r"(Comp[eé]tences\s*/?\s*qualifications?\s+pour\s+la\s+mission" \
             r"|R[eé]f[eé]rences?\s+de\s+projets?" \
             r"|Missions?\s+r[eé]alis[eé]es?" \
             r"|Projets?\s+et\s+missions?" \
             r"|Qualifications?\s+pour\s+la\s+mission)"

    parts = re.split(marker, cv_text, flags=re.IGNORECASE)

    if len(parts) > 2 and len(parts[0]) >= 500:
        profile_zone  = parts[0]
        projects_zone = parts[1] + "".join(parts[2:])
        print(f"  [Split] Zone profil : {len(profile_zone)} chars | Zone projets : {len(projects_zone)} chars")
    else:
        profile_zone  = cv_text
        projects_zone = cv_text
        print(f"  [Split] ⚠ Marqueur absent ou zone profil suspecte ({len(parts[0]) if parts else 0} chars) — Analyse globale.")

    
    return profile_zone, projects_zone


def chunk_text_by_size(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    if not text:
        return []

    chunks  = []
    lines   = text.split('\n')
    current = []
    length  = 0

    for line in lines:
        if length + len(line) > chunk_size and current:
            chunks.append('\n'.join(current))
            current = [line]
            length  = len(line)
        else:
            current.append(line)
            length += len(line) + 1

    if current:
        chunks.append('\n'.join(current))

    return chunks


# ──────────────────────────────────────────────────────────────────────────────
# CODE AGENTS (Inchangé)
# ──────────────────────────────────────────────────────────────────────────────

def agent_1_civil_academique(profile_text: str) -> dict:
    prompt = f"""
Tu es l'Agent 1 (Extracteur Civil & Académique). Ton rôle est d'analyser l'en-tête du CV pour en extraire l'identité et le parcours académique.

CONSIGNES CRITIQUES POUR LE NOM :
1. Le nom de l'expert se trouve systématiquement au tout début du document (dans les 5 premières lignes).
2. Il peut être en texte brut isolé ou dans un tableau. Tu DOIS le trouver.
3. Ne renvoie JAMAIS null ou une chaîne vide pour "nom_expert" si un nom d'humain est identifiable.

EXTRAIT DU CV :
---
{profile_text}
---

Renvoie UNIQUEMENT un objet JSON respectant STRICTEMENT cette structure :
{{
    "nom_expert": "NOM Prénom (Écrire le nom de famille en MAJUSCULES)",
    "date_naissance": "JJ/MM/AAAA ou null",
    "nationalite": "Nationalité seule (ex: Tunisienne, Française) ou null",
    "langues": ["Français", "Anglais"],
    "etudes": [
        {{"annee": "Année ou null", "diplome": "Intitulé du diplôme", "institution": "Établissement"}}
    ],
    "certifications": ["Nom de la certification"],
    "pays_listes_explicitement": ["Pays mentionnés"]
}}
"""
    return call_llm(prompt)


def agent_2_experiences(profile_text: str) -> dict:
    prompt = f"""
Tu es l'Agent 2 (Analyseur d'Expériences). Ton rôle est de reconstruire la chronologie de la carrière de l'expert.

CONSIGNES :
1. Repère la section du parcours professionnel / historique d'emploi.
2. Attention : bien que ces informations soient présentées dans un tableau dans le document Word d'origine, le texte brut que tu reçois peut avoir perdu ses bordures (pas de barres verticales '|'). Analyse le texte de manière sémantique pour associer chaque période à son employeur, son poste et ses activités.
3. Extrais TOUS les postes occupés (ex: ST2I, CNCT, etc.).
4. Pour chaque poste, extrait le résumé des tâches ou activités réalisées.

RÈGLE CALCUL : annees_experience_total = 2026 - année du premier poste.

EXTRAIT CV :
---
{profile_text}
---

Renvoie UNIQUEMENT un JSON strict avec la clé "poste_occupe" :
{{
    "titre_poste_principal": "Titre du poste affiché tout en haut du CV (ex: Expert Géomaticien)",
    "annees_experience_total": 34,
    "experiences_professionnelles": [
        {{
            "periode": "Période (ex: Depuis 2024 ou 1990-1997)",
            "employeur": "Nom de l'employeur / entreprise",
            "poste_occupe": "Intitulé exact du poste occupé",
            "pays": "Pays de l'expérience",
            "resume_activites": ["Activité ou responsabilité principale 1", "Activité ou responsabilité principale 2"]
        }}
    ]
}}
"""
    return call_llm(prompt, max_tokens=4096)


def agent_3_skills_tagging(cv_chunk: str) -> dict:
    prompt = f"""
Tu es l'Agent 3 (Indexeur de Compétences). Extrais les tags de compétences techniques de ce morceau de CV.
Mots-clés courts uniquement, pas de phrases.

MORCEAU CV :
---
{cv_chunk}
---

Renvoie UNIQUEMENT un JSON strict :
{{
    "competences_techniques": ["Java", "SIG", "Scrum", "PostgreSQL", "Oracle"]
}}
"""
    return call_llm(prompt)


def agent_4_projets_missions(projects_chunk: str) -> dict:
    prompt = f"""
Tu es l'Agent 4 (Spécialiste Projets & Missions). Extrais tous les projets de ce morceau de texte.

MORCEAU SECTION PROJETS :
---
{projects_chunk}
---

Renvoie UNIQUEMENT un JSON strict :
{{
    "pays_d_intervention": ["Pays A", "Pays B"],
    "projets_et_missions": [
        {{
            "nom_projet": "Nom complet du projet",
            "client_ou_bailleur": "PNUD / GIZ / Ministère...",
            "annee": "2023 ou 2019-2020",
            "pays": "Tunisie",
            "poste_occupe": "Développeur Senior"
        }}
    ]
}}
"""
    return call_llm(prompt, max_tokens=4096)


# ──────────────────────────────────────────────────────────────────────────────
# ORCHESTRATEUR PRINCIPAL ROBUSTE AVEC REPRISE ULTÉRIEURE
# ──────────────────────────────────────────────────────────────────────────────

def run_expert_extraction_pipeline(expert_id: int):
    db: Session = SessionLocal()
    try:
        print(f"[CV Pipeline] 🚀 Démarrage de l'analyse pour l'expert ID: {expert_id}")

        expert = db.query(Expert).filter(Expert.id == expert_id).first()
        if not expert:
            return

        # 1. Vérification de l'avancement sauvegardé (Checkpointing)
        if not expert.extracted_data:
            expert.extracted_data = {}
        
        # On lit l'étape où le pipeline s'était arrêté (0 par défaut)
        etape_sauvegardee = expert.extracted_data.get("_etape_analyse", 0)

        # On met le statut à "En cours d'analyse" si c'est un premier démarrage
        if etape_sauvegardee == 0:
            expert.status = "En cours d'analyse"
            db.commit()

        cv_text = extract_text_from_docx(expert.file_path)
        print(f"[CV Pipeline] 📄 Contenu chargé : {len(cv_text)} caractères")

        if not cv_text or not cv_text.strip():
            raise ValueError("Le fichier DOCX a été lu mais aucun texte n'a pu en être extrait.")

        profile_text, projects_text = split_cv_sections(cv_text)

        # 🛑 CHECKPOINT GÉNÉRAL : L'utilisateur a-t-il annulé/supprimé l'expert ?
        db.expire_all()
        if not db.query(Expert).filter(Expert.id == expert_id).first():
            print(f"[CV Pipeline] 🛑 Arrêt : L'expert {expert_id} a été annulé/supprimé par l'utilisateur.")
            return

        # ── Agent 1 ───────────────────────────────────────────────────────────
        if etape_sauvegardee < 1:
            print("[CV Pipeline] 🤖 Agent 1 — Identité & Académique")
            data_1 = agent_1_civil_academique(profile_text)
            
            if not data_1 or not data_1.get("nom_expert") or "Nom et prénom" in data_1.get("nom_expert", ""):
                if not data_1: data_1 = {}
                data_1["nom_expert"] = f"Expert_Inconnu_{expert_id}"
            
            temp_data = expert.extracted_data.copy()
            temp_data.update(data_1)
            temp_data["_etape_analyse"] = 1
            expert.extracted_data = temp_data
            db.commit()
            time.sleep(2)
        else:
            print("[CV Pipeline] ⏭️ Étape 1 déjà réalisée. Skip.")

        # 🛑 CHECKPOINT 2
        if not db.query(Expert).filter(Expert.id == expert_id).first():
            print(f"[CV Pipeline] 🛑 Arrêt : L'expert {expert_id} a été supprimé.")
            return

        # ── Agent 2 ───────────────────────────────────────────────────────────
        if etape_sauvegardee < 2:
            print("[CV Pipeline] 🤖 Agent 2 — Expériences")
            data_2 = agent_2_experiences(profile_text)
            if not data_2:
                raise ValueError("L'Agent 2 n'a pas pu extraire les expériences.")
            
            temp_data = expert.extracted_data.copy()
            temp_data.update(data_2)
            temp_data["_etape_analyse"] = 2
            expert.extracted_data = temp_data
            db.commit()
            time.sleep(2)
        else:
            print("[CV Pipeline] ⏭️ Étape 2 déjà réalisée. Skip.")

        # ── Agent 3 ───────────────────────────────────────────────────────────
        if etape_sauvegardee < 3:
            full_chunks  = chunk_text_by_size(cv_text)
            global_skills = set()
            print(f"[CV Pipeline] 🤖 Agent 3 — Compétences ({len(full_chunks)} chunk(s))")

            for idx, chunk in enumerate(full_chunks):
                if not db.query(Expert).filter(Expert.id == expert_id).first():
                    print(f"[CV Pipeline] 🛑 Arrêt en cours de route (Agent 3) pour l'ID {expert_id}.")
                    return
                    
                print(f"  [Agent 3] Chunk {idx+1}/{len(full_chunks)}")
                result = agent_3_skills_tagging(chunk)
                for skill in (result.get("competences_techniques") or []):
                    if skill: global_skills.add(skill.strip())
                time.sleep(2)

            # Sauvegarde intermédiaire de l'étape 3
            temp_data = expert.extracted_data.copy()
            temp_data["competences_techniques"] = sorted(list(global_skills))
            temp_data["_etape_analyse"] = 3
            expert.extracted_data = temp_data
            db.commit()
        else:
            print("[CV Pipeline] ⏭️ Étape 3 déjà réalisée. Skip.")

        # ── Agent 4 ───────────────────────────────────────────────────────────
        if etape_sauvegardee < 4:
            project_chunks    = chunk_text_by_size(projects_text)
            global_countries  = set()
            all_projects      = []
            noms_existants    = set()

            print(f"[CV Pipeline] 🤖 Agent 4 — Projets ({len(project_chunks)} chunk(s))")

            for idx, chunk in enumerate(project_chunks):
                if not db.query(Expert).filter(Expert.id == expert_id).first():
                    print(f"[CV Pipeline] 🛑 Arrêt en cours de route (Agent 4) pour l'ID {expert_id}.")
                    return

                print(f"  [Agent 4] Chunk {idx+1}/{len(project_chunks)}")
                result = agent_4_projets_missions(chunk)

                for pays in (result.get("pays_d_intervention") or []):
                    if pays: global_countries.add(pays.strip())

                for projet in (result.get("projets_et_missions") or []):
                    nom = projet.get("nom_projet", "").strip().lower()
                    if nom and nom not in noms_existants:
                        noms_existants.add(nom)
                        all_projects.append(projet)
                time.sleep(2)   

            # Sauvegarde intermédiaire de l'étape 4
            temp_data = expert.extracted_data.copy()
            temp_data["pays_d_intervention"] = sorted(list(global_countries))
            temp_data["projets_et_missions"] = all_projects
            temp_data["_etape_analyse"] = 4
            expert.extracted_data = temp_data
            db.commit()
        else:
            print("[CV Pipeline] ⏭️ Étape 4 déjà réalisée.")

        expert = db.query(Expert).filter(Expert.id == expert_id).first()
        if not expert:
            print(f"[CV Pipeline] 🛑 Annulation : L'expert {expert_id} n'existe plus en base.")
            return

        # ── Fusion & Nettoyage des données finalisées ─────────────────────────
        # On consolide les données déjà stockées étape par étape dans `extracted_data`
        extracted_json = expert.extracted_data
        
        # On harmonise les pays (civils + interventions)
        tous_pays = set(extracted_json.get("pays_listes_explicitement") or [])
        tous_pays.update(extracted_json.get("pays_d_intervention") or [])
        extracted_json["pays_d_intervention"] = sorted(list(tous_pays))

        nom_extrait  = extracted_json.get("nom_expert")
        date_naiss   = extracted_json.get("date_naissance")
        target_slug  = generate_expert_slug(nom_extrait, date_naiss)

        # Nettoyage de notre clé technique d'étape de reprise avant l'enregistrement final
        if "_etape_analyse" in extracted_json:
            del extracted_json["_etape_analyse"]

        # Traitement des doublons
        expert_existant = db.query(Expert).filter(
            Expert.slug_unique == target_slug, 
            Expert.id != expert_id
        ).first()

        if expert_existant:
            print(f"[CV Pipeline] 🔄 Doublon détecté pour le slug '{target_slug}' (ID {expert_existant.id}). Fusion...")
            expert_existant.nom_expert     = nom_extrait
            expert_existant.extracted_data = extracted_json
            expert_existant.status         = "Analysé"
            
            db.delete(expert)
            db.commit()
            print(f"[CV Pipeline] ✅ Doublon fusionné sur l'ID {expert_existant.id}.")
            return

        # Sauvegarde classique réussie
        expert.nom_expert     = nom_extrait
        expert.slug_unique    = target_slug
        expert.extracted_data = extracted_json
        expert.status         = "Analysé"
        db.commit()
        print(f"[CV Pipeline] ✅ {nom_extrait} — Analyse terminée avec succès de bout en bout.")

    except Exception as e:
        import traceback
        db.rollback()
        print(traceback.format_exc())
        
        # Sauvegarde du statut d'erreur spécifique au quota ou technique
        expert = db.query(Expert).filter(Expert.id == expert_id).first()
        if expert:
            err_msg = str(e).lower()
            if "quota" in err_msg or "429" in err_msg or "rate" in err_msg or "limit" in err_msg:
                # Statut personnalisé d'interruption pour le Quota Journalier !
                expert.status = "Quota journalier dépassé (En pause)"
            else:
                expert.status = "Erreur"
            db.commit()
        print(f"[CV Pipeline] ❌ Erreur : {e}")
    finally:
        db.close()