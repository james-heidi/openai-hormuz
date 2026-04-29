from fastapi import FastAPI


def setup_telemetry_providers() -> None:
    """Install process-wide telemetry providers.

    This starts as a no-op to keep the hackathon scaffold lightweight. Add
    OpenTelemetry providers here before constructing Mongo, Redis, gRPC, or
    OpenAI clients.
    """


def instrument_app(app: FastAPI) -> None:
    """Instrument the FastAPI app when OTEL dependencies are enabled."""

