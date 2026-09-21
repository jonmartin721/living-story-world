"""Reserve a world across awaits in the local, single-process API server."""

from contextlib import contextmanager
from uuid import uuid4

from fastapi import HTTPException

active_world_operations: dict[str, str] = {}


def check_world_idle(slug: str) -> None:
    operation = active_world_operations.get(slug)
    if operation:
        raise HTTPException(
            status_code=409,
            detail={
                "error": f"An operation is already running for '{slug}'.",
                "job_id": operation,
            },
        )


@contextmanager
def world_operation(slug: str):
    # There is no await between checking and reserving the slot.
    check_world_idle(slug)
    token = str(uuid4())
    active_world_operations[slug] = token
    try:
        yield
    finally:
        if active_world_operations.get(slug) == token:
            active_world_operations.pop(slug, None)
