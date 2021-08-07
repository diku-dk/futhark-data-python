# Used by test.sh.

import io
import sys

import futhark_data

for v in futhark_data.load(open(sys.argv[1], 'rb')):
    sys.stdout.buffer.write(futhark_data.dumpb(v))
