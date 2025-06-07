import logging
import contextlib

from fastapi import FastAPI
from .agent_ws import router as agent_ws_router
from .config import settings
from .graph import init_graph, shutdown_graph

# Configure logging once, at module import time
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Start Services
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting…")
    # initialize RedisSaver + compile your graph
    await init_graph()
    yield
    logger.info("Application shutting down…")
    # clean up RedisSaver
    await shutdown_graph()

# 3) Single FastAPI app
app = FastAPI(
    title="Interview Agent",
    lifespan=lifespan
)

# Mount the websocket router
app.include_router(agent_ws_router)