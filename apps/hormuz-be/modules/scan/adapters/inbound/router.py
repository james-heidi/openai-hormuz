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


@router.websocket("/ws/scans")
async def scan_socket(
    websocket: WebSocket,
    orchestrator: ScanOrchestrator = Depends(get_scan_orchestrator),
) -> None:
    await websocket.accept()

    async def emit(event: dict) -> None:
        await websocket.send_json(jsonable_encoder(event))

    try:
        payload = await websocket.receive_json()
        request = ScanRequest.model_validate(payload)
        await orchestrator.run(request, emit)
    except WebSocketDisconnect:
        return
    except ScanConfigurationError as exc:
        await emit(
            {
                "type": "error",
                "detail": ErrorDetail(code=exc.code, message=str(exc)).model_dump(),
            }
        )
        await websocket.close(code=1011)
    except ValidationError as exc:
        await emit(
            {
                "type": "error",
                "detail": ErrorDetail(
                    code="invalid_scan_request",
                    message=str(exc),
                ).model_dump(),
            }
        )
    except RepositoryPreparationError as exc:
        await emit(
            {
                "type": "error",
                "detail": ErrorDetail(code=exc.code, message=exc.message).model_dump(),
            }
        )
    except Exception:
        await emit(
            {
                "type": "error",
                "detail": ErrorDetail(
                    code="scan_failed",
                    message="The scan failed before completion.",
                ).model_dump(),
            }
        )
        await websocket.close(code=1011)
