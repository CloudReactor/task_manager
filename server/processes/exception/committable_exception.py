

class CommittableException(Exception):
    def __init__(self, message: str | None = None, cause: Exception | None = None):
        if cause:
            self.__cause__ = cause

        self.cause = self.__cause__
        self.message = message or f"CommitableException: cause={self.cause}"
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message or '[MISSING MESSAGE]'
