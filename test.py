# Used by test.sh.

import futhark_data
import io
import sys

for v in futhark_data.load(open(sys.argv[1], 'rb')):
    sys.stdout.buffer.write(futhark_data.dumpb(v))
