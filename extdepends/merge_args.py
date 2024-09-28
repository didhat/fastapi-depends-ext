import inspect
import itertools
import types
import functools
import sys
import typing

__all__ = ('merge_args',)

PY38 = sys.version_info >= (3, 8)
PY310 = sys.version_info >= (3, 10)
PY311 = sys.version_info >= (3, 11)


# Coping and adapted from https://github.com/Kwpolska/merge_args, really nice hack for merging signatures of two
# functions


def _blank():  # pragma: no cover
    pass


def _merge(
        source,
        dest,
        drop_args: typing.Optional[typing.List[str]] = None,
        drop_kwonlyargs: typing.Optional[typing.List[str]] = None,
):
    """Merge the signatures of ``source`` and ``dest``.

    ``dest`` args go before ``source`` args in all three categories
    (positional, keyword-maybe, keyword-only).
    """
    if drop_args is None:
        drop_args = []
    if drop_kwonlyargs is None:
        drop_kwonlyargs = []

    source = _get_original_function(source) # for unwrapping original function with Depends

    source_spec = inspect.getfullargspec(source)
    dest_spec = inspect.getfullargspec(dest)

    if source_spec.varargs or source_spec.varkw:
        raise ValueError("The source function may not take variable arguments.")

    source_all = source_spec.args
    dest_all = dest_spec.args

    if source_spec.defaults:
        source_pos = source_all[:-len(source_spec.defaults)]
        source_kw = source_all[-len(source_spec.defaults):]
    else:
        source_pos = source_all
        source_kw = []

    if dest_spec.defaults:
        dest_pos = dest_all[:-len(dest_spec.defaults)]
        dest_kw = dest_all[-len(dest_spec.defaults):]
    else:
        dest_pos = dest_all
        dest_kw = []

    args_merged = dest_pos
    for a in source_pos:
        if a not in args_merged and a not in drop_args:
            args_merged.append(a)

    defaults_merged = []
    for a, default in itertools.chain(
            zip(dest_kw, dest_spec.defaults or []),
            zip(source_kw, source_spec.defaults or [])
    ):
        if a not in args_merged and a not in drop_args:
            args_merged.append(a)
            defaults_merged.append(default)

    kwonlyargs_merged = dest_spec.kwonlyargs
    for a in source_spec.kwonlyargs:
        if a not in kwonlyargs_merged and a not in drop_kwonlyargs:
            kwonlyargs_merged.append(a)

    args_all = tuple(args_merged + kwonlyargs_merged)

    if PY38:
        replace_kwargs = {
            'co_argcount': len(args_merged),
            'co_kwonlyargcount': len(kwonlyargs_merged),
            'co_posonlyargcount': dest.__code__.co_posonlyargcount,
            'co_nlocals': len(args_all),
            'co_flags': source.__code__.co_flags,
            'co_varnames': args_all,
            'co_filename': dest.__code__.co_filename,
            'co_name': dest.__code__.co_name,
            'co_firstlineno': dest.__code__.co_firstlineno,
        }

        if PY310:
            replace_kwargs['co_linetable'] = dest.__code__.co_linetable
        else:
            replace_kwargs['co_lnotab'] = dest.__code__.co_lnotab

        if PY311:
            replace_kwargs['co_exceptiontable'] = dest.__code__.co_exceptiontable
            replace_kwargs['co_qualname'] = dest.__code__.co_qualname

        passer_code = _blank.__code__.replace(**replace_kwargs)
    else:
        passer_args = [
            len(args_merged),
            len(kwonlyargs_merged),
            _blank.__code__.co_nlocals,
            _blank.__code__.co_stacksize,
            source.__code__.co_flags,
            _blank.__code__.co_code, (), (),
            args_all, dest.__code__.co_filename,
            dest.__code__.co_name,
            dest.__code__.co_firstlineno,
            dest.__code__.co_lnotab,
        ]
        passer_code = types.CodeType(*passer_args)

    passer = types.FunctionType(passer_code, globals())
    dest.__wrapped__ = passer

    # annotations

    # ensure we take destination’s return annotation
    has_dest_ret = 'return' in dest.__annotations__
    if has_dest_ret:
        dest_ret = dest.__annotations__['return']

    for v in ('__kwdefaults__', '__annotations__'):
        out = getattr(source, v)
        if out is None:
            out = {}
        if getattr(dest, v) is not None:
            out = out.copy()
            out.update(getattr(dest, v))
            setattr(passer, v, out)

    if has_dest_ret:
        passer.__annotations__['return'] = dest_ret
    dest.__annotations__ = passer.__annotations__

    passer.__defaults__ = tuple(defaults_merged)
    if not dest.__doc__:
        dest.__doc__ = source.__doc__
    return dest


def _get_original_function(func):
    while func.__dict__.get("__wrapped__") is not None:
        func = func.__dict__.get("__wrapped__")
    return func


def merge_args(
        source,
        drop_args: typing.Optional[typing.List[str]] = None,
        drop_kwonlyargs: typing.Optional[typing.List[str]] = None,
):
    """Merge the signatures of two functions."""
    return functools.partial(
        lambda x, y: _merge(x, y, drop_args, drop_kwonlyargs), source
    )
