from fastapi import FastAPI
from app.database.session import engine
from app.models.tender import Base
from app.api.tender import router as tender_router
from fastapi.middleware.cors import CORSMiddleware

# Crée les tables SQL
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AO AI Platform API", version="1.0.0")

origins = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"], # L'URL de l'application Angular
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Inclusion du router de l'appel d'offres
app.include_router(tender_router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "status": "success",
        "message": "API opérationnelle. Visitez /docs pour tester les endpoints."
    }