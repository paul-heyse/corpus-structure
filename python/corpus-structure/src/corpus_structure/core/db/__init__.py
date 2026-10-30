"""Database connection and extension utilities.

Importing storage no longer constructs the superseded model's physical tables.
Historical database code explicitly imports ``legacy_metadata`` when it needs them.
The current authority is ``semantic.metadata``.
"""
