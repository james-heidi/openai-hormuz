from json import JSONDecodeError

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError

from modules.scan import get_fix_generator, get_scan_orchestrator
from modules.scan.application.fix_generator import FixGenerator
from modules.scan.application.orchestrator import ScanOrchestrator
from modules.scan.application.repositories import RepositoryPreparationError
from modules.scan.domain.entities import ErrorDetail, FixRequest, FixSummary, ScanRequest, ScanSummary
from modules.scan.domain.errors import ScanConfigurationError

router = APIRouter(tags=["scan"])


@router.post("/api/scans/preview", response_model=ScanSummary)
async def preview_scan(
    request: ScanRequest,
    orchestrator: ScanOrchestrator = Depends(get_scan_orchestrator),
) -> ScanSummary:
    async def emit(_event: dict) -> None:
        return None

    try:
        return await orchestrator.run(request, emit)
    except ScanConfigurationError as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorDetail(code=exc.code, message=str(exc)).model_dump(),
        ) from exc
    except RepositoryPreparationError as exc:
        raise HTTPException(
            status_code=400,
            detail=ErrorDetail(code=exc.code, message=exc.message).model_dump(),
        ) from exc


@router.post("/api/fixes/generate", response_model=FixSummary)
async def generate_fixes(
    request: FixRequest,
    fix_generator: FixGenerator = Depends(get_fix_generator),
) -> FixSummary:
    try:
        return await fix_generator.generate(request)
    except RepositoryPreparationError as exc:
        raise HTTPException(
            status_code=400,
            detail=ErrorDetail(code=exc.code, message=exc.message).model_dump(),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=ErrorDetail(code="invalid_fix_request", message=str(exc)).model_dump(),
        ) from exc


@router.post("/api/scans/fixes", response_model=FixSummary)
async def generate_scan_fixes(
    request: FixRequest,
    fix_generator: FixGenerator = Depends(get_fix_generator),
) -> FixSummary:
    return await generate_fixes(request, fix_generator)


@router.websocket("/ws/scan")
async def scan_socket(
    websocket: WebSocket,
    orchestrator: ScanOrchestrator = Depends(get_scan_orchestrator),
) -> None:
    await websocket.accept()

    async def emit(event: dict) -> None:
        await _send_event(websocket, event)

    try:
        request = await _receive_scan_request(websocket)
        if request is None:
            return
        await orchestrator.run(request, emit)
    except WebSocketDisconnect:
        return
    except ScanConfigurationError as exc:
        await _send_error(websocket, exc.code, str(exc))
        await _close_websocket(websocket, code=1011)
    except RepositoryPreparationError as exc:
        await _send_error(websocket, exc.code, exc.message)
    except Exception:
        await _send_error(
            websocket,
            "scan_failed",
            "The scan failed before completion.",
        )
        await _close_websocket(websocket, code=1011)


async def _receive_scan_request(websocket: WebSocket) -> ScanRequest | None:
    try:
        payload = await websocket.receive_json()
    except JSONDecodeError:
        await _send_error(
            websocket,
            "invalid_scan_request",
            "Scan request must be valid JSON.",
        )
        return None

    if not isinstance(payload, dict):
        await _send_error(
            websocket,
            "invalid_scan_request",
            "Scan request must be a JSON object.",
        )
        return None

    try:
        return ScanRequest.model_validate(payload)
    except ValidationError:
        await _send_error(
            websocket,
            "invalid_scan_request",
            "Scan request must include a non-empty repo_path.",
        )
        return None


async def _send_error(websocket: WebSocket, code: str, message: str) -> None:
    await _send_event(
        websocket,
        {
            "type": "error",
            "detail": ErrorDetail(code=code, message=message).model_dump(),
        },
    )


async def _send_event(websocket: WebSocket, event: dict) -> None:
    await websocket.send_json(jsonable_encoder(event))


async def _close_websocket(websocket: WebSocket, code: int) -> None:
    try:
        await websocket.close(code=code)
    except RuntimeError:
        return
