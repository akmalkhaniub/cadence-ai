import logging
from typing import Optional, List
from app.config import settings

logger = logging.getLogger(__name__)

def get_langfuse_callback(tenant_id: str, session_id: str, tags: Optional[List[str]] = None):
    """
    Initializes Langfuse CallbackHandler if credentials exist;
    otherwise falls back gracefully with a no-op handler.
    """
    if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
        try:
            from langfuse.callback import CallbackHandler
            return CallbackHandler(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_HOST,
                user_id=tenant_id,
                session_id=session_id,
                tags=tags or ["cadence", settings.ENVIRONMENT]
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse callback: {e}")
            return None
    return None
