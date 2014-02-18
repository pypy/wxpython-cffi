import warnings

def deprecated_msg(message):
    warnings.warn(message, category=DeprecationWarning, stacklevel=3)

