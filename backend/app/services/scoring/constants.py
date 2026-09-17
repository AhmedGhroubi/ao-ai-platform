# app/services/scoring/constants.py

ROLES_DICTIONNAIRE = {
    "developpeur": [
        "développeur", "developpeur", "programmeur", "software engineer",
        "software developer", "ingénieur développeur", "ingenieur developpeur",
        "ingénieur d'études et de développement",
        "ingenieur d'etudes et de developpement",
        "ingénieur développement", "ingenieur developpement",
        "expert en développement",
        "expert en développement informatique",
        "expert developpement informatique",
        "développeur web"
    ],

    "expert_technique": [
        "tech lead", "techlead", "lead tech",
        "chef d'équipe développement",
        "responsable technique", "lead developpeur",
        "expert technique"
    ],

    "chef_projet": [
        "chef de projet", "project manager",
        "directeur de projet", "directeur de mission",
        "coordinateur de projet", "pmo",
        "scrum master", "chef de mission",
        "chef de mission adjoint"
    ],

    "analyste": [
        "analyste fonctionnel",
        "business analyst",
        "amoa",
        "consultant fonctionnel",
        "analyste"
    ],

    "qualite": [
        "testeur", "developpeur recette", "recetteur",
        "qa", "quality assurance",
        "ingénieur test", "ingenieur test",
        "ingénieur qa", "ingenieur qa",
        "ingénieur qualité", "ingenieur qualite",
        "responsable qualité", "responsable qualite",
        "consultant qa", "expert test",
        "qualité", "qualite",
        "testeur logiciel",
        "qa engineer", "test engineer",
        "consultant qualite", "consultant qualité"
    ],

    "sysadmin": [
        "administrateur système",
        "administrateur systeme",
        "ingénieur système",
        "sysadmin",
        "expert administration système et réseaux",
        "ingénieur réseaux",
        "administrateur système et réseaux",
        "expert systèmes et réseaux",
        "expert systemes et reseaux"
    ],

    "dba": [
        "dba",
        "expert en bases de données",
        "expert base de données",
        "expert bases de données",
        "expert database",
        "administrateur base de données",
        "administrateur bases de données",
        "database administrator",
        "database expert"
    ]
}


MATRICE_COMPATIBILITE_ROLES = {
    "developpeur": {
        "developpeur": 1.0,
        "expert_technique": 0.85,
        "qualite": 0.40,
        "chef_projet": 0.30,
        "dba": 0.20,
        "sysadmin": 0.0
    },
    "expert_technique": {
        "expert_technique": 1.0,
        "developpeur": 0.80,
        "qualite": 0.35,
        "chef_projet": 0.50,
        "sysadmin": 0.10
    },
    "qualite": {
        "qualite": 1.0,
        "analyste": 0.50,
        "developpeur": 0.40,
        "expert_technique": 0.35,
        "chef_projet": 0.30,
        "sysadmin": 0.10,
        "dba": 0.10
    },
    "sysadmin": {
        "sysadmin": 1.0,
        "dba": 0.15,
        "developpeur": 0.0,
        "expert_technique": 0.25,
        "qualite": 0.10
    },
    "chef_projet": {
        "chef_projet": 1.0,
        "expert_technique": 0.50,
        "analyste": 0.40,
        "qualite": 0.30,
        "developpeur": 0.20
    },
    "analyste": {
        "analyste": 1.0,
        "qualite": 0.50,
        "chef_projet": 0.50,
        "developpeur": 0.30
    },
    "dba": {
        "dba": 1.0,
        "sysadmin": 0.15,
        "developpeur": 0.25,
        "expert_technique": 0.35,
        "qualite": 0.10
    }
}


DOMAINES_ROLE = {
    "developpeur": [
        "developpement", "developpement web", "application web",
        "microservices", "software", "programmation", "code",
        "java", "python", "javascript", "php", "c#", "spring", "api"
    ],
    "dba": [
        "base de donnees", "bases de donnees",
        "sql", "oracle", "postgres", "mysql",
        "postgresql", "database", "sgbd",
        "mariadb", "mongodb", "tuning sql", "pl/sql"
    ],
    "sysadmin": [
        "systeme", "systemes", "reseau", "reseaux",
        "administration systeme", "linux",
        "windows server", "infrastructure", "cloud",
        "devops", "virtualisation", "active directory"
    ],
    "qualite": [
        "test", "testing", "qa", "qualite", "recette",
        "validation", "selenium", "cypress", "istqb",
        "assurance qualite", "cahier de recette",
        "tests automatises"
    ],
    "analyste": [
        "analyse fonctionnelle", "analyste fonctionnel",
        "business analyst", "amoa",
        "analyse des besoins", "recueil des besoins",
        "expression des besoins", "specifications",
        "specifications fonctionnelles", "cahier des charges",
        "uml", "bpmn", "modelisation fonctionnelle",
        "ateliers metier", "diagramme uml", "analyse"
    ],
    "chef_projet": [
        "gestion de projet", "management de projet", "pmo",
        "scrum", "agile", "chef de projet",
        "directeur de projet", "planning",
        "budget", "chef de mission"
    ],
    "expert_technique": [
        "tech lead", "architecture", "lead dev",
        "expertise technique", "encadrement technique",
        "revue de code"
    ]
}


