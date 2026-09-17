
import json
import os
import hashlib
from typing import Dict, Any, List, Optional
from rapidfuzz import fuzz
from sqlalchemy.orm import Session
from anthropic import Anthropic

from app.utils.normalizer import normalize_text
from app.models.semantic_cache import SemanticCache


class MatchingEngine:
    def __init__(self, rules_dir: Optional[str] = None):
        # 1. Initialisation des répertoires et des règles métier
        self.rules_dir = rules_dir or os.path.join(
            os.path.dirname(__file__), "..", "rules"
        )
        self.rules = self._load_rules()

        # 2. Initialisation du client Anthropic (Claude)
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            self.client = Anthropic(api_key=api_key)
        else:
            self.client = None

        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")

    def _load_rules(self) -> Dict[str, Dict]:
        """Charge les fichiers JSON du dossier rules de manière sécurisée."""
        rules = {}
        if os.path.exists(self.rules_dir):
            for filename in os.listdir(self.rules_dir):
                if filename.endswith(".json"):
                    path = os.path.join(self.rules_dir, filename)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            cat = filename.replace(".json", "")
                            rules[cat] = json.load(f)
                    except Exception as e:
                        print(f"⚠️ Erreur chargement {filename}: {e}")
        return rules

    def evaluate(
        self,
        critere: str,
        valeurs_cv: List[str],
        type_critere: str = "general",
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Évalue un critère et garantit TOUJOURS le retour des clés :
        {"match": bool, "score": float, "confidence": float, "valeur_retenue": str|None, "explication": str, "source": str}
        """
        critere_str = str(critere or "").strip()
        valeurs_list = [str(v) for v in (valeurs_cv or []) if v]

        # ── 0. AUCUNE DONNÉE DANS LE CV ──
        if not valeurs_list:
            return {
                "match": False,
                "score": 0.0,
                "confidence": 1.0,
                "valeur_retenue": None,
                "explication": "Aucune donnée présente dans le CV pour ce critère.",
                "source": "NO_DATA",
            }

        critere_norm = normalize_text(critere_str)
        valeurs_norm = [normalize_text(v) for v in valeurs_list]

        # ── 1. RÈGLES MÉTIER (JSON) ──
        rule_res = self._check_rules(
            critere_norm, valeurs_list, valeurs_norm, type_critere
        )
        if rule_res:
            return rule_res

        # ── 2. RAPIDFUZZ (Calcul du meilleur score textuel) ──
        best_score = 0.0
        best_idx = 0
        for idx, v_norm in enumerate(valeurs_norm):
            score = float(fuzz.token_set_ratio(critere_norm, v_norm))
            if score > best_score:
                best_score = score
                best_idx = idx

        # Score textuel très fort (>= 80%)
        if best_score >= 80.0:
            return {
                "match": True,
                "score": best_score,
                "confidence": round(best_score / 100.0, 2),
                "valeur_retenue": valeurs_list[best_idx],
                "explication": f"Forte correspondance textuelle ({int(best_score)}%).",
                "source": "RAPIDFUZZ",
            }

        # Score textuel très faible (< 30%)
        if best_score < 30.0:
            return {
                "match": False,
                "score": best_score,
                "confidence": 0.95,
                "valeur_retenue": None,
                "explication": f"Faible correspondance textuelle ({int(best_score)}%).",
                "source": "RAPIDFUZZ",
            }

        # ── 3. CACHE BDD ──
        cache_hash = hashlib.md5(
            f"{type_critere}|{critere_norm}|{sorted(valeurs_norm)}".encode()
        ).hexdigest()
        if db is not None:
            try:
                cached = (
                    db.query(SemanticCache)
                    .filter_by(cache_hash=cache_hash)
                    .first()
                )
                if cached:
                    return {
                        "match": cached.match_result,
                        "score": 100.0 if cached.match_result else 0.0,
                        "confidence": cached.confidence,
                        "valeur_retenue": cached.valeur_cv,
                        "explication": cached.explication,
                        "source": "DB_CACHE",
                    }
            except Exception as db_err:
                print(f"⚠️ Erreur lecture cache BDD: {db_err}")

        # ── 4. EVALUATION PAR LLM (CLAUDE) ──
        if self.client:
            try:
                llm_res = self._call_batch_llm(critere_str, valeurs_list)
                llm_match = bool(llm_res.get("match", False))
                llm_score = float(
                    llm_res.get("score", 100.0 if llm_match else 0.0)
                )

                res_dict = {
                    "match": llm_match,
                    "score": llm_score,
                    "confidence": float(llm_res.get("confidence", 0.85)),
                    "valeur_retenue": llm_res.get("valeur_retenue"),
                    "explication": llm_res.get(
                        "explication", "Évaluation par Claude accomplie."
                    ),
                    "source": "LLM",
                }

                # Sauvegarde en cache BDD
                if db is not None:
                    try:
                        cache_entry = SemanticCache(
                            cache_hash=cache_hash,
                            critere=critere_norm,
                            valeur_cv=res_dict["valeur_retenue"],
                            match_result=llm_match,
                            confidence=res_dict["confidence"],
                            explication=res_dict["explication"],
                            source="LLM",
                        )
                        db.add(cache_entry)
                        db.commit()
                    except Exception:
                        db.rollback()

                return res_dict

            except Exception as llm_err:
                print(
                    f"⚠️ Erreur LLM Claude ({llm_err}). Bascule automatique sur le Fallback RapidFuzz."
                )

        # ── 5. FALLBACK SÉCURISÉ (Si le LLM n'est pas disponible ou échoue) ──
        is_match = best_score >= 50.0
        return {
            "match": is_match,
            "score": best_score if is_match else 0.0,
            "confidence": round(best_score / 100.0, 2),
            "valeur_retenue": valeurs_list[best_idx] if is_match else None,
            "explication": f"Estimation basée sur la similarité textuelle ({int(best_score)}%).",
            "source": "RAPIDFUZZ_FALLBACK",
        }

    def _check_rules(
        self,
        critere_norm: str,
        valeurs_orig: List[str],
        valeurs_norm: List[str],
        type_critere: str,
    ) -> Optional[Dict[str, Any]]:
        """Vérification dans les règles JSON."""
        cat_key = type_critere.lower().strip()
        rules_cat = self.rules.get(f"{cat_key}s", {}) or self.rules.get(
            cat_key, {}
        )

        for concept, synonymes in rules_cat.items():
            concept_norm = normalize_text(concept)
            if concept_norm in critere_norm:
                for idx, v_norm in enumerate(valeurs_norm):
                    if any(normalize_text(syn) in v_norm for syn in synonymes):
                        return {
                            "match": True,
                            "score": 100.0,
                            "confidence": 1.0,
                            "valeur_retenue": valeurs_orig[idx],
                            "explication": f"Équivalence métier directe pour '{concept}'.",
                            "source": "RULE_ENGINE",
                        }
        return None

    def _call_batch_llm(
        self, critere: str, valeurs_cv: List[str]
    ) -> Dict[str, Any]:
        """Appel LLM sécurisé via l'API Anthropic (Claude)."""
        prompt = f"""Tu es un expert RH et auditeur spécialisé dans le dépouillement des appels d'offres.

CRITÈRE D'ÉVALUATION DE L'APPEL D'OFFRES :
"{critere}"

DONNÉES DU CV DE L'EXPERT :
{json.dumps(valeurs_cv, ensure_ascii=False)}

ÉVALUE la conformité du CV par rapport au critère requis. 
Attribue un score de 0 à 100 selon le degré d'adéquation (ex: 100 = totalement satisfait, 50-80 = partiellement satisfait, 0 = non satisfait).

Réponds EXCLUSIVEMENT sous la forme d'un objet JSON valide sans aucun texte avant ou après :
{{
  "match": true,
  "score": 100.0,
  "valeur_retenue": "extrait du CV qui prouve le critère (ou null)",
  "confidence": 0.9,
  "explication": "courte justification claire et précise"
}}"""

        # Appel au SDK Anthropic (max_tokens augmenté à 1000 pour éviter toute coupure)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extraction sécurisée du texte (filtre les blocs ThinkingBlock)
        content = "".join(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ).strip()

        # Nettoyage des balises Markdown (ex: ```json ... ```)
        if content.startswith("```"):
            lines = content.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            content = "\n".join(lines).strip()

        data = json.loads(content)

        return {
            "match": bool(data.get("match", False)),
            "score": float(
                data.get("score", 100.0 if data.get("match") else 0.0)
            ),
            "valeur_retenue": data.get("valeur_retenue"),
            "confidence": float(data.get("confidence", 0.85)),
            "explication": str(
                data.get("explication", "Évaluation RH accomplie.")
            ),
        }