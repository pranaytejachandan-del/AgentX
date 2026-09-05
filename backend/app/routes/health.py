from fastapi import APIRouter, Response, status
from app.schemas.health import RootResponse, HealthCheckResponse
from app.database.connection import check_db_connection

router = APIRouter(tags=["Health"])


@router.get("/", response_model=RootResponse)
def get_root():
    """Root status endpoint."""
    return RootResponse(status="ok", service="AgentX")


@router.get("/health", response_model=HealthCheckResponse)
def get_health(response: Response):
    """Database connectivity health check endpoint."""
    db_connected = check_db_connection()
    
    if db_connected:
        return HealthCheckResponse(
            status="ok",
            service="AgentX",
            database="connected"
        )
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthCheckResponse(
            status="error",
            service="AgentX",
            database="disconnected",
            detail="Could not establish connection to the database"
        )
