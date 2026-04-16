import os

# data_processor imports dictionaries.py at module level, which requires
# SHAPE_DOCS_PATH to be set. For tests we only call functions that receive
# DataFrames directly (no file I/O), so any non-empty string is fine.
os.environ.setdefault('SHAPE_DOCS_PATH', '/tmp/test_placeholder')
