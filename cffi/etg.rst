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
        void SomeMethod(const SomeObject *obj = NULL) const;
        void SomeOutMethod(SomeObject /Out/ *obj) const;
    """)

Can be replaced by:

::

    c.addMethod('void', 'SomeMethod', '(const SomeObject *obj = NULL)',
                isConst=True)
    c.addMethod('void', 'SomeOutMethod',
                ArgsString('(SomeObject *obj)').annt(0, 'out'), isConst=True)


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
Some of these simply involve replacing a ``CppMethoDef_sip`` with a
``CppMethodDef``. Any function that code that uses the CPython's C-API directly
or takes a ``PyObject*`` parameters must be replaced with a
``CppMethoDef_cffi``. ``CppMethoDef_cffi`` is a cffi backend specific
declaration type. It allows custom Python body code to be specified in addition
to C++ code.

The attributes of a ``CppMethodDef_cffi`` are documented in the class
defination in etgtools/extractors.py. Some additional notes: Inside the Python
body, the variable ``call``, which is set before body code, aliases the C
function cffi name so that knowing the mangled name for the method isn't
necessary. Inside the body of a constructor, ``wrapper_lib.init_wrapper``
should be used in place of ``super().__init__`` to initialize the wrapper
object. Inside of C body code, the ``WL_CLASS_NAME`` macro can be used to get
the name of the generated subclass. If one wasn't generate, then it will refer
to the name of the original class. Inside of the virtual handler C code, the
macro ``call`` aliases the callback to the Python virtual handler code.

Note that code that only uses the exception part of the Python C-API doesn't
need to be replaced. Since some way of setting exceptions from C++ is needed
(wxWidget assertion failures result in Python exceptions), to simplify things
and decrease the amount of that needed to replaced, the Python exception API is
(partially) copied. If you encounter some part of it that isn't implemented, it
should be added to ``src/cffi/wxpy_api.h``.


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

``placeHolder``
  A dummy value used to support defaults. It should be of the same type as
  ``cType`` and be inexpensive to create. For example, if the ``cType`` is
  ``long long``, 0 would be a fine value. The default is ``ffi.NULL`` since it
  is assumed many mapped types will use pointers.

``instanceCheck``
  Code that checks if a Python object meets the criteria to
  be converted into the given C++ types. This should return True or False.

``py2c``
  Code that converts a Python object into the intermediary C type.

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
and ``instanceCheck_cffi``. The former should perform the conversion and return
the new, wrapped instance. The latter should return True if the object can be
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

``wrapper_lib.get_ptr(obj, cls=None)``
  Returns the address of a wrapped object. If ``cls`` is provided, the address
  is is the address of the object aftering being cast to  the given class. If
  the object is not an instance of ``cls``, the original pointer of the ``obj``
  will be returned.

``wrapper_lib.obj_from_ptr(ptr, cls=CppWrapper, is_new=False)``
  Returns a wrapper object for the given pointer. If a wrapper object already
  exists for the pointer, that object is returned. If an wrapper does not
  already exist, the type passed as the ``cls`` argument is the used to create
  a new wrapper object, which is return.

``wrapper_lib.take_ownership(obj)``
  Makes the passed wrapper object owned by Python, which is to say that when
  the wrapper is garbage collected, the underlying C++ object is deleted too.

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

``wrapper_lib.check_exception()``
  Checks for an exception set in C++ code. This should follow most calls to C++
  code, though potentially following cleanup code for the call.

``wrapper_lib.instancecheck(obj, cls)``
  Checks if ``obj`` is an wrapper for an instance of ``cls`` or is a Python
  object that can be converted to an instance of ``cls``.

``wrapper_lib.convert_to_type(obj, cls)``
  Converts ``obj`` to an instance of ``cls`` and returns it if possible. If the
  conversion is not possible, returns ``None``.

``wrapper_lib.init_wrapper(obj, ptr, is_subclass)``
  Method to call in a custom ``__init__`` in place of calling
  ``super().__init__`` (which would have unexpected side-effects.) ``self``
  should be passed obj ``obj`` and the pointer created by the C++ component
  of the constructor. ``is_subclass`` is used to indicate if the object is an
  instance of the generate C++ subclass or of the original class. If the object
  was created using the ``WL_CLASS_NAME`` macro, then
  ``wrapper_lib.hassubclass(type(self))`` may be used.

``wrapper_lib.hassubclass(cls)``
  Returns True if a C++ subclass was generated for a class.

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
