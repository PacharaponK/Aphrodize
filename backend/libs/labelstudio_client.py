from label_studio_sdk import LabelStudio

from backend.core.config import settings


def get_label_studio_client() -> LabelStudio | None:
    """Return an SDK client only when an API key is configured."""
    # Use the token for the running instance; annotation_service selects the project.
    if not settings.label_studio_api_key:
        # Callers can distinguish a missing configuration from an SDK request failure.
        return None
    return LabelStudio(base_url=settings.label_studio_url, api_key=settings.label_studio_api_key)
