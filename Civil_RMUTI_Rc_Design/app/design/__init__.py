"""Design modules (one sub-package per member type).

Use :mod:`app.design.registry` to look up the design class of a
:class:`~app.core.constants.DesignType`. This ``__init__`` intentionally
imports nothing to avoid circular imports between design and calculation
packages.
"""
