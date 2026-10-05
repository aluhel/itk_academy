from enum import StrEnum


class EventStatus(StrEnum):
    NEW = "new"
    PUBLISHED = "published"
    REGISTRATION_CLOSED = "registration_closed"


class SyncStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
