class NotFoundError(Exception):
    pass


class ForbiddenError(Exception):
    pass


class UnauthorizedError(Exception):
    pass


class TooManyRequestsError(Exception):
    pass
