class LLMError(Exception):
    pass


class TimeoutError(LLMError):
    pass


class RateLimitedError(LLMError):
    pass


class InvalidRequestError(LLMError):
    pass


class AuthError(LLMError):
    pass


class ServerError(LLMError):
    pass
