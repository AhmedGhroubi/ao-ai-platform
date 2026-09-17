import json
import os

RULES_DIR = os.path.join("app", "ai", "rules")

RULES_DATA = {
    "certifications.json": {
        "gestion de projet": ["pmp", "prince2", "prince 2", "pmi acp", "ipma", "capm", "project management professional"],
        "agile": ["scrum master", "psm", "psm i", "psm ii", "csm", "safe", "safe agilist", "pmi acp", "kanban", "agile coach", "product owner", "pspo"],
        "cloud": ["aws", "azure", "gcp", "google cloud", "aws certified", "solutions architect", "cloud practitioner", "azure administrator"],
        "kubernetes": ["cka", "ckad", "cks", "kubernetes certified"],
        "linux": ["rhce", "rhca", "rhcsa", "lpic", "lpic 1", "lpic 2", "red hat certified"],
        "securite": ["cissp", "ceh", "cism", "cisa", "iso 27001", "certified ethical hacker", "comptia security", "oscp"],
        "architecture": ["togaf", "itil", "itil v3", "itil v4", "cobit", "aws architecture"]
    },
    "diplomes.json": {
        "informatique": ["genie logiciel", "computer science", "systemes d information", "technologies de l information", "genie informatique", "informatique de gestion", "software engineering"],
        "telecom": ["reseaux", "telecom", "reseaux et telecommunications", "genie telecommunication", "network engineering"],
        "data": ["data science", "statistiques", "intelligence artificielle", "big data", "science des donnees", "mathematiques appliquees"],
        "bac5": ["master", "bac 5", "diplome d ingenieur", "magistere", "dea", "dess", "ingenieur"]
    },
    "competences.json": {
        "backend": ["python", "java", "spring boot", "node js", "nodejs", "c#", "dotnet", "php", "laravel", "django", "fastapi"],
        "frontend": ["react", "reactjs", "angular", "vue js", "vuejs", "typescript", "javascript", "next js"],
        "devops": ["docker", "kubernetes", "terraform", "ansible", "jenkins", "gitlab ci", "github actions", "cicd"],
        "database": ["postgresql", "mysql", "mongodb", "oracle", "sql server", "redis", "elasticsearch"]
    }
}

def init_rules_files():
    """Génère le dossier et les fichiers de règles s'ils n'existent pas encore."""
    os.makedirs(RULES_DIR, exist_ok=True)
    
    for filename, content in RULES_DATA.items():
        filepath = os.path.join(RULES_DIR, filename)
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
            print(f"✅ Fichier créé : {filepath}")
        else:
            print(f"ℹ️ Le fichier existe déjà : {filepath}")

if __name__ == "__main__":
    init_rules_files()