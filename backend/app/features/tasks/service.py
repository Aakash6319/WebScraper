"""
AutoWebAgent - Task Service
=============================
Task CRUD and execution orchestration.
Delegates actual agent execution to the AgentService.
"""

from typing import Optional, List
from datetime import datetime, timezone

from beanie import PydanticObjectId
from loguru import logger

from app.core.exceptions import TaskNotFoundError
from app.features.tasks.models import TaskDocument, TaskStatus
from app.features.tasks.schemas import TaskCreateRequest


class TaskService:
    """Manages task lifecycle — CRUD + delegation to AgentService."""

    @staticmethod
    async def create_task(
        user_id: str,
        data: TaskCreateRequest,
    ) -> TaskDocument:
        """Create a new task and queue it for execution."""
        task = TaskDocument(
            user_id=user_id,
            session_id=data.session_id,
            website_id=data.website_id,
            prompt=data.prompt,
            status=TaskStatus.PENDING,
            priority=data.priority,
            max_retries=data.max_retries,
            timeout_seconds=data.timeout_seconds,
        )
        await task.insert()
        logger.info(f"📝 Task created: {task.id} — '{data.prompt[:80]}...'")

        # Trigger async execution (via Celery or background task)
        # This will be handled by AgentService.execute_task(task)
        from app.features.agent.service import AgentService
        import asyncio
        asyncio.create_task(AgentService.execute_task(str(task.id), user_id))

        return task

    @staticmethod
    async def get_task(task_id: str, user_id: str) -> TaskDocument:
        """Get a task, verifying ownership."""
        task = await TaskDocument.get(PydanticObjectId(task_id))
        if not task or task.user_id != user_id:
            raise TaskNotFoundError(task_id)
        return task

    @staticmethod
    async def list_user_tasks(
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> tuple[List[TaskDocument], int]:
        """List tasks for a user with optional filters."""
        query = TaskDocument.find(TaskDocument.user_id == user_id)

        if status:
            query = query.find(TaskDocument.status == status)
        if session_id:
            query = query.find(TaskDocument.session_id == session_id)

        total = await query.count()
        tasks = await query.sort("-created_at") \
            .skip((page - 1) * page_size) \
            .limit(page_size) \
            .to_list()

        return tasks, total

    @staticmethod
    async def cancel_task(task_id: str, user_id: str) -> TaskDocument:
        """Cancel a pending or running task."""
        task = await TaskService.get_task(task_id, user_id)

        if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.RETRYING):
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now(timezone.utc)
            if task.started_at:
                task.duration_ms = int(
                    (task.completed_at - task.started_at).total_seconds() * 1000
                )
            await task.save()
            logger.info(f"🚫 Task cancelled: {task_id}")

        return task

    @staticmethod
    async def update_task_status(
        task_id: str,
        status: str,
        error_message: Optional[str] = None,
        extracted_data: Optional[dict] = None,
        step_result: Optional[dict] = None,
    ) -> TaskDocument:
        """Update task status and append results."""
        task = await TaskDocument.get(PydanticObjectId(task_id))
        if not task:
            raise TaskNotFoundError(task_id)

        task.status = status
        task.updated_at = datetime.now(timezone.utc)

        if error_message:
            task.error_message = error_message
        if extracted_data:
            task.extracted_data = extracted_data
        if step_result:
            task.steps_executed.append(step_result)
            task.current_step = len(task.steps_executed)

        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            task.completed_at = datetime.now(timezone.utc)
            if task.started_at:
                task.duration_ms = int(
                    (task.completed_at - task.started_at).total_seconds() * 1000
                )

        await task.save()
        return task

    @staticmethod
    async def delete_task(task_id: str, user_id: str) -> None:
        """Delete a task."""
        task = await TaskService.get_task(task_id, user_id)
        await task.delete()
        logger.info(f"🗑️ Task deleted: {task_id}")
