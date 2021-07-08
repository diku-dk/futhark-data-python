import io
import re
import string
import struct
import sys

import numpy as np

__all__ = ['dump', 'dumps', 'dumpb', 'load', 'loads', 'loadb']

BINARY_DATA_FORMAT_VERSION = 2

PRIMTYPES = {
    'i8':  {'binname' : b"  i8",
            'size' : 1,
            'bin_format': 'b',
            'numpy_type': np.int8 },

    'i16': {'binname' : b" i16",
            'size' : 2,
            'bin_format': 'h',
            'numpy_type': np.int16 },

    'i32': {'binname' : b" i32",
            'size' : 4,
            'bin_format': 'i',
            'numpy_type': np.int32 },

    'i64': {'binname' : b" i64",
            'size' : 8,
            'bin_format': 'q',
            'numpy_type': np.int64},

    'u8':  {'binname' : b"  u8",
            'size' : 1,
            'bin_format': 'B',
            'numpy_type': np.uint8 },

    'u16': {'binname' : b" u16",
            'size' : 2,
            'bin_format': 'H',
            'numpy_type': np.uint16 },

    'u32': {'binname' : b" u32",
            'size' : 4,
            'bin_format': 'I',
            'numpy_type': np.uint32 },

    'u64': {'binname' : b" u64",
            'size' : 8,
            'bin_format': 'Q',
            'numpy_type': np.uint64 },

    'f32': {'binname' : b" f32",
            'size' : 4,
            'bin_format': 'f',
            'numpy_type': np.float32 },

    'f64': {'binname' : b" f64",
            'size' : 8,
            'bin_format': 'd',
            'numpy_type': np.float64 },

    'bool': {'binname' : b"bool",
             'size' : 1,
             'bin_format': 'b',
             'numpy_type': np.bool8 }
}

def suffix_to_type(suffix):
    if suffix in PRIMTYPES:
        return PRIMTYPES.get(suffix)['numpy_type']

