from ..base import CppObject, ItemFlags, TypeInfo
from ..basictype import VoidType

from ..wrappedtype import WrappedType
from ..mappedtype import MappedType

from .. import utils
from ..utils import nci

from ... import extractors

class Param(object):
    # This needs to be a global variable because to avoid collisions of keepref
    # indices. Technically the indices need only be kept track of for a given
    # class hierarchy instead of for a whole module, but this is simplier.
    current_keepref_index = -2

    def __init__(self, param, func):
        self.name = param.name
        if not param.name:
            # Invent a name for parameters not named in the interface.
            self.name = '_x%d' % func.item.items.index(param)
        self.item = param
        self.default = param.default
        self.flags = ItemFlags(param)

        self.func = func
        self.scope = func.parent

        if self.flags.keepref:
            self.keepref_index = Param.current_keepref_index
            Param.current_keepref_index -= 1

        if self.default:
            self.default_bit_index = func.current_default_bit_index
            func.current_default_bit_index <<= 1

        if self.flags.arraysize:
            self.name = TypeInfo.ARRAY_SIZE_PARAM

    def setup(self):
        self.type = TypeInfo(self.scope, self.item.type, self.flags)

        # Defaults are printed in a function in the global namespace. If the
        # default value refers to a variable by an less than fully-qualified
        # name, we'll get a compiler error, even though the original header
        # code was semantically correct. To get around this, we'll attempt to
        # locate the variables and use their fully-qualified names.
        # Sip does some amount expression analysis of defaults as well. Adding
        # that may be necessary later, but for now, I'm content requiring users
        # to re-write a some of thier more complex defaults.
        default_obj = self.scope.getobject(self.default)
        if default_obj is not None:
            self.default = default_obj.unscopedname

        if self.flags.arraysize:
            array_param = [p for p in self.func.params if p.flags.array][0]
            self.array_param_name = array_param.name

    def print_call_cdef_setup(self, pyfile, indent):
        conversion = self.type.call_cdef_param_setup(self.name)

        can_be_default = self.default and not self.flags.out

        if can_be_default:
            name = self.name
            if self.flags.arraysize:
                name = self.array_param_name
            pyfile.write(nci("""\
            if {1} is wrapper_lib.default_arg_indicator:
                defaults_bitflags |= {0.default_bit_index}
                {0.name}{2.CFFI_PARAM_SUFFIX} = {0.type.default_placeholder}
            """.format(self, name, TypeInfo), indent + 4))

        if conversion is not None and can_be_default:
            pyfile.write(nci('else:', indent + 4))

        if conversion is not None:
            pyfile.write(nci(
                conversion, indent + 4 + 4 * int(bool(can_be_default))))

    def print_type_check(self, pyfile, indent):
        if self.flags.arraysize or self.flags.out:
            return
        pyfile.write(nci(
            "wrapper_lib.check_arg_type('{0.name}', {0.type.py_type}, {0.name})"
            .format(self), indent))

    def __eq__(self, other):
        return self.type == other.type

class SelfParam(Param):
    def __init__(self, method):
        self.name = 'self'
        self.default = ''
        self.flags = method.parent.flags

        self.method = method

    def setup(self):
        typename = (('const ' if self.method.const else '') +
                    self.method.parent.unscopedname + '*')
        self.type = TypeInfo(self.method.parent.parent, typename, self.flags)

        assert isinstance(self.type.type, WrappedType)

    def print_call_cdef_setup(self, pyfile, indent):
        conversion = self.type.call_cdef_param_setup(self.name)
        if conversion is not None:
            pyfile.write(nci(conversion, indent + 4))

    def print_type_check(self, pyfile, indent):
        pass

    def __eq__(self, other):
        return isinstance(other, SelfParam)

class void_args_string(object):
    def __init__(self, func):
        self.builder = func

    def __get__(self, func, cls=None):
        args = list(self.builder(func))
        if len(args) == 0:
            return '(void)'
        else:
            return '(' + ', '.join(args) + ')'

class args_string(object):
    def __init__(self, func):
        self.builder = func

    def __get__(self, func, cls=None):
        if func is None:
            return self.builder
        return '(' + ', '.join(self.builder(func)) + ')'

class OverloadManager(object):
    _cache = {}
    def __new__(cls, func):
        key = (func.parent, func.pyname)
        try:
            return cls._cache[key]
        except KeyError:
            pass

        newobj = super(OverloadManager, cls).__new__(cls)
        cls._cache[key] = newobj
        newobj.functions = []
        return newobj

    def __init__(self, func):
        self.functions.append(func)
        func.cname = func.cname + '__overload%d' % len(self.functions)

    @utils.call_once
    def print_pycode(self, pyfile, indent):
        pyname = self.functions[0].pyname
        pyfile.write(nci("def %s(*args, **kwargs):" % pyname, indent))

        # Print the docstring of every overload joined together
        docs = [nci(func.docstring) for func in self.functions]
        self.docstring = ''.join(docs)
        utils.print_docstring(self, pyfile, indent + 4)

        pyfile.write(nci("error_list = []", indent + 4))

        for func in self.functions:
            func.print_actual_pycode(pyfile, indent + 4)
            pyfile.write(nci("""\
            try:
                return %s(*args, **kwargs)
            except (TypeError, wrapper_lib.MMTypeError) as e:
                error_list.append(e)
            except wrapper_lib.MMInternalError as e:
                raise e.exception
            """ % pyname, indent + 4))

        pyfile.write(nci("wrapper_lib.raise_mm_arg_failure(error_list)",
                        indent + 4))

    def is_overloaded(self):
        return len(self.functions) > 1

class FunctionBase(CppObject):
    WRAPPER_NAME = 'WrappedUserCppCode::exec'
    OVERLOAD_MANAGER = OverloadManager
    def __init__(self, func, parent):
        super(FunctionBase, self).__init__(func, parent)
        self.func = func
        self.cname = self.PREFIX + self.cname

        self.current_default_bit_index = 1
        self.params = [Param(p, self) for p in self.item.items]

        try:
            self.cppcode = func.cppCode[0]
            self.original_wrapper_types = func.cppCode[1] == 'original_types'
        except (AttributeError, TypeError):
            self.cppcode = None
            self.original_wrapper_types = False

        # Flags for handling ownership transfering
        self.ownership_transfer_name = 'None'
        self.keepref_on_object = False
        self.return_has_external_ref = False
        if self.flags.factory:
            self.ownership_transfer_name = 'creturnval'
            self.keepref_on_object = True

        self.docstring = utils.fix_docstring(self.item.briefDoc)

        for o in func.overloads:
            o.generate(parent)

    def setup(self):
        self.type = TypeInfo(self.parent, self.item.type, self.flags)

        self.overload_manager = self.OVERLOAD_MANAGER(self)

        for param in self.params:
            param.setup()

    @args_string
    def c_args(self):
        if self.has_default_args():
            yield 'int defaults_bitflags'
        for param in self.params:
            yield " ".join((param.type.c_type, param.name))

    @void_args_string
    def cdef_args(self):
        if self.has_default_args():
            yield 'int defaults_bitflags'
        for param in self.params:
            yield param.type.cdef_type

    @args_string
    def cpp_args(self):
        for param in self.params:
            if isinstance(param, SelfParam):
                continue
            yield " ".join((param.type.original, param.name))

    @args_string
    def py_args(self):
        for param in self.params:
            if param.flags.arraysize or param.flags.out:
                continue
            if not param.default:
                yield param.name
            else:
                yield param.name + '=wrapper_lib.default_arg_indicator'

    @property
    def wrapper_type_attr(self):
        if self.original_wrapper_types:
            return 'cpp_type'
        else:
            return 'wrapper_type'

    @property
    def wrapper_call_code(self):
        call = '{0.WRAPPER_NAME}{0.call_wrapper_args}'.format(self)
        if not self.original_wrapper_types:
            call = self.type.user_cpp_return(call)
        return call

    @property
    def deprecated_msg(self):
        return "%s() is deprecated" % self.name

    @args_string
    def wrapper_args(self):
        for param in self.params:
            yield " ".join((getattr(param.type, self.wrapper_type_attr),
                            param.name))

    @args_string
    def call_wrapper_args(self):
        for param in self.params:
            code = param.type.call_cpp_param_inline(param.name)
            if not self.original_wrapper_types:
                code = param.type.user_cpp_param_inline(code)
            yield code

    @args_string
    def call_cdef_args(self):
        if self.has_default_args():
            yield 'defaults_bitflags'
        for param in self.params:
            yield param.type.call_cdef_param_inline(param.name)

    @args_string
    def call_cpp_args(self):
        default_count = 1
        for param in self.params:
            if isinstance(param, SelfParam) and not self.cppcode:
                continue
            if param.default:
                yield 'defaults_bitflags & %d ? (%s)(%s) : %s' % (
                    default_count, param.type.cpp_type, param.default,
                    param.type.call_cpp_param_inline(param.name))
                default_count <<= 1
            else:
                yield param.type.call_cpp_param_inline(param.name)

    @args_string
    def call_original_cpp_args(self):
        for param in self.params:
            if isinstance(param, SelfParam):
                continue
            yield param.name

    @property
    def call_cpp_code(self):
        pass


    def has_default_args(self):
        return any(bool(p.default) for p in self.params)

    def print_cdef_and_verify(self, pyfile):
        pyfile.write("{0.type.cdef_type} {0.cname}{0.cdef_args};\n".format(self))


    def print_pycode_header(self, pyfile, indent):
        pyfile.write(nci("def {0.pyname}{0.py_args}:".format(self), indent))

        for param in self.params:
            param.print_type_check(pyfile, indent + 4)

    def print_pycode_setup(self, pyfile, indent):
        if self.has_default_args():
            pyfile.write(nci('defaults_bitflags = 0', indent + 4))

        for param in self.params:
            param.print_call_cdef_setup(pyfile, indent)

    def print_pycode_call(self, pyfile, indent):
        pyfile.write(' ' * (indent + 4));
        if not isinstance(self.type.type, VoidType):
            pyfile.write('creturnval = '.format(self))

        call = 'clib.{0.cname}{0.call_cdef_args}'.format(self)
        pyfile.write(self.type.convert_variable_c_to_py(call) + '\n')

    def print_pycode_cleanup(self, pyfile, indent):
        for param in self.params:
            conversion = param.type.call_cdef_param_cleanup(param.name)
            if conversion is not None:
                pyfile.write(nci(conversion, 4))

    def print_pycode_ownership_transfer(self, pyfile, indent):
        # Handle owership of parameters
        # This loop needs to be limited to wrapped types because transfer can
        # be applied to a mapped type, where it has a very different meaning.
        for param in [p for p in self.params if isinstance(p.type.type, WrappedType)]:
            if param.flags.keepref:
                key = 'None'
                if self.keepref_on_object:
                    key = int(param.keepref_index)
                pyfile.write(nci(
                    "wrapper_lib.keep_reference(%s, key=%s, owner=%s)" %
                    (param.name, key, self.ownership_transfer_name), indent + 4))

            if param.flags.transfer and not param.flags.array:
                # Note that transfer + array has a very different meaning
                code = "wrapper_lib.give_ownership({0}, {1})"
                if param.default:
                    code = "if {0} is not wrapper_lib.default_arg_indicator: " + code
                pyfile.write(nci(code.format(param.name,
                                             self.ownership_transfer_name),
                                 indent + 4))
            if param.flags.transfer_back:
                pyfile.write(nci("wrapper_lib.take_ownership(%s)" %
                                 param.name, indent + 4))
            if param.flags.transfer_this:
                pyfile.write(nci("""\
                if {0} is None:
                    wrapper_lib.take_ownership({1})
                else:
                    wrapper_lib.give_ownership({1}, {0})"""
                .format(param.name, self.ownership_transfer_name), indent + 4))

        # Handle ownership of return values
        if self.flags.transfer_back:
            pyfile.write(nci("wrapper_lib.take_ownership(creturnval)",
                             indent + 4))
        if self.flags.factory:
            pyfile.write(nci("wrapper_lib.take_ownership(creturnval)", indent + 4))

    def print_pycode_return(self, pyfile, indent):
        outvars = []
        if not isinstance(self.type.type, VoidType):
            outvars.append('creturnval')
        for param in self.params:
            if param.flags.out or param.flags.inout:
                outvars.append(param.type.convert_variable_c_to_py(param.name))
        if len(outvars) > 0:
            pyfile.write(nci('return (%s)' % ','.join(outvars), indent + 4))

    def print_actual_pycode(self, pyfile, indent=0):
        self.print_pycode_header(pyfile, indent)

        pyfile.write(nci("try:", indent + 4))

        self.print_pycode_setup(pyfile, indent + 4)
        self.print_pycode_call(pyfile, indent + 4)
        self.print_pycode_cleanup(pyfile, indent + 4)
        self.print_pycode_ownership_transfer(pyfile, indent + 4)

        if self.flags.deprecated:
            pyfile.write(nci("wrapper_lib.deprecated_msg('%s')" %
                             self.deprecated_msg, indent + 8))

        # XXX Is this the correct place to check for exceptions? Should it
        #     happen sooner?
        pyfile.write(nci("wrapper_lib.check_exception(clib)", indent + 8))

        self.print_pycode_return(pyfile, indent + 4)

        # Wrap any exceptions that occur within the method body so that
        # errors within this block will be visible instead of looking like an
        # overloaded resolution failure.
        pyfile.write(nci("""\
        except Exception as e:
            raise wrapper_lib.MMInternalError(e)
        """, indent + 4))


    def print_pycode(self, pyfile, indent=0):
        # The overload manager will call print_actual_pycode for each overload.
        # It also will not be printed more than once.
        self.overload_manager.print_pycode(pyfile, indent)


    def print_cppcode(self, cppfile):
        cppfile.write(nci("""\
        WL_C_INTERNAL {0.type.c_type} {0.cname}{0.c_args}
        {{""".format(self)))

        if self.cppcode:
            self.print_wrapper(cppfile)

        for param in self.params:
            conversion = param.type.call_cpp_param_setup(param.name)
            if conversion is not None:
                cppfile.write(nci(conversion, 4))

        cppfile.write(nci(self.call_cpp_code, 4))

        for param in self.params:
            conversion = param.type.call_cpp_param_cleanup(param.name)
            if conversion is not None:
                cppfile.write(nci(conversion, 4))

        if not isinstance(self.type.type, VoidType):
            cppfile.write('    return %s;\n' %
                           self.type.convert_variable_cpp_to_c('cppreturnval'))

        cppfile.write('}\n\n')

    def print_wrapper(self, cppfile):
        wrapper_type = getattr(self.type, self.wrapper_type_attr)
        cppfile.write(nci("""\
        struct WrappedUserCppCode
        {{
            inline static {1} exec{0.wrapper_args}
            {{
        """.format(self, wrapper_type), 4))

        cppfile.write(nci(self.cppcode, 12))

        cppfile.write("""\
        }
    };\n""")

