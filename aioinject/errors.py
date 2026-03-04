class CannotDetermineReturnTypeError(Exception):
    pass


class ProviderNotFoundError(Exception):
    pass


class ScopeNotFoundError(Exception):
    pass


class CyclicDependencyError(Exception):
    pass
