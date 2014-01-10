=======================
Converting ETG scripts
=======================


Building the bindings
---------------------

Before you can begin converting ETG scripts, you need to be able to build the
binding. The building process is roughly outlined in the ``README``. A couple
of extra notes: The actual compiling takes place when you first import the
module. Also, cffi normally only recompiles when the cdefs change, so you may
have to delete the ``cffi/wx/__pycache__`` directory in order to persuade it to
recompile. It is also recommended that you read the original wxPython Phoenix
README, though its not required.


---------------
Important TODOs
---------------

Review the usage of the ``addDefaultCtor``, ``addDtor``,
``addPrivateAssignOp``, ``addPrivateCopyCtor``, ``addCopyCtor``. These affect
the visibility of items that follow them in the sip backend but don't in the
cffi backend. This may or may not be a problem. Each usage of these methods
should be investigated to make sure that they aren't causing problems/
incompatibilities.



Converting scripts
-----------------------


Unconverted ETG scripts are located in the ``etg/unfinished`` directory. 

The general process for converting the scripts are:

1. Find and unconverted script in ``etg/unfinished``, and ``hg mv`` into the
``etg`` directory.

2. Locate the script for its module and uncomment the script's name in the
modules ``INCLUDES`` list. The name of a script's module is the ``MODULE``
string near the top of the file.

3. Replace WigCode segments with manual declarations and add conversion code as
needed.

4. Determine if there is any CPython or sip specific code that needs to be
replaced. If there isn't any, then proceed to step 6.

5. Create a script in ``etg/sip`` and move all of the sip specific code to that
directory.  Create a script in ``etg/cffi`` and in it replicate the
functionality of the code that was moved into the sip script. Add both scripts
to the original scripts ``OTHERDEPS`` list (creating the list if it doesn't
exist). Add ``tools.runGeneratorSpecificScript(module)`` to original script
near the bottom but above the call to ``tools.doCommonTweaks(module)``.

6. Rerun the ETG scripts and the binding generator and then try importing the
module. The cffi backend doesn't support automatically creating opaque types at
the moment, so if something added in the new ETG script depends on a type from
another script.  A missing type will usually result in either the binding
generator throwing an exception or cffi being unable to parse a cdef.

7. Try running the unittests for the script(s) and make sure things work as
expected.. Some tests may have some CPython specific expectations (ie check
refcounts) and so may require some editing.


Template for a generator specific ETG script (a script in ``etg/sip`` or
``etg/cffi``.)

::

    import etgtools
    import etgtools.tweaker_tools as tools

    def run(module):
        # c = module.find("SomeClass")
        # ....
        pass

The ``run`` function will be called when ``tools.runGeneratorSpecificScript``
is called in the main script.
        

Replacing WigCode
-----------------

WigCode declarations are segments of 'wrapper interface generator' code (ie
sip) that are inserted directly into the output files. These segments are
meaningless for the cffi backend, which has no way to parse them. They must be
replaced with manual declarations. A simple example:

::

    c.addItem(etgtools.WigCode("""\
        void SomeMethod(const SomeObject &obj) const;
    """)

Can be replaced by:

::

    c.addMethod(
        'void', 'SomeMethod', '(const SomeObject &obj)', isConst=True,
        items=[etgtools.ParamDef(type='const SomeObject &', name='obj')])


Some things to keep in mind:

* The constructors of all the \*Def classes will add all of keyword arguments
  passed to them to the objects' attributes. This can be seen in the ``ParamDef``
  above.

* Overloaded functions have just one entry in their parent's ``items`` list.
  The overloads are placed in the ``overloads`` list of the primary overload. The
  ``addMethod`` and ``addCppMethod`` methods automatically take care of this, but
  in some circumstances you may have to handle this manually.

Additionally, the different \*Def classes and their fields are documented a
little in ``etgtools/extractors.py``.

Replacing CPython specific functions
------------------------------------

In a number places the existing ETG scripts use CPython or sip specific code.
Some of these simply involve replace a ``CppMethoDef_sip`` with
``CppMethodDef``. Any function that code that uses CPython's C-API directly or
take a ``PyObject*`` parameters must be replaced with a ``CppMethoDef_cffi``.
``CppMethoDef_cffi`` is a cffi backend specific declaration type. It differs
from the regular ``CppMethodDef`` in the following ways:

 * No automatic conversion of types takes place.

 * Instead of generating a signature for the Python method from the types of
   C++ signature, it has a ``pySignature`` attribute that is used directly.

 * It has a ``pyBody`` attribute that is used for the body of the Python
   method. The ``call`` variable in the method body is assigned the cffi function
   to call the C++ code specified by the ``body`` attribute, so you won't need to
   worry about how the name is mangled.

 * It has an optional ``pyArgs`` attribute. This attribute can be used to
   automate type-checking of parameters before they reach the code specified in
   ``pyBody``. The attribute should be a list populated with ``ParamDefs``. The
   generator will first try to look up a C++ type (wrapped or mapped) for ``type``
   attribute of the ``ParamDef`` and if it isn't able to find one, it will use
   value literally as a type. In this way, you may specify either a C++ type or a
   Python type.

 * It has an optional ``callArgs`` attribute. This is only useful if the method
   being added it a Ctor. It is used to specify the parameters to pass to the base
   class's Ctor if a subclass is going to be generated for this class (ie it has a
   virtual or a protected method.)

By combining a custom Python body and a custom C++ body, you should be able to
achieve the same effect as any ``CppMethodDef`` or ``CppMethodDef_sip``
declaration.

Note that code that only uses the exception part of the Python C-API doesn't
need to be replaced. Since some way of setting exceptions from C++ is needed
(wxWidget assertion failures result in Python exceptions), to simplify things
and decrease the amount of that needed to replaced, the Python exception API is
(partially) copied. If you encounter some part of it that isn't implemented, it
should be added to ``src/cffi/wxpy_api.h``.

Replacing virtual catcher code is a done somewhat similarly. Virtual catcher
code handles calling a Python re-implementation of a C++ virtual method. For
the cffi backend, it is pure Python code that is called in place of the actual
Python  in the usual virtual method handling process. It is also called with
the same arguments that the actual Python method would be. All C++ types are
automatically converted/wrapped (this may change in the future because it
inflexible and inconsistent with the above.) Virtual catcher code for cffi is
placed in the ``virtualCatcheCode_cffi`` attribute of a method declaration
(``MethodDef``, ``CppMethodDef``, etc.)


Adding mapped types
-------------------

There are few wrapped types and its relatively unlikely you'll have to add one,
but they're documented here for the sake of having them documented.

Mapped types are C++ types that are silently converted to/from Python types.
They are defined by five attributes:

``cType``
  A type that acts as an intermediary between Python and C++. Must
  be a type that cffi can understand. If you need a custom struct you can add it
  by using the ``cdef_cffi`` attribute of the module.

``instancecheck``
  Code that checks if a Python object meets the criteria to
  be converted into the given C++ types. This should return True or False.

``py2c``
  Code that converts a Python object into the intermediary C type.
  This should return a 2-tuple. The first element of the return value is the
  value passed to the C function. The second element is a keep-alive variable so
  that data allocated with ``ffi.new`` in this method stays in scope.

``c2cpp``
  Code that converts the intermediary C data into the final C++
  object. Should return the C++ object allocated on the heap. If ``py2c``
  allocated any memory using ``malloc`` it should be freed here.

``cpp2c``
  Code that converts a C++ object into intermediary C data.

``c2py``
  Code that converts the intermediary C data into a Python object.
  Any memory allocated in ``cpp2c`` should be freed here.


Replacing custom type conversions
---------------------------------

Some classes have custom conversion code that silently Python objects into C++
objects. An example is wx.Size, which any sequence of numbers can be converted
to. The code for the sip backend is specified in the ``convertFromPyObject``
attribute. This one block of code specifies both the code to check if a Python
object can be converted and the code to perform the conversion. For the cffi
backend this code is split up into two attributes: ``convertFromPyObject_cffi``
and ``instancecheck``. The former should perform the conversion and return the
new, wrapped instance. The latter should return True if the object can be
converted to the given C++ type, and False if not.


Functions available in handwritten Python code
----------------------------------------------

Inside the handwritten Python code you may use the ``ffi`` and ``clib``
variables to access the FFI instance and C library functions. ``clib.malloc``
and ``clib.free`` are already available, but if you need extra C standard
library functions, you can append their signatures to ``module.cdefs_cffi``,
which is a list of strings.


The ``wrapper_lib`` module is available inside hand written Python code blocks.
It provides the following functions:

``wrapper_lib.get_ptr(obj)``
  Returns the address of a wrapped object.

``wrapper_lib.obj_from_ptr(ptr, cls=CppWrapper, is_new=False)``
  Returns a wrapper object for the given pointer. If a wrapper object already
  exists for the pointer, that object is returned. If an wrapper does not
  already exist, the type passed as the ``cls`` argument is the used t

``wrapper_lib.take_ownership(obj)``
  Makes the passed wrapper object owned by Python.

``wrapper_lib.give_ownership(obj, parent=None, external_ref=False)``
  Makes the given wrapper object owned by C++, meaning its Dtor won't be called
  when the Python object is deleted. If ``parent`` is not ``None``, ``obj``
  will not be deleted until ``parent`` is deleted. If ``external_ref`` is True,
  ``obj`` will not be deleted until either its ownership is changed again or
  its Dtor is called (assuming the type being wrapped has a virtual Dtor.)

``wrapper_lib.keep_reference(obj, key=None, owner=None)``
  Creates an extra reference to ``obj``. If ``owner`` is not ``None``, then the
  reference is stored on ``owner``, keeping ``obj`` alive until either
  ``owner`` is deleted or a new object for the given key for ``owner``. Any
  value may be used for ``key``, but negative integer values are reserved by
  the implementation.  If ``owner`` is ``None`` the reference is leaked and
  ``obj`` will never be deleted.

``wrapper_lib.LD(expression)``
  LD stands for "lazy default." This can be used in the default values for
  function parameters to delay the evaluation of an expression until the whole
  module has been initialized. This must be used for any default value that
  references a wrapped variable or type. For example:
  ``def some_func(param=wrapper_lib.LD('Size(10, 10)'):``

``wrapper_lib.check_exception()``
  Checks for an exception set in C++ code. This should follow most calls to C++
  code, though potentially following cleanup code for the call.

``wrapper_lib.instancecheck(obj, cls)``
  Checks if ``obj`` is an wrapper for an instance of ``cls`` or is a Python
  object that can be converted to an instance of ``cls``.

``wrapper_lib.convert_to_type(obj, cls)``
  Converts ``obj`` to an instance of ``cls`` and returns it if possible. If the
  conversion is not possible, returns ``None``.

.. TODO: Document adjust_refcount, get_refcounted_handle


Miscellaneous
-------------

The ``pyCode_cffi`` attribute of a ClassDef can be used to specify any extra
code to be added to the Python body a class. Note this is added to the end of
the body.

If you need to locate which ETG script provides a particular class or function,
the easiest way is to grep for it in the ``sip/gen`` directory of a checkout of
upstream wxPython Phoenix. You will of course need to have run ``./build.py
etg`` in the checkout before that directory will be populated.