class Reader:
    def __init__(self, f):
        self.f = f
        self.lookahead_buffer = []

    def get_char(self):
        if len(self.lookahead_buffer) == 0:
            b = self.f.read(1)
            if len(b) == 0:
                return None
            elif type(b) == bytes:
                return chr(b[0])
            else:
                return b
        else:
            c = self.lookahead_buffer[0]
            self.lookahead_buffer = self.lookahead_buffer[1:]
            return c

    def unget_char(self, c):
        self.lookahead_buffer = [c] + self.lookahead_buffer

    # The latin1 stuff is misleading - we just want to treat the file
    # as both binary and text.  In practice, the input has to be
    # UTF-8.

    def get_chars(self, n):
        n1 = min(n, len(self.lookahead_buffer))
        s = ''.join(self.lookahead_buffer[:n1])
        self.lookahead_buffer = self.lookahead_buffer[n1:]
        n2 = n - n1
        if n2 > 0:
            s += self.f.read(n2).decode('latin1')
        return s

    def get_bytes(self, n):
        cs = self.get_chars(n)
        return bytes(cs, encoding='latin1')

    def peek_char(self):
        c = self.get_char()
        if c:
            self.unget_char(c)
        return c

    def skip_spaces(self):
        c = self.get_char()
        while c != None:
            if c.isspace():
                c = self.get_char()
            elif c == '-':
              # May be line comment.
              if self.peek_char() == '-':
                # Yes, line comment. Skip to end of line.
                while (c != '\n' and c != None):
                  c = self.get_char()
              else:
                break
            else:
              break
        if c:
            self.unget_char(c)

    def next_token(self):
        self.skip_spaces()
        s = ''
        while True:
            c = self.get_char()
            if c == None or c.isspace():
                break
            elif c in '()[],':
                if len(s) == 0:
                    return c
                else:
                    self.unget_char(c)
                    return s
            else:
                s += c

        if len(s) == 0:
            return None
        else:
            return s

    def unget_token(self, tok):
        self.unget_char(' ')
        for c in tok[::-1]:
            self.unget_char(c)

    _INTEGER_REGEXP = re.compile(r'(-?[0-9][0-9_]*|-?0[xX][0-9a-fA-F][0-9a-fA-F_]*|-?0b[01][01_]+)(i8|u8|i16|u16|i32|u32|i64|u64)?')
    _DECFLOAT_REGEXP = re.compile(r'(-?[0-9][0-9_]*(?:\.[0-9][0-9_]*)?(?:[eE][+-]?[0-9][0-9_]*)?)(f32|f64)?')
    _HEXFLOAT_REGEXP = re.compile(r'(-?0[xX][0-9a-fA-F][0-9a-fA-F_]*\.[0-9a-fA-F][0-9a-fA-F_]*[pP][+-]?[0-9]+)(f32|f64)?')

    def token_value(self, tok):
        if not tok:
            raise ValueError('unexpected end of input')

        # Check if boolean.
        if tok == 'true':
            return True
        if tok == 'false':
            return False

        # Check if integer.
        m = self._INTEGER_REGEXP.fullmatch(tok)
        if m:
            num, suffix = m.groups()
            t = suffix_to_type(suffix)
            if t == None:
                t = np.int32
            return t(int(num, 0))

        # Check if decimal float.
        m = self._DECFLOAT_REGEXP.fullmatch(tok)
        if m:
            num, suffix = m.groups()
            t = suffix_to_type(suffix)
            if t == None:
                t = np.float64
            return t(float(num))

        # Check if hex float.
        m = self._HEXFLOAT_REGEXP.fullmatch(tok)
        if m:
            num, suffix = m.groups()
            t = suffix_to_type(suffix)
            if t == None:
                t = np.float64
            return t(float.fromhex(num))

        raise ValueError('invalid value: ' + tok)

    # Read a nested list of scalars in nonempty array notation.
    def text_scalars(self):
        tok = self.next_token()
        vs = []

        if tok == '[':
            while True:
                tok = self.next_token()
                if not tok:
                    break
                elif tok == ']':
                    return vs
                elif tok == '[':
                    self.unget_char('[')
                    vs += [self.text_scalars()]
                elif len(vs) != 0 and tok == ',':
                    tok = self.next_token()
                    if tok == '[':
                        self.unget_char('[')
                        vs += [self.text_scalars()]
                    else:
                        vs += [self.token_value(tok)]
                elif len(vs) == 0:
                    vs += [self.token_value(tok)]
                else:
                    raise ValueError('unexpected token {}'.format(tok))
        else:
            return self.token_value(tok)

        raise ValueError

    def read_empty_array(self):
        # Assuming the 'empty' string has already been read.
        if self.get_char() != '(':
            raise ValueError

        shape = []
        t = None
        while True:
            tok = self.next_token()
            if tok == '[':
                shape += [int(self.next_token())]
                if self.get_char() != ']':
                    raise ValueError
            else:
                t = suffix_to_type(tok)
                if t == None:
                    raise ValueError('unknown type {}'.format(tok))
                break

        if self.get_char() != ')':
            raise ValueError

        if len(shape) == 0:
            raise ValueError('empty array with no dimensions')

        if np.product(shape) != 0:
            raise ValueError('empty array with nonempty shape')

        # We piggyback on Numpy's detection of irregular arrays.
        v = np.zeros(shape, dtype=t)

        return v

    def text_value(self):
        # First check whether this is an empty array.
        tok = self.next_token()
        if tok == 'empty':
            return self.read_empty_array()
        if tok:
            self.unget_token(tok)

        res = self.text_scalars()

        if type(res) != list:
            # We read a scalar, so we are done.
            return res
        else:
            # We read an array.  Now we have to figure out whether it
            # is homogeneous and regular, and then convert it to a
            # Numpy array.
            t = None
            def check(v):
                nonlocal t
                if type(v) is list:
                    for x in v:
                        check(x)
                elif t == None:
                    t = type(v)
                elif t != type(v):
                    raise ValueError('unexpected type of array element: {}'.format(v))

            check(res)

            return np.array(res, dtype=t)

    def next_is_binary(self):
        self.skip_spaces()
        c = self.get_char()
        if c == 'b':
            (bin_version,) = struct.unpack('<B', self.get_bytes(1))
            if bin_version != BINARY_DATA_FORMAT_VERSION:
                raise ValueError('expected format version {}, got format version {}'.format(
                    BINARY_DATA_FORMAT_VERSION, bin_version))
            return True
        else:
            self.unget_char(c)
            return False

    def bin_read_type(f):
        read_binname = f.get_bytes(4)

        for (k,v) in PRIMTYPES.items():
            if v['binname'] == read_binname:
                return k
        raise ValueError('Unknown type: {}'.format(read_binname))

    # Assumes header has already been read.
    def bin_value(self):
        (r,) = struct.unpack('<B', self.get_bytes(1))
        t = self.bin_read_type()

        shape = []
        n = 1
        for i in range(r):
            (bin_size,) = struct.unpack('<Q', self.get_bytes(8))
            n *= bin_size
            shape.append(bin_size)

        bin_fmt = PRIMTYPES[t]['bin_format']

        # We first read the expected number of types into a
        # bytestring, then use np.fromstring.  This is because
        # np.fromfile does not work on things that are insufficiently
        # file-like, like a network stream.
        bytes = self.get_bytes(n * PRIMTYPES[t]['size'])
        arr = np.frombuffer(bytes, dtype=PRIMTYPES[t]['numpy_type'])
        arr.shape = shape

        return arr

    def value(self):
        if self.next_is_binary():
            return self.bin_value()
        else:
            return self.text_value()

    def eof(self):
        self.skip_spaces()
        return self.peek_char() == None

