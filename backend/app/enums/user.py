from enum import Enum

class UserRole(str, Enum):
    USER = "user"
    REVIEWER = "reviewer"
