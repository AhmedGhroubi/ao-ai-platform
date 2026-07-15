import docx
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.text.paragraph import Paragraph
from docx.table import Table

def extract_text_from_docx(file_path: str) -> str:
    """Extrait le texte et les tableaux d'un fichier .docx dans l'ordre d'apparition (Haut en bas)"""
    doc = docx.Document(file_path)
    full_text = []

    for element in doc.element.body:
        
        # 1. Si l'élément est un paragraphe classique
        if isinstance(element, CT_P):
            para = Paragraph(element, doc)
            if para.text.strip():
                full_text.append(para.text.strip())
                
        # 2. Si l'élément est un tableau
        elif isinstance(element, CT_Tbl):
            table = Table(element, doc)
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                
                cleaned_row = []
                for text in row_text:
                    if not cleaned_row or cleaned_row[-1] != text:
                        cleaned_row.append(text)
                        
                if cleaned_row:
                    full_text.append(" | ".join(cleaned_row))

    return "\n".join(full_text)