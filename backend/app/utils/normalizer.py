# app/ai/utils/normalizer.py

import re
import unicodedata

def normalize_text(text: str) -> str:
    if not text:
        return ""
    
    # 1. Minuscules
    text = text.lower()
    
    # 2. Suppression des accents (NFKD)
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    
    # 3. Traitement des acronymes avec points (ex: p.m.p. -> pmp)
    text = re.sub(r'(?<=\b\w)\.(?=\w\b)', '', text)
    
    # 4. Suppression des caractères spéciaux (®, ™, @, etc.) et de la ponctuation
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    
    # 5. Normalisation des espaces multiples
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text