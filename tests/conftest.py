import os
import sys

# scripts/ is not a package; its modules import each other by name.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
