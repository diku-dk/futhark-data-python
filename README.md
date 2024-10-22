# Python implementation of the [Futhark](https://github.com/diku-dk/futhark) data format

This is a small Python library that implements reading and writing of
the textual and [binary data
format](https://futhark.readthedocs.io/en/latest/binary-data-format.html)
used by Futhark executables and test tools.  It is intended to make it
easy to write Python scripts that use Python libraries to convert complex
formats (e.g. images, audio) into Futhark test data.  It provides
functions that convert between Numpy values and textual/binary
representations in the Futhark formats.  Comments are supported.
**Beware:** reading and writing the textual data format is very slow.
Use the binary format for all arrays of more than a few hundred
elements.

The following Numpy types are supported: `np.int8`, `np.int16`,
`np.in32`, `np.int64`, `np.uint8`, `np.uint16`, `np.uint32`,
`np.uint64`, `np.float32`, `np.float64`, `np.bool_`, as well as up to
255-dimensional arrays containing elements of these sizes.

## Installation

```
$ pip install --user futhark-data
```

## API

### Serialising

* `dump(v, f, binary=None)`: Dump `v`, which must be a Numpy value, to
  the file-like object `f`.  The parameter `binary` indicates whether
  to use binary data format.  If ``None``, decide based on the type of
  ``f``.

* `dumps(v)`: Returns the argument in the textual data format.

* `dumpb(v)`: Returns the argument in the binary data format.

### Deserialising

* `load(f)`: Load all values from the file-like object `f`.

* `loads(s)`: Load all values from the string `s`.

* `loadb(b)`: Load all values from the byte sequence `b`.

Since a file (or `str`, or `bytes`) can contain any number of Futhark
values, the functions above all return generators.  Use `next` if you
know for sure there is just a single value, and you want it (see
example below).

The functions automatically detect whether the data is encoded using
the binary or textual format, so there is no need for the caller to
specify.

## Examples

```Python
>>> import futhark_data
>>> for x in futhark_data.loads('[1,2,3] [4,5,6]'):
...     print(x)
...
[1 2 3]
[4 5 6]
>>> futhark_data.dumpb(next(futhark_data.loads('[1,2,3]')))
b'b\x02\x01 i32\x03\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00'
```
