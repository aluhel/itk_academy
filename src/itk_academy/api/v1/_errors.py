from typing import NoReturn

from fastapi import HTTPException, status

from itk_academy.events_provider.exceptions import (
    EventsProviderBadRequestError,
    EventsProviderError,
    EventsProviderNotFoundError,
    EventsProviderRateLimitError,
)


def raise_http_for_provider_error(exc: EventsProviderError) -> NoReturn:
    """Map EventsProviderError to the corresponding HTTPException.

    Never returns — always raises. The `NoReturn` return type makes that
    explicit for type checkers and callers.
    """
    if isinstance(exc, EventsProviderNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    if isinstance(exc, EventsProviderBadRequestError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    if isinstance(exc, EventsProviderRateLimitError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Events provider rate limit exceeded",
            headers={"Retry-After": "5"},
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Events provider unavailable",
    ) from exc
