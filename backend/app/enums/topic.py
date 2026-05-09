from enum import Enum

class TopicStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
