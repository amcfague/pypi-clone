class PypiCloneException(Exception):
    pass


class LocalException(PypiCloneException):
    pass


class FileAlreadyExistsException(LocalException):
    pass


class FileDoesNotExistException(LocalException):
    pass


class RemoteException(PypiCloneException):
    pass


class ImmutableException(RemoteException):
    """ Raised when attempting to write a read-only property. """
    pass