MOTS_GENERIQUES_SIMILARITE = {
    "systeme", "système", "information", "gestion",
    "projet", "projets", "mission", "missions",
    "expert", "experte", "developpement", "développement",
    "production", "national", "nationale",
    "solution", "application", "applications",
    "mise", "place", "plateforme",
    "informatique", "technique", "techniques",
    "service", "services", "experience",
    "expérience", "avoir", "conduite",
    "ans", "année", "années"
}


NIVEAUX_ACADEMIQUES = [
    (r'\b(doctorat|phd|docteur)\b', 8),
    (r'\b(master\s*2|m2|ing[é e]nieur|dea|dess|msc|master|bac\s*[\+\-]?\s*5)\b', 5),
    (r'\b(master\s*1|m1|ma[î i]trise|bac\s*[\+\-]?\s*4)\b', 4),
    (r'\b(licence|bachelor|l3|bac\s*[\+\-]?\s*3)\b', 3),
    (r'\b(dut|bts|deug|l2|bac\s*[\+\-]?\s*2)\b', 2),
    (r'\b(baccalaur[é e]at|bac)\b', 0)
]


ORGANISMES_RECONNUS = [
    "pmi", "project management institute", "axelos",
    "scrum.org", "scrum alliance", "istqb",
    "isaca", "the open group", "oracle", "microsoft",
    "amazon", "aws", "google", "cisco",
    "red hat", "comptia", "offsec",
    "sans", "giac", "iso"
]


CERTIFICATION_DOMAINES = {
        "gestion_projet": {
            "exactes": ["pmp", "prince2", "prince 2", "psm", "csm", "capm", "ipma", "pmi-acp", "prince2 practitioner"],
            "proches": ["agile", "scrum", "scrum master", "safe", "kanban", "pmi", "pmp certified"],
            "mots_cles": ["gestion de projet", "management de projet", "project management", "agile", "scrum", "prince", "pmp"]
        },
        "bases_donnees": {
            "exactes": ["oracle certified professional", "ocp", "oca", "mysql certified", "microsoft certified database", "cmdb"],
            "proches": ["oracle", "mysql", "sql server", "postgresql", "mongodb", "mariadb"],
            "mots_cles": ["database", "base de donnees", "bases de donnees", "sql", "oracle", "mysql", "sgbd"]
        },
        "test_logiciel": {
            "exactes": ["istqb foundation", "istqb advanced", "istqb expert", "cste", "istqb"],
            "proches": ["selenium", "cypress", "quality assurance", "qa", "software testing"],
            "mots_cles": ["test logiciel", "software testing", "testing", "recette", "assurance qualite", "qa"]
        },
        "architecture_logicielle": {
            "exactes": ["togaf", "isae", "aws certified solutions architect", "azure solutions architect expert"],
            "proches": ["software architecture", "enterprise architecture", "solution architect", "architecte SI"],
            "mots_cles": ["architecture logicielle", "software architecture", "architecture informatique", "enterprise architecture", "togaf"]
        },
        "data_analysis": {
            "exactes": ["google data analytics", "microsoft certified power bi", "tableau desktop certified", "tableau certified"],
            "proches": ["power bi", "tableau", "qlik", "looker", "data analyst"],
            "mots_cles": ["data analysis", "data analyst", "analyse de donnees", "data analytics", "business intelligence", "bi"]
        },
        "devops": {
            "exactes": ["cka", "ckad", "docker certified associate", "aws certified devops engineer", "azure devops engineer", "devops engineer"],
            "proches": ["kubernetes", "docker", "jenkins", "terraform", "ansible", "gitlab ci"],
            "mots_cles": ["devops", "ci/cd", "continuous integration", "continuous deployment", "kubernetes", "docker"]
        },
        "cybersecurite": {
            "exactes": ["cissp", "cism", "ceh", "oscp", "comptia security+", "iso 27001 lead auditor", "cisa"],
            "proches": ["security+", "iso 27001", "ethical hacker", "cybersecurity", "penta"],
            "mots_cles": ["cybersecurite", "securite informatique", "security", "pentest", "iso 27001", "auditeur securite"]
        },
        "cloud": {
            "exactes": ["aws certified practitioner", "aws certified sysops", "azure administrator", "gcp professional cloud architect"],
            "proches": ["aws", "azure", "gcp", "google cloud", "cloud practitioner"],
            "mots_cles": ["cloud", "aws", "azure", "gcp", "google cloud"]
        },
        "reseaux": {
            "exactes": ["ccna", "ccnp", "ccie", "jncis", "jncip", "comptia network+"],
            "proches": ["cisco", "juniper", "fortinet", "network+"],
            "mots_cles": ["reseau", "reseaux", "network", "routing", "switching", "telecom"]
        },
        "systemes": {
            "exactes": ["rhce", "rhcsa", "mcse", "mcsa", "lpi-1", "lpi-2"],
            "proches": ["linux", "red hat", "windows server", "sysadmin"],
            "mots_cles": ["systeme", "systemes", "administration systeme", "sysadmin", "linux", "windows server"]
        },
        "intelligence_artificielle": {
            "exactes": ["tensorflow developer", "aws certified machine learning", "azure ai engineer"],
            "proches": ["machine learning", "deep learning", "ai practitioner", "pytorch"],
            "mots_cles": ["intelligence artificielle", "ia", "machine learning", "deep learning", "ai"]
        },
        "data_engineering": {
            "exactes": ["databricks certified", "gcp professional data engineer", "aws certified data analytics"],
            "proches": ["spark", "hadoop", "snowflake", "big data"],
            "mots_cles": ["data engineering", "data engineer", "big data", "etl"]
        },
        "erp_sap": {
            "exactes": ["sap certified", "oracle e-business suite certified", "microsoft dynamics 365 certified"],
            "proches": ["sap", "oracle erp", "dynamics 365", "progiciel"],
            "mots_cles": ["erp", "sap", "progiciel de gestion", "pge"]
        }
}


