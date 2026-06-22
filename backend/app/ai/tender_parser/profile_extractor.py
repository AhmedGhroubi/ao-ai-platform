import os
import json
import base64
from groq import Groq
from dotenv import load_dotenv

# Charge les variables du fichier .env
load_dotenv()

# Initialise le client Groq avec ta clé gratuite
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def encode_image(image_path):
    """Encode l'image générée par PyMuPDF en Base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_profiles_from_images(image_paths, tender_id, reference):
    
    system_prompt = """
    Tu es un expert en analyse visuelle d'appels d'offres. Ton objectif est d'extraire les profils demandés sous forme de JSON en lisant les grilles d'évaluation en image.

    ATTENTION - RÈGLES STRICTES DE LECTURE DES TABLEAUX :
    1. LIGNES GROUPÉES ET LANGUES (TRÈS IMPORTANT) : Si une catégorie principale (ex: "Expérience dans la Région" valant 1.5 pt) contient plusieurs sous-lignes (ex: une ligne "sous-région" à 0.75 pt ET une ligne "langues" à 0.75 pt), tu DOIS créer un objet distinct pour CHAQUE ligne. N'oublie JAMAIS la ligne des langues, qui est souvent tout en bas du tableau !
    2. SUIVI DES LETTRES (a, b, c...) ET EXHAUSTIVITÉ : Ne saute AUCUNE ligne. Si tu extrais un point "a)" et un "b)", tu DOIS impérativement chercher et extraire le "c)" (comme les certifications). Lis le tableau ligne par ligne, jusqu'en bas.
    3. INTERDICTION DES CHAMPS VIDES : Les champs 'libelle_exigence' et 'regle_notation' ne doivent JAMAIS être vides (""). 
    4. LIBELLÉ EXACT : Pour le 'libelle_exigence', recopie le texte descriptif de la ligne, même s'il n'y a pas de chiffres (ex: "Avoir conduit au moins une mission dans la sous-région", ou "Justifie des certifications en gestion des projets...").
    5. NOTATION DIRECTE (SANS OPÉRATEUR MATHÉMATIQUE) : Si une ligne n'a pas de condition avec "<" ou ">=" mais donne juste un score fixe (ex: "0.75"), ta 'regle_notation' doit simplement être : "0.75 point si le critère est rempli, 0 sinon".
    6. NOTATION CONDITIONNELLE : S'il y a des colonnes avec des seuils (ex: "< 7 ans", ">= 7 ans"), la 'regle_notation' doit expliquer la mécanique. Ex: "2 points si >= 7 ans, 0 point si < 7 ans".
    7. SYNTAXE JSON STRICTE : N'utilise JAMAIS de guillemets doubles (") à l'intérieur de tes phrases de texte. Utilise des guillemets simples (').

    Format attendu (Génère UNIQUEMENT un objet JSON valide, sans texte avant ou après) :
    {
      "contexte_mission_globale": "Objectif global",
      "profils": [
        {
          "titre_du_poste": "Nom exact",
          "quantite_demandee": 1,
          "criteres_evaluation": [
            {
              "type_critere": "certifications",
              "libelle_exigence": "Justifie des certifications en gestion des projets en cours de validité (Agile, Prince 2...)",
              "points_maximum": 1.0,
              "regle_notation": "1 point si >= 2, 0 point si < 2."
            },
            {
              "type_critere": "experience_region",
              "libelle_exigence": "Avoir conduit au moins une mission dans la sous-région",
              "points_maximum": 0.75,
              "regle_notation": "0.75 point si le critère est rempli, 0 sinon."
            }
          ],
          "observations": ""
        }
      ]
    }
    """
    # Construction du message pour l'API Vision de Groq
    content_list = [{"type": "text", "text": system_prompt}]
    
    for path in image_paths:
        base64_img = encode_image(path)
        content_list.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
        })

    try:
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct", 
            messages=[
                {
                    "role": "user",
                    "content": content_list
                }
            ],
            temperature=0,
            max_tokens=4096
        )
        
        # Récupération et nettoyage de la réponse (au cas où Llama ajoute des backticks Markdown)
        raw_response = completion.choices[0].message.content.strip()
        if raw_response.startswith("```json"):
            raw_response = raw_response[7:-3].strip()
        elif raw_response.startswith("```"):
            raw_response = raw_response[3:-3].strip()
            
        extracted_json = json.loads(raw_response)
        
        return {
            "tender_id": tender_id,
            "reference": reference,
            "extracted_data": extracted_json
        }
    except Exception as e:
        print(f"Erreur Vision Groq : {str(e)}")
        return None