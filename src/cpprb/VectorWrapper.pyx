# distutils: language = c++
# cython: linetrace=True

cimport numpy as np
import numpy as np

from libc.stdlib cimport malloc, free
from cython.operator cimport dereference
import cython

cdef class VectorWrapper:
    def __cinit__(self,ndim=1,value_dim=1,**kwarg):
        self.ndim = min(ndim,2)
        self.value_dim = value_dim

        self.shape   = <Py_ssize_t*>malloc(sizeof(Py_ssize_t) * self.ndim)
        self.strides = <Py_ssize_t*>malloc(sizeof(Py_ssize_t) * self.ndim)

    def __reduce__(self):
        return (self.__class__, (self.ndim,self.value_dim))

    cdef void update_size(self):
        self.shape[0] = <Py_ssize_t>(self.vec_size()//self.value_dim)

    cdef void set_buffer(self,Py_buffer* buffer):
        raise NotImplementedError()

    cdef void set_shape_strides(self):
        self.strides[self.ndim -1] = self.itemsize

        if self.ndim == 2:
            self.shape[1] = <Py_ssize_t> (self.value_dim)
            self.strides[0] = self.value_dim * self.itemsize

    cpdef size_t vec_size(self):
        raise NotImplementedError()

    def __dealloc__(self):
        free(self.shape)
        free(self.strides)

    def __getbuffer__(self, Py_buffer *buffer, int flags):
        self.update_size()

        self.set_buffer(buffer)
        buffer.len = self.vec_size() * self.itemsize
        buffer.readonly = 0
        buffer.ndim = self.ndim
        buffer.shape = self.shape
        buffer.strides = self.strides
        buffer.suboffsets = NULL
        buffer.itemsize = self.itemsize
        buffer.internal = NULL
        buffer.obj = self

    def __releasebuffer__(self, Py_buffer *buffer):
        pass

    def as_numpy(self,copy = False,**kwargs):
        return np.array(self,copy=copy,**kwargs)

cdef class VectorInt(VectorWrapper):
    def __cinit__(self,ndim=1,value_dim=1,**kwargs):
        self.vec = vector[int]()
        self.itemsize = sizeof(int)
        self.set_shape_strides()

    cdef void set_buffer(self,Py_buffer* buffer):
        buffer.buf = <void*>(self.vec.data())
        buffer.format = 'i'

    cpdef size_t vec_size(self):
        return self.vec.size()

cdef class VectorDouble(VectorWrapper):
    def __cinit__(self,ndim=1,value_dim=1,**kwargs):
        self.vec = vector[double]()
        self.itemsize = sizeof(double)
        self.set_shape_strides()

    cdef void set_buffer(self,Py_buffer* buffer):
        buffer.buf = <void*>(self.vec.data())
        buffer.format = 'd'

    cpdef size_t vec_size(self):
        return self.vec.size()

cdef class VectorFloat(VectorWrapper):
    def __cinit__(self,ndim=1,value_dim=1,**kwargs):
        self.vec = vector[float]()
        self.itemsize = sizeof(float)
        self.set_shape_strides()

    cdef void set_buffer(self,Py_buffer* buffer):
        buffer.buf = <void*>(self.vec.data())
        buffer.format = 'f'

    cpdef size_t vec_size(self):
        return self.vec.size()

cdef class VectorSize_t(VectorWrapper):
    def __cinit__(self,ndim=1,value_dim=1,**kwargs):
        self.vec = vector[size_t]()
        self.itemsize = sizeof(size_t)
        self.set_shape_strides()

    cdef void set_buffer(self,Py_buffer* buffer):
        buffer.buf = <void*>(self.vec.data())
        if sizeof(size_t) == sizeof(unsigned long):
            buffer.format = 'L'
        elif sizeof(size_t) == sizeof(unsigned long long):
            buffer.format = 'Q'
        elif sizeof(size_t) == sizeof(unsigned int):
            buffer.format = 'I'
        elif sizeof(size_t) == sizeof(unsigned char):
            buffer.format = 'B'
        else:
            raise BufferError("Unknown size_t implementation!")

    cpdef size_t vec_size(self):
        return self.vec.size()

cdef class PointerDouble(VectorWrapper):
    def __cinit__(self,ndim=1,value_dim=1,size=1,**kwargs):
        self._vec_size = value_dim * size
        self.itemsize = sizeof(double)
        self.set_shape_strides()

    def __reduce__(self):
        return (self.__class__,
                (self.ndim,self.value_dim,self._vec_size // self.value_dim))

    cdef void set_buffer(self,Py_buffer* buffer):
        buffer.buf = <void*> self.ptr
        buffer.format = 'd'

    cdef void update_vec_size(self,size_t size):
        self._vec_size = self.value_dim * size

    cpdef size_t vec_size(self):
        return self._vec_size
