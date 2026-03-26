from fastapi.responses import JSONResponse

def api_response(
    *,
    data: dict = None,
    status: str = "success",
    code: int = 100,
    errors: list = None,
    http_code: int = 200
):
    return JSONResponse(
        status_code=http_code,
        content={
            "status": status,
            "code": code,
            "data": data if data is not None else {},
            "errors": errors if errors is not None else [],
        },
    )
