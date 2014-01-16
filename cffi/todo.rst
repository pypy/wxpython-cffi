=====
To Do
=====

Items below are some problems with the binding generator that have yet to be
addressed. They are ordered approximately by importance.


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
