from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging


async def http_exception_handler(request: Request, exception: HTTPException):
    return JSONResponse(
        status_code=exception.status_code,
        content={"status_code": exception.status_code, "message": exception.detail},
    )


async def validation_exception_error(
    request: Request, exception: RequestValidationError
):

    exception_object = exception.errors()

    exception_strings = []

    for string in exception_object:
        result = (
            f"Validation Error in location '{'/'.join(string['loc'])}'. {string['msg']}"
        )
        exception_strings.append(result)

    return JSONResponse(
        status_code=422, content={"status_code": 422, "message": exception_strings}
    )


async def catch_all_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logging.basicConfig(filename="errors.log", level=logging.INFO)
        logging.info(f"Error happened! {e}")
        print(e)
        return JSONResponse(
            status_code=500, content={"message": "Internal server error."}
        )
