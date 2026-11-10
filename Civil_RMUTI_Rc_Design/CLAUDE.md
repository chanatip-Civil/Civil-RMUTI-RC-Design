# Civil RMUTI Rc Design — instructions for Claude

Read `README.md`, `CONTRIBUTING.md` and `docs/DECISIONS.md` before changing code.

- Extend the existing code; never replace the architecture, the `.rcproj` format or the GUI.
- Each team member owns one module (column / beam / slab / stair / footing); edit only that
  module's files (see CONTRIBUTING.md section 2). Ask before touching shared files.
- New inputs go into `FIELD_SPECS`; calculations go into the module's `CalculationEngine`
  and return a `DesignResult`. Keep calculations out of the GUI.
- Every design formula or code constant must cite the design standard and clause in a comment.
  Never invent formulas or values; ask the user when a reference is unclear.
- Add tests for every formula (textbook/standard example with its source), keep
  `web/src/core.js` identical in behaviour and extend `tests/test_web_parity.py`.
- Before finishing: `python tools/build_web.py` (if FIELD_SPECS or web/src changed) and
  `python -m pytest` must pass. Report which files changed and why.
