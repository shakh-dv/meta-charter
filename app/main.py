
from fastapi.exceptions import RequestValidationError
import uvicorn
from fastapi import Depends, FastAPI, Request
from app.core.response import api_response
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.router import router as auth_router
from app.api.offers.router import router as offers_router
from app.db.session import get_session

app = FastAPI()
app.include_router(offers_router)
app.include_router(auth_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        message = error["msg"].removeprefix("Value error, ")
        errors.append({"field": field, "message": message})
    return api_response(
        status="error",
        code=422,
        errors=errors,
        http_code=422
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return api_response(
        status="error",
        code=exc.status_code,
        errors=[{"message": str(exc.detail)}],
        http_code=exc.status_code
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    trace_id = str(uuid.uuid4())
    logging.error(f"Unhandled error [{trace_id}]:", exc_info=exc)
    return api_response(
        status="error",
        code=500,
        data={"request_id": trace_id},
        errors=[{"message": str(exc)}],
        http_code=500
    )

def run_dev():
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )

@app.get("/health/db")
async def db_check(session: AsyncSession = Depends(get_session)):
    result = await session.execute(text("SELECT 1"))
    return api_response(data={"db": result.scalar()})

