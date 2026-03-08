"""
Stub out heavy dependencies before app.py is imported.
This prevents the BART model from loading and Gradio from launching during tests.
"""
import sys
from unittest.mock import MagicMock

for mod in ("transformers", "gradio", "torch"):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()