def numpy_type_to_type_name(t):
    for (k,v) in PRIMTYPES.items():
        if v['numpy_type'] == t:
            return k
    raise Exception('Unknown Numpy type: {}'.format(t))

TYPE_STRS = { np.dtype('int8'): b'  i8',
              np.dtype('int16'): b' i16',
              np.dtype('int32'): b' i32',
              np.dtype('int64'): b' i64',
              np.dtype('uint8'): b'  u8',
              np.dtype('uint16'): b' u16',
              np.dtype('uint32'): b' u32',
              np.dtype('uint64'): b' u64',
              np.dtype('float32'): b' f32',
              np.dtype('float64'): b' f64',
              np.dtype('bool'): b'bool'}

def load(f):
    """Load all values from the given file-like object.

Returns a generator.

    """
    r = Reader(f)
    while not r.eof():
        yield r.value()

def loads(s):
    """Load all values from the given str.

Returns a generator.

    """
    return load(io.StringIO(s))

def loadb(s):
    """Load all values from the given bytes object.

Returns a generator.

    """
    return load(io.BytesIO(s))

def construct_binary_value(v):
    t = v.dtype
    shape = v.shape

    elems = 1
    for d in shape:
        elems *= d

    num_bytes = 1 + 1 + 1 + 4 + len(shape) * 8 + elems * t.itemsize
    bytes = bytearray(num_bytes)
    bytes[0] = np.int8(ord('b'))
    bytes[1] = 2
    bytes[2] = np.int8(len(shape))
    bytes[3:7] = TYPE_STRS[t]

    for i in range(len(shape)):
        bytes[7+i*8:7+(i+1)*8] = np.int64(shape[i]).tostring()

    bytes[7+len(shape)*8:] = np.ascontiguousarray(v).tostring()

    return bytes

def dump_text(v, f):
    if type(v) == np.uint8:
        f.write("%uu8" % v)
    elif type(v) == np.uint16:
        f.write("%uu16" % v)
    elif type(v) == np.uint32:
        f.write("%uu32" % v)
    elif type(v) == np.uint64:
        f.write("%uu64" % v)
    elif type(v) == np.int8:
        f.write("%di8" % v)
    elif type(v) == np.int16:
        f.write("%di16" % v)
    elif type(v) == np.int32:
        f.write("%di32" % v)
    elif type(v) == np.int64:
        f.write("%di64" % v)
    elif type(v) in [np.bool, np.bool_]:
        if v:
            f.write("true")
        else:
            f.write("false")
    elif type(v) == np.float32:
        if np.isnan(v):
            f.write('f32.nan')
        elif np.isinf(v):
            if v >= 0:
                f.write('f32.inf')
            else:
                f.write('-f32.inf')
        else:
            f.write("%.6ff32" % v)
    elif type(v) == np.float64:
        if np.isnan(v):
            f.write('f64.nan')
        elif np.isinf(v):
            if v >= 0:
                f.write('f64.inf')
            else:
                f.write('-f64.inf')
        else:
            f.write("%.6ff64" % v)
    elif type(v) == np.ndarray:
        if np.product(v.shape) == 0:
            tname = numpy_type_to_type_name(v.dtype)
            f.write('empty({}{})'.format(''.join(['[{}]'.format(d)
                                                    for d in v.shape]), tname))
        else:
            first = True
            f.write('[')
            for x in v:
                if not first: f.write(', ')
                first = False
                dump_text(x, f)
            f.write(']')
    else:
        raise Exception("Cannot print value of type {}: {}".format(type(v), v))

def dump(v, f, binary=None):
    """Dump the given value to the given file.

:param v: the value to dump.

:param f: a ``.write()``-supporting file-like object.

:param binary: whether to use the binary data format.  If ``None``,
decide based on the type of ``f``.

    """
    if binary == None:
        binary = not isinstance(f, io.TextIOBase)
    if binary:
        f.write(construct_binary_value(v))
    else:
        dump_text(v, f)

def dumps(v):
    """Returns the textual representation of the argument."""
    f = io.StringIO()
    dump(v, f)
    return f.getvalue()

def dumpb(v):
    """Returns the binary representation of the argument."""
    f = io.BytesIO()
    dump(v, f)
    return f.getvalue()
