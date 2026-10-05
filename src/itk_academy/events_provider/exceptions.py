class EventsProviderError(Exception):
    """Base exception for all Events Provider client errors."""


class EventsProviderAuthError(EventsProviderError):
    """401 Unauthorized — invalid or missing API key."""


class EventsProviderNotFoundError(EventsProviderError):
    """404 Not Found."""


class EventsProviderBadRequestError(EventsProviderError):
    """400 Bad Request — business error (e.g. seat already taken)."""


class EventsProviderRateLimitError(EventsProviderError):
    """429 Too Many Requests."""


class EventsProviderServerError(EventsProviderError):
    """5xx — server-side error."""


class EventsProviderUnexpectedError(EventsProviderError):
    """Any unexpected error."""
