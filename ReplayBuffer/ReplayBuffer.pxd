from libcpp.vector cimport vector

cdef extern from "<tuple>" namespace "std" nogil:
  cdef cppclass tuple[T1,T2,T3,T4]:
    tuple(T1,T2,T3,T4) except +


cdef extern from "ReplayBuffer.hh" namespace "ymd":
  cdef cppclass ReplayBuffer:
    ReplayBuffer(size_t)
    void add(vector[double],vector[double],double,vector[double],bool)
    tuple[vector[vector[double]],vector[vector[double]],vector[double],vector[vector],vecto[bool]] sample(size_t)
