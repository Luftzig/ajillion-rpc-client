from requests.exceptions import HTTPError

__author__ = 'yoav.luft@ajillionmax.com'


class LoginError(HTTPError):
    """Raised if client failed to authenticate itself to the remote for any reason"""
    pass


class NoHandlerError(NotImplementedError):
    """Raised if no handler that can handle the method was found"""
    pass


class RemoteFailedError(HTTPError):
    """Raised if the remote returned an error or invalid response"""
    pass


class RemoteTimeoutError(TimeoutError):
    """Raised if connection to the remote was timed-out"""
    pass
