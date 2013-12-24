import functools

from ..generators import nci

def call_once(func):
    @functools.wraps(func)
    def first(self, *args, **kwargs):
        setattr(self, func.__name__, after)
        return func(self, *args, **kwargs)

    @functools.wraps(func)
    def after(*args, **kwargs):
        pass

    return first

def pad(f):
    f.write('\n')

def print_docstring(obj, file, indent):
    file.write(nci('"""', indent))

    if obj.docstring:
        file.write(nci(obj.docstring, indent))

    file.write(nci('"""', indent))
