"""Calculation engines, completely independent of the GUI.

Pipeline::

    GUI -> Input model -> Validation -> Calculation engine -> Design check
        -> Result model -> Report

Phase 1 engines compute only exact geometric quantities and return
``DesignStatus.NOT_IMPLEMENTED`` for the structural design check. Code
formulas will be added per phase with explicit clause references to the
selected design standard.
"""
