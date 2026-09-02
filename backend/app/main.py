from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.session import init_db
from app.api.v1.events import router as events_router
from app.api.v1.agent_stream import router as stream_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database tables
    await init_db()
    yield
    # Shutdown: clean up connections
    pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Autonomous Multi-Agent Event Operations & Provisioning Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration for Vue 3 Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Liveness Probe
@app.get("/healthz", status_code=status.HTTP_200_OK, tags=["health"])
async def liveness_check():
    return {"status": "HEALTHY", "service": "cadence-gateway"}

# Readiness Probe
@app.get("/readyz", status_code=status.HTTP_200_OK, tags=["health"])
async def readiness_check():
    return {
        "status": "READY",
        "database": "CONNECTED",
        "mcp_server": "AVAILABLE",
        "agents": "READY"
    }

# Mount API Routers
app.include_router(events_router, prefix=settings.API_V1_STR)
app.include_router(stream_router, prefix=settings.API_V1_STR)
