=====
To Do
=====

Items below are some problems with the binding generator that have yet to be
addressed. They are ordered approximately by importance.


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


Improve import times
--------------------

For the most part import times are out of our hands: the parsing of the
``cdef`` string takes up at least half of time spent importing the module. That
said, there is something that can be done to improve things. Like sip, the
populating of classes attribute dictionaries can be delayed until they are
accessed for the first time. At the moment, I have no idea how to actually
implement this.


Change how parent-child hierarchy is implemented
------------------------------------------------

The parent-child structure is implemented using a linked list of siblings.
PyPy's garbage collector doesn't handle that sort of structure particularly
well. Store siblings in a list instead.
