from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError

from modules.scan import get_scan_orchestrator
from modules.scan.application.orchestrator import ScanOrchestrator
from modules.scan.application.repositories import RepositoryPreparationError
from modules.scan.domain.entities import ErrorDetail, ScanRequest, ScanSummary

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
    except RepositoryPreparationError as exc:
        raise HTTPException(
            status_code=400,
            detail=ErrorDetail(code=exc.code, message=exc.message).model_dump(),
        ) from exc


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
