from typing import Optional

class CommittableException(Exception):
    def __init__(self, message: Optional[str] = None, cause: Optional[Exception] = None):
        if cause:
            self.__cause__ = cause

        self.cause = self.__cause__
        self.message = message or f"CommitableException: cause={self.cause}"
        super().__init__(self.message)

    def __str__(self):
        return self.message
