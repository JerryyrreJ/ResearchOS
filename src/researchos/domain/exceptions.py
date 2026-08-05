class ResearchOSError(Exception):
    """Base error for expected ResearchOS failures."""


class UploadTooLargeError(ResearchOSError):
    pass


class UnsupportedFormatError(ResearchOSError):
    pass


class UnsupportedContentError(ResearchOSError):
    pass


class InvariantViolationError(ResearchOSError):
    pass


class NotFoundError(ResearchOSError):
    pass
