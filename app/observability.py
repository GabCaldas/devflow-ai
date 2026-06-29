from app.config import settings

_enabled = bool(settings.langfuse_public_key and settings.langfuse_secret_key)

if _enabled:
    from langfuse import Langfuse, get_client
    from langfuse import observe as _observe

    Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )
    _client = get_client()
    observe = _observe

    def record_generation(**kwargs) -> None:
        try:
            _client.update_current_generation(**kwargs)
        except Exception:
            pass

    def flush() -> None:
        try:
            _client.flush()
        except Exception:
            pass

else:

    def observe(func=None, **_kwargs):
        def wrap(f):
            return f

        return wrap(func) if func else wrap

    def record_generation(**_kwargs) -> None:
        pass

    def flush() -> None:
        pass
