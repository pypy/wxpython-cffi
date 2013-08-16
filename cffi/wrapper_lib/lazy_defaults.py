class LD(str):
    """
    Simple wrapper to indicate which arguments should be lazy evaluated
    """
    pass

def eval_func_defaults(func):
    if getattr(func, 'func_defaults', None) is not None:
        defaults = tuple(eval(d, func.func_globals) if isinstance(d, LD) else d
                     for d in func.func_defaults)
        func.func_defaults = defaults
