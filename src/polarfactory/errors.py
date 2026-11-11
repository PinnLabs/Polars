class PolarFactoryError(TypeError):
    """Base class for every error raised by polarfactory."""


class GenerationError(PolarFactoryError):
    """A field value could not be generated."""
