"""
AutoWebAgent - Task Routes
============================
Task CRUD and status endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from app.features.auth.dependencies import get_current_user
from app.features.auth.models import UserDocument
from app.features.tasks.schemas import (
    TaskCreateRequest,
    TaskResponse,
    TaskListResponse,
    TaskCancelRequest,
)
from app.features.tasks.service import TaskService
from app.features.tasks.models import TaskStatus

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    data: TaskCreateRequest,
    current_user: UserDocument = Depends(get_current_user),
):
    """Create and queue a new automation task."""
    try:
        task = await TaskService.create_task(str(current_user.id), data)
        return task.dict_for_response()
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    session_id: Optional[str] = None,
    current_user: UserDocument = Depends(get_current_user),
):
    """List tasks with optional filters."""
    tasks, total = await TaskService.list_user_tasks(
        str(current_user.id), page, page_size, status, session_id
    )
    return TaskListResponse(
        tasks=[t.dict_for_response() for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: UserDocument = Depends(get_current_user),
):
    """Get task details including execution progress."""
    try:
        task = await TaskService.get_task(task_id, str(current_user.id))
        return task.dict_for_response()
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: str,
    current_user: UserDocument = Depends(get_current_user),
):
    """Cancel a pending or running task."""
    try:
        task = await TaskService.cancel_task(task_id, str(current_user.id))
        return task.dict_for_response()
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    current_user: UserDocument = Depends(get_current_user),
):
    """Delete a task."""
    try:
        await TaskService.delete_task(task_id, str(current_user.id))
        return {"message": "Task deleted successfully"}
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{task_id}/submit-input", response_model=TaskResponse)
async def submit_task_input(
    task_id: str,
    data: dict,  # {"value": "123456"}
    current_user: UserDocument = Depends(get_current_user),
):
    """Submit user input / OTP code for a waiting task."""
    try:
        task = await TaskService.get_task(task_id, str(current_user.id))
        if task.status != TaskStatus.WAITING_USER_INPUT:
            raise HTTPException(status_code=400, detail="Task is not waiting for user input.")
        
        # Save input value to database
        task.user_input_value = data.get("value")
        await task.save()
        return task.dict_for_response()
    except Exception as e:
        if hasattr(e, "status_code"):
            raise HTTPException(status_code=e.status_code, detail=e.message)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{task_id}/debug-screenshot")
async def debug_task_screenshot(
    task_id: str,
    current_user: UserDocument = Depends(get_current_user),
):
    """Take a live screenshot of the running task page for debugging."""
    from app.features.sessions.service import SessionService
    from app.features.tasks.models import TaskDocument
    from bson import ObjectId
    from fastapi.responses import Response

    task = await TaskDocument.get(ObjectId(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    session_id = str(task.session_id)
    context = SessionService._active_contexts.get(session_id)
    if not context:
        raise HTTPException(
            status_code=404,
            detail=f"Active context not found for session {session_id}. Keys: {list(SessionService._active_contexts.keys())}"
        )

    pages = context.pages
    if not pages:
        raise HTTPException(status_code=404, detail="No pages open in context")

    page = pages[0]
    screenshot_bytes = await page.screenshot(type="png", full_page=True)
    return Response(content=screenshot_bytes, media_type="image/png")


@router.get("/{task_id}/debug-text")
async def debug_task_text(
    task_id: str,
    current_user: UserDocument = Depends(get_current_user),
):
    """Retrieve the URL, title, and body text of the running task page for debugging."""
    from app.features.sessions.service import SessionService
    from app.features.tasks.models import TaskDocument
    from bson import ObjectId

    task = await TaskDocument.get(ObjectId(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    session_id = str(task.session_id)
    context = SessionService._active_contexts.get(session_id)
    if not context:
        raise HTTPException(
            status_code=404,
            detail=f"Active context not found for session {session_id}"
        )

    pages = context.pages
    if not pages:
        raise HTTPException(status_code=404, detail="No pages open in context")

    page = pages[0]
    url = page.url
    title = await page.title()
    text = await page.evaluate("() => document.body.innerText")
    
    # Analyze captcha elements
    captcha_elements = await page.evaluate("""
        () => {
            const results = {};
            const selectors = [
                'iframe[src*="recaptcha/api2"]',
                'iframe[src*="google.com/recaptcha"]',
                '.g-recaptcha',
                '[data-sitekey]',
                '#recaptcha',
                'iframe'
            ];
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el) {
                    results[sel] = {
                        tagName: el.tagName,
                        src: el.src || null,
                        sitekey: el.getAttribute('data-sitekey') || null,
                        id: el.id || null,
                        className: el.className || null,
                        innerHTML: el.innerHTML || null,
                        outerHTML: el.outerHTML.slice(0, 500)
                    };
                }
            }
            return results;
        }
    """)
    
    return {
        "url": url,
        "title": title,
        "text_length": len(text),
        "text_preview": text[:1000],
        "captcha_elements": captcha_elements
    }
