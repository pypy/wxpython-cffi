=====
To Do
=====

Items below are some problems with the binding generator that have yet to be
addressed. They are ordered approximately by importance.

Re-organize
-----------

When I started writing the generator, I made the somewhat ill-informed decision
to try copy the layout of the existing generator when creating cffi binding
generator. Instead, I should have taken a more OO approach. So, do that. Also,
the naming of a number of things is inconsistent. More details here later?


Implementing automatic opaque types
-----------------------------------

Sip automatically creates opaque types for any C++ types that it encounters for
which it is provided no specification. Implementing this would make testing
converted ETG scripts easier. At the moment, if some element an ETG script
introduces uses a type added by another scripts, the bindings won't work until
the latter script is added too. Automatic opaque types would solve this
problem.


Fix inherited virtual methods
-----------------------------

Virtual methods don't inherit correctly at the moment. The primary roadblock is
figuring out how to detect when a method on a subclass is a redeclaration of a
method on the base class. Maybe look at how sip figures this out?


Fix multiple inheritance
------------------------

No special considerations are taken to convert subclass pointers to base
classes that aren't at the same address for methods declared on the base class.
Multiple inheritance is relatively uncommon in wxWidgets, but this still needs
to be fixed eventually.

Two possible strategies:

1. Pre-calculate the address offset for class to call of its base classes'
conversions and perform the pointer arithmetic in Python using cffi. Since the
vast majority of these will simply be an offset of 0, a special case can be
made to speed things up. This could hopefully also be accelerated by PyPy's
JIT.

2. Mimic sip's behavior. Each class gets a unique identifier and a
``cast_$CLASSNAME`` function. The cast function takes two parameters: a pointer
to convert and the target type. The function checks if the target type matches
the current class, and if so returns the pointer as is. Otherwise, for each of
its the class's bases, it casts the pointer to that type (offsetting correctly
in the process) and calls the base's cast function. If the function returns a
non-NULL pointer that pointer is returned. If all of the bases' functions
returned NULL (or there are no bases) a NULL is returned.

Benchmarking to compare the two options is probably in order.


Handle defaults more intelligently
----------------------------------

Defaults are handled by trying to convert a C++ default value into a default
value on the arguments of Python functions. This is actually a really bad
solution since some default values are actually expressions (``SOME_CONST |
SOME_OTHER_CONST``), some don't have a corresponding Python name, and some have
a different name. The solution is to be more like sip and assign default values
in the bodies of the ``extern "C"`` functions. Of course, we will also need a
way to let the function know which default values are being used.


Implement support for template classes and wrapped types
--------------------------------------------------------

I believe this is optional. Exactly how much support sip has for templates is
unclear. The documentation clearly states that templates are only supported for
mapped types, but the existence of ``src/arrayholder.sip`` would seem to
contradict this. Further investigation is required.


Fix the ``Array`` annotation for wrapped types
----------------------------------------------

The ``Array`` annotation for wrapped type parameters is broken at the moment.
Fixing this should be easy, but its a relatively low priority because wxPython
doesn't use ``Array`` for wrapped types at all.


Improve the generated conversion code
-------------------------------------

This can mean a couple of different things:

* The names of temporary variables used in the conversion process suck. Maybe
  come up with a good, consistent naming scheme for temporary variables?

* Lean on templates a little more heavily. The handling of when to
  de-reference could be done by templates rather than by the binding generator
  itself. This makes the generator simpler, but makes generated code harder to
  read/debug and worsens compile times.


Improve import times
--------------------

For the most part import times are out of our hands: the parsing of the
``cdef`` string takes up at least half of time spent importing the module. That
said, there is something that can be done to improve things. Like sip, the
populating of classes attribute dictionaries can be delayed until they are
accessed for the first time. At the moment, I have no idea how to actually
implement this.

