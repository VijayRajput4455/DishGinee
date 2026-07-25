import uuid
from contextvars import ContextVar

_request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def set_request_id(request_id: str | None = None) -> str:
    """Store given request_id in context, generating a new UUID string if absent."""
    rid = request_id or str(uuid.uuid4())
    _request_id_var.set(rid)
    return rid


def get_request_id() -> str:
    """Retrieve the current context request_id."""
    return _request_id_var.get()
