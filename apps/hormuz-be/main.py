from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Keep telemetry setup first so future instrumented clients are patched at
# construction time. The scaffold implementation is a no-op until OTEL deps are
# added.
from infrastructure.observability.telemetry import setup_telemetry_providers

setup_telemetry_providers()

from infrastructure.config import get_backend_settings  # noqa: E402
from infrastructure.di import wire_cross_module_events  # noqa: E402
from infrastructure.health.router import router as health_router  # noqa: E402
from infrastructure.observability.telemetry import instrument_app  # noqa: E402
from modules.scan.adapters.inbound.router import router as scan_router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    wire_cross_module_events()
    yield


def _cors_origins() -> list[str]:
    return get_backend_settings().cors_origins


app = FastAPI(title="Hormuz API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

instrument_app(app)

app.include_router(health_router)
app.include_router(scan_router)
