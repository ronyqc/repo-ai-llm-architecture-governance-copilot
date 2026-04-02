from fastapi import FastAPI

from src.api.routes import router


app = FastAPI(title="Architecture Governance Copilot")
app.include_router(router)
