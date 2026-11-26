"""Task logic for the claims ELT pipeline.

Kept separate from the DAG file so every step can be unit-tested and run
without a scheduler. The DAG only wires these functions together.
"""
