from typing import Any, Callable

from app.jobs.base import JobDefinition, JobPriority


class JobRegistry:
    _definitions: dict[str, JobDefinition] = {}

    @classmethod
    def register(
        cls,
        job_type: str,
        handler: Callable[..., Any],
        description: str = "",
        max_retries: int = 3,
        priority: JobPriority = JobPriority.MEDIUM,
        timeout_seconds: int = 300,
        idempotent: bool = False,
    ) -> None:
        cls._definitions[job_type] = JobDefinition(
            job_type=job_type,
            handler=handler,
            description=description,
            max_retries=max_retries,
            priority=priority,
            timeout_seconds=timeout_seconds,
            idempotent=idempotent,
        )

    @classmethod
    def get(cls, job_type: str) -> JobDefinition | None:
        return cls._definitions.get(job_type)

    @classmethod
    def get_handler(cls, job_type: str) -> Callable[..., Any] | None:
        definition = cls.get(job_type)
        return definition.handler if definition else None

    @classmethod
    def list_types(cls) -> list[str]:
        return list(cls._definitions.keys())

    @classmethod
    def list_definitions(cls) -> list[JobDefinition]:
        return list(cls._definitions.values())