DIPLOME_DOMAINES = {
    "informatique": {
        "synonymes": [
            "informatique", "genie informatique", "computer science",
            "computer engineering", "sciences informatiques",
            "technologies de l'information", "information technology",
            "ingenierie informatique", "systèmes d'information", "systemes d'information",
        ],
        "domaines_proches": [
            "genie logiciel", "systèmes d'information", "systèmes informatiques",
            "réseaux", "data science", "intelligence artificielle", "cybersécurité",
            "ingenieur informatique",
        ],
    },
    "geomatique": {
        "synonymes": [
            "géomatique", "geomatique", "sig", "gis", "géoinformatique",
            "geoinformatique", "information géographique", "geospatial", "sciences géomatiques",
        ],
        "domaines_proches": [
            "informatique", "bases_donnees", "systemes_information", "genie_logiciel", "data science",
        ],
    },
    "genie_logiciel": {
        "synonymes": [
            "génie logiciel", "développement logiciel", "developpement logiciel",
            "software engineering", "software development", "informatique logicielle",
        ],
        "domaines_proches": [
            "informatique", "systèmes d'information", "bases de données", "programmation",
            "ingenieur informatique", "data science", "intelligence artificielle",
            "cybersécurité",
        ],
    },
    "systemes_reseaux": {
        "synonymes": [
            "systèmes et réseaux", "systemes et reseaux", "systèmes informatiques et réseaux",
            "réseaux informatiques", "network engineering", "administration systèmes",
            "infrastructure informatique", "cloud", "ingenieerie des réseaux", "ingenierie des reseaux", "ingenieur informatique",
        ],
        "domaines_proches": [
            "informatique", "télécommunications", "cybersécurité", "cloud computing",
            "devops", "bases de données", "data science", "intelligence artificielle",
            "ingenierie informatique", "ingenieur informatique",
        ],
    },
    "bases_donnees": {
        "synonymes": [
            "bases de données", "bases de donnees", "database", "database systems",
            "data engineering", "systèmes de gestion de bases de données",
        ],
        "domaines_proches": [
            "informatique", "génie logiciel", "data science", "systèmes d'information",
            "big data", "data analysis", "intelligence artificielle",
            "ingenierie des données", "ingenieur informatique", "geomatique", "geospatial data", "gis", "sig",
        ],
    },
    "systemes_information": {
        "synonymes": [
            "systèmes d'information", "systemes d'information", "systeme d'information",
            "information systems", "management information systems", "informatique de gestion", "sig",
        ],
        "domaines_proches": [
            "informatique", "génie logiciel", "gestion de projet informatique",
            "bases de données", "data science", "intelligence artificielle",
            "cybersécurité", "ingenierie des données", "ingenieur informatique",
        ],
    },
    "gestion_projet_informatique": {
        "synonymes": [
            "gestion de projet informatique", "management de projet informatique",
            "it project management", "gestion de projets it",
            "management des systèmes d'information",
        ],
        "domaines_proches": [
            "systèmes d'information", "informatique", "gestion de projet",
            "génie logiciel", "gestion de projet agile", "scrum", "kanban",
            "devops", "cloud computing", "data science", "intelligence artificielle",
            "cybersécurité", "bases de données", "systemes d'information",
            "ingenierie informatique", "ingenieur informatique", "ingenieur",
        ],
    },
}