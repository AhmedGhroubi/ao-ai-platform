# 🤖 AO AI Platform

**AI-Powered Tender Analysis & Staffing Platform**

AO AI Platform est une plateforme intelligente destinée à automatiser l'analyse des **appels d'offres (AO)** et à faciliter la constitution d'équipes techniques adaptées aux exigences d'un projet.

La plateforme utilise des techniques d'**Intelligence Artificielle**, de **recherche sémantique** et de **matching** pour analyser les documents d'appel d'offres, identifier les profils recherchés et sélectionner les experts les plus pertinents à partir d'une base de CV.

---

## 🎯 Objectifs

La plateforme vise à automatiser plusieurs étapes du processus de réponse aux appels d'offres :

* 📄 Analyse automatique des documents d'appel d'offres
* 🔎 Extraction des profils et postes demandés
* 📋 Extraction des critères d'évaluation associés à chaque poste
* 👤 Analyse et structuration des CV des experts
* 🧠 Recherche des experts correspondant aux critères
* 📊 Calcul d'un score de compatibilité entre les experts et les postes
* 🤖 Génération de justifications pour les recommandations
* 👥 Constitution d'une équipe technique adaptée
* ✏️ Validation et modification manuelle des propositions
* 📑 Génération des documents finaux de réponse

---

## 🏗️ Architecture

```text
ao-ai-platform/
│
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   ├── api/
│   │   ├── database/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── utils/
│   │   └── main.py
│   │
│   └── storage/
│       └── uploads/
│           └── CVs/
│
├── frontend/
│   └── src/
│
├── storage/
│   └── uploads/
│       └── CVs/
│
├── docs/
│   ├── banner.png
│   └── logo.png
│
├── requirements.txt
├── .env
└── README.md
```

---

## 🔄 Workflow

```text
                    ┌─────────────────────┐
                    │  Appel d'offres PDF │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Analyse du document │
                    │       (LLM)         │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Profils recherchés  │
                    │ + critères          │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Recherche dans la   │
                    │ base des experts    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Matching & Ranking  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Experts recommandés │
                    │ + scores            │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Équipe technique    │
                    │ proposée            │
                    └─────────────────────┘
```

---

## 🧠 Fonctionnalités IA

### 1. Analyse des appels d'offres

Le système analyse les documents PDF afin d'extraire les informations importantes :

* Poste demandé
* Nombre de personnes nécessaires
* Niveau académique
* Années d'expérience
* Nombre de missions similaires
* Compétences techniques
* Certifications
* Langues
* Domaines d'expérience
* Critères d'évaluation

Une étape de validation permet ensuite de corriger ou d'ajuster les informations extraites.

---

### 2. Analyse des CV

Les CV sont transformés en données structurées afin de faciliter leur recherche et leur comparaison.

Les informations peuvent notamment inclure :

* Informations générales
* Formation
* Expériences professionnelles
* Postes occupés
* Compétences
* Certifications
* Langues
* Missions réalisées
* Domaines d'expertise

Les CV sont identifiés par un identifiant unique afin d'éviter la création de doublons lors d'une nouvelle version du même CV.

---

### 3. Matching des experts

Le système compare les exigences du poste avec les caractéristiques des experts.

Le matching prend notamment en compte :

* 🎓 Formation
* 💼 Expérience professionnelle
* 👨‍💻 Expérience dans le rôle recherché
* 🏢 Domaine d'expérience
* 📋 Nombre de missions similaires
* 🏆 Certifications
* 🌍 Langues
* 🛠️ Compétences techniques

Un score global de compatibilité est ensuite calculé.

---

### 4. Ranking

Les experts sont classés en fonction de leur compatibilité avec chaque poste.

Exemple :

```text
Chef de Mission

1. Expert A → 86.5 %
2. Expert B → 81.2 %
3. Expert C → 76.7 %
4. Expert D → 71.4 %
5. Expert E → 68.9 %
```

Le système peut ensuite proposer les meilleurs candidats pour chaque poste.

---

## 🛠️ Technologies utilisées

### Backend

* Python
* FastAPI
* SQLAlchemy
* PostgreSQL
* Pydantic
* Uvicorn

### Intelligence Artificielle

* Large Language Models (LLM)
* Semantic Search
* Information Extraction
* Text Similarity
* Ranking

### LLM

Le projet utilise des modèles de langage pour certaines tâches d'extraction, d'analyse et de génération.

### Recherche

* Recherche textuelle
* Recherche sémantique
* Similarité entre profils et critères

### Frontend

* Angular
* TypeScript
* HTML / CSS

### Base de données

* PostgreSQL

### Conteneurisation

* Docker
* Docker Desktop

---

## ⚙️ Installation

### 1. Cloner le projet

```bash
git clone <repository-url>
cd ao-ai-platform
```

### 2. Créer l'environnement virtuel

Sous Windows :

```bash
python -m venv .venv
```

Activer l'environnement :

```bash
.venv\Scripts\activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

---

## 🐘 Lancer PostgreSQL avec Docker

La base de données PostgreSQL est exécutée dans un conteneur Docker.

### 1. Vérifier que Docker fonctionne

```bash
docker --version
```

Puis :

```bash
docker ps
```

### 2. Créer et démarrer le conteneur PostgreSQL

```bash
docker run -d \
  --name ao-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=ao_db \
  -p 5433:5432 \
  postgres:17
```

Sous PowerShell, tu peux également utiliser une seule ligne :

```powershell
docker run -d --name ao-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=password -e POSTGRES_DB=ao_db -p 5433:5432 postgres:17
```

La configuration correspond alors à :

```text
Host:     127.0.0.1
Port:     5433
Database: ao_db
User:     postgres
Password: password
```

### 3. Vérifier que le conteneur fonctionne

```bash
docker ps
```

Tu devrais voir :

```text
ao-postgres
```

avec le port :

```text
5433 -> 5432
```

### 4. Arrêter PostgreSQL

```bash
docker stop ao-postgres
```

### 5. Redémarrer PostgreSQL

```bash
docker start ao-postgres
```

###

---

## 🔐 Configuration

Créer un fichier `.env` dans le dossier `backend/` :

```env
DATABASE_URL=postgresql://postgres:password@127.0.0.1:5433/ao_db?client_encoding=utf8

API_KEY=your_api_key
```

Ajouter le fichier `.env` au `.gitignore` :

```text
.env
.venv/
__pycache__/
*.pyc
```

---

## ▶️ Lancer le Backend

Depuis la racine du projet, entrer dans le dossier `backend` :

```bash
cd backend
```

Puis :

```bash
uvicorn app.main:app --reload
```

L'API sera accessible sur :

```text
http://127.0.0.1:8000
```

### Documentation Swagger

```text
http://127.0.0.1:8000/docs
```

---

## 🖥️ Lancer le Frontend

Dans un autre terminal :

```bash
cd frontend
```

Installer les dépendances :

```bash
npm install
```

Lancer Angular :

```bash
ng serve
```

Le frontend sera ensuite accessible à l'adresse indiquée par Angular dans le terminal.

---

## 📁 Gestion des données

Les documents utilisés par la plateforme sont organisés comme suit :

```text
storage/
├── uploads/
│   └── CVs/
└── tenders/
```


---

## 🚀 Évolutions prévues

* Amélioration du matching sémantique
* Optimisation du ranking
* Support de nouveaux formats de documents
* Amélioration de la génération des justifications
* Optimisation des coûts LLM
* Amélioration de l'interface de constitution d'équipe

---

## 👨‍💻 Projet

**AO AI Platform**
*AI-Powered Tender Analysis & Staffing Platform*

Projet réalisé dans le cadre d'un projet de stage en ingénierie informatique.

---

## 📄 License

Ce projet est destiné à un usage académique et/ou professionnel selon les conditions définies par l'organisation propriétaire du projet.
