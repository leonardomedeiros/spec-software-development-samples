from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.adapters.api import build_router
from app.application.use_cases import CreateTask
from app.infrastructure.repositories import (
    InMemoryProjectRepository,
    InMemoryTaskRepository,
    InMemoryUserRepository,
)

projects = InMemoryProjectRepository()
users = InMemoryUserRepository()
tasks = InMemoryTaskRepository()
create_task = CreateTask(projects, users, tasks)

app = FastAPI(title="TaskTrack")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    detail = []
    for error in exc.errors():
        message = error["msg"]
        if message.startswith("Value error, "):
            message = message.removeprefix("Value error, ")
        detail.append({"loc": error["loc"], "msg": message, "type": error["type"]})
    return JSONResponse(status_code=422, content={"detail": detail})


app.include_router(build_router(create_task))