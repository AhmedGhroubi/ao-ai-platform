import pdfplumber
import pandas as pd

def extract_text_and_tables_from_pdf(pdf_path: str,start_page: int = None, end_page: int = None) -> str:
    """
    Lit un PDF, extrait le texte libre et convertit les tableaux en Markdown.
    Idéal pour préparer le terrain avant d'envoyer le contenu à un LLM.
    """
    full_content = []
    
    # On ouvre le PDF avec pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_number = i + 1
            if start_page and page_number < start_page:
                continue
            if end_page and page_number > end_page:
                break

            full_content.append(f"\n\n--- DÉBUT DE LA PAGE {page_number} ---\n")
            
            # 1. Extraction des tableaux de la page
            tables = page.extract_tables()
            
            # 2. Extraction du texte brut de la page
            # On demande à pdfplumber d'ignorer la zone des tableaux pour ne pas avoir de texte en double
            text = page.extract_text(layout=True)
            if text:
                full_content.append(text)
            
            # 3. Formatage des tableaux trouvés en Markdown
            if tables:
                full_content.append("\n\n[TABLEAUX DÉTECTÉS SUR CETTE PAGE] :\n")
                for table in tables:
                    # Nettoyage : remplacer les sauts de ligne dans les cellules par des espaces
                    cleaned_table = []
                    for row in table:
                        cleaned_row = [str(cell).replace('\n', ' ') if cell is not None else "" for cell in row]
                        cleaned_table.append(cleaned_row)
                    
                    # Utilisation de Pandas pour générer un beau format Markdown
                    try:
                        df = pd.DataFrame(cleaned_table[1:], columns=cleaned_table[0])
                        markdown_table = df.to_markdown(index=False)
                        full_content.append(markdown_table)
                        full_content.append("\n")
                    except Exception as e:
                        # Si le tableau est mal formé, on le passe en texte brut
                        full_content.append(str(cleaned_table))
                        
            full_content.append(f"\n--- FIN DE LA PAGE {page_number} ---")
            
    # On assemble tout en un seul grand texte
    return "\n".join(full_content)