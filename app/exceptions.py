class ConfigurationError(Exception):
    """
    Raised when application configuration is invalid.
    """
    pass


class DataValidationError(Exception):
    """
    Raised when received environmental data is invalid.
    """
    pass


class APIError(Exception):
    """
    Raised when an external API request fails.
    """
    pass