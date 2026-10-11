import os
import sys

# scripts/ is not a package; its modules import each other by name.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import laz_item  # noqa: E402

# Every validate() in the suite reads the checked-in crate schemas, as the build does.
laz_item.schemas_preload()
