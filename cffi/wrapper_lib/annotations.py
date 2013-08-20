from cppwrapper import get_ptr
import collections

def array(seq, array_func, assign_func, map_py2c=get_ptr):
    if not isinstance(seq, collections.Sequence):
        raise TypeError("'seq' parameter must be a sequence")
    seq_len = len(seq)
    array = array_func(seq_len)
    for i in range(seq_len):
        assign_func(array, i, map_py2c(seq[i]))

    return array, seq_len
