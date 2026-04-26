from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
import json

from database import get_session
from controllers.relay import RelayController
from middleware.auth import require_user, AuthContext

router = APIRouter(prefix="/v1")


@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = RelayController(db)
    return await controller.chat_completions(request, ctx)


@router.post("/messages")
async def messages(
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = RelayController(db)
    body = await request.json()
    if "response_format" not in body:
        body["response_format"] = "anthropic"

    from starlette.datastructures import URL, QueryParams
    scope = dict(request.scope)
    scope["method"] = "POST"
    scope["_body"] = json.dumps(body).encode()

    async def receive():
        return {"type": "http.request", "body": json.dumps(body).encode()}

    new_request = Request(scope, receive)
    return await controller.chat_completions(new_request, ctx)


@router.post("/completions")
async def completions(
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = RelayController(db)
    return await controller.completions(request, ctx)


@router.post("/embeddings")
async def embeddings(
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = RelayController(db)
    return await controller.embeddings(request, ctx)


@router.post("/images/generations")
async def images_generations(
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = RelayController(db)
    return await controller.images_generations(request, ctx)


@router.post("/audio/transcriptions")
async def audio_transcriptions(
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = RelayController(db)
    return await controller.audio_transcriptions(request, ctx)


@router.post("/audio/translations")
async def audio_translations(
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = RelayController(db)
    return await controller.audio_translations(request, ctx)


@router.post("/audio/speech")
async def audio_speech(
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = RelayController(db)
    return await controller.audio_speech(request, ctx)


@router.get("/models")
async def list_models(
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = RelayController(db)
    return await controller.list_models(ctx)


@router.get("/models/{model}")
async def retrieve_model(
    model: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = RelayController(db)
    return await controller.retrieve_model(model, ctx)


@router.post("/edits")
async def edits(
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = RelayController(db)
    return await controller.edits(request, ctx)


@router.post("/moderations")
async def moderations(
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = RelayController(db)
    return await controller.moderations(request, ctx)


@router.get("/files")
async def list_files(
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(content={
        "object": "list",
        "data": [],
    })


@router.post("/files")
async def upload_file(
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "File upload not implemented", "type": "not_implemented_error"}}
    )


@router.get("/files/{file_id}")
async def retrieve_file(
    file_id: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "File retrieval not implemented", "type": "not_implemented_error"}}
    )


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "File deletion not implemented", "type": "not_implemented_error"}}
    )


@router.get("/files/{file_id}/content")
async def get_file_content(
    file_id: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "File content not implemented", "type": "not_implemented_error"}}
    )


@router.post("/assistants")
async def create_assistant(
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Assistants API not implemented", "type": "not_implemented_error"}}
    )


@router.get("/assistants/{assistant_id}")
async def retrieve_assistant(
    assistant_id: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Assistants API not implemented", "type": "not_implemented_error"}}
    )


@router.post("/assistants/{assistant_id}")
async def modify_assistant(
    assistant_id: str,
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Assistants API not implemented", "type": "not_implemented_error"}}
    )


@router.delete("/assistants/{assistant_id}")
async def delete_assistant(
    assistant_id: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Assistants API not implemented", "type": "not_implemented_error"}}
    )


@router.get("/assistants")
async def list_assistants(
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(content={
        "object": "list",
        "data": [],
    })


@router.post("/assistants/{assistant_id}/files")
async def create_assistant_file(
    assistant_id: str,
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Assistants API not implemented", "type": "not_implemented_error"}}
    )


@router.get("/assistants/{assistant_id}/files/{file_id}")
async def get_assistant_file(
    assistant_id: str,
    file_id: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Assistants API not implemented", "type": "not_implemented_error"}}
    )


@router.get("/assistants/{assistant_id}/files")
async def list_assistant_files(
    assistant_id: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(content={
        "object": "list",
        "data": [],
    })


@router.delete("/assistants/{assistant_id}/files/{file_id}")
async def delete_assistant_file(
    assistant_id: str,
    file_id: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Assistants API not implemented", "type": "not_implemented_error"}}
    )


@router.post("/threads")
async def create_thread(
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Threads API not implemented", "type": "not_implemented_error"}}
    )


@router.get("/threads/{thread_id}")
async def retrieve_thread(
    thread_id: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Threads API not implemented", "type": "not_implemented_error"}}
    )


@router.post("/threads/{thread_id}")
async def modify_thread(
    thread_id: str,
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Threads API not implemented", "type": "not_implemented_error"}}
    )


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Threads API not implemented", "type": "not_implemented_error"}}
    )


@router.get("/threads")
async def list_threads(
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(content={
        "object": "list",
        "data": [],
    })


@router.post("/threads/{thread_id}/messages")
async def create_message(
    thread_id: str,
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Threads API not implemented", "type": "not_implemented_error"}}
    )


@router.get("/threads/{thread_id}/messages/{message_id}")
async def retrieve_message(
    thread_id: str,
    message_id: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Threads API not implemented", "type": "not_implemented_error"}}
    )


@router.get("/threads/{thread_id}/messages")
async def list_messages(
    thread_id: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(content={
        "object": "list",
        "data": [],
    })


@router.post("/threads/{thread_id}/runs")
async def create_run(
    thread_id: str,
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Threads API not implemented", "type": "not_implemented_error"}}
    )


@router.get("/threads/{thread_id}/runs/{run_id}")
async def retrieve_run(
    thread_id: str,
    run_id: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Threads API not implemented", "type": "not_implemented_error"}}
    )


@router.get("/threads/{thread_id}/runs")
async def list_runs(
    thread_id: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(content={
        "object": "list",
        "data": [],
    })


@router.post("/threads/{thread_id}/runs/{run_id}/submit_tool_outputs")
async def submit_tool_outputs(
    thread_id: str,
    run_id: str,
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Threads API not implemented", "type": "not_implemented_error"}}
    )


@router.post("/threads/{thread_id}/runs/{run_id}/cancel")
async def cancel_run(
    thread_id: str,
    run_id: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Threads API not implemented", "type": "not_implemented_error"}}
    )


@router.get("/threads/{thread_id}/runs/{run_id}/steps/{step_id}")
async def retrieve_run_step(
    thread_id: str,
    run_id: str,
    step_id: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Threads API not implemented", "type": "not_implemented_error"}}
    )


@router.get("/threads/{thread_id}/runs/{run_id}/steps")
async def list_run_steps(
    thread_id: str,
    run_id: str,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    return JSONResponse(content={
        "object": "list",
        "data": [],
    })


@router.post("/engines/{model}/embeddings")
async def engine_embeddings(
    model: str,
    request: Request,
    ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_session),
):
    controller = RelayController(db)
    return await controller.embeddings(request, ctx)