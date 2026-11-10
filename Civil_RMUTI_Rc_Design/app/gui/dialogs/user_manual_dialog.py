"""Built-in user manual."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser, QVBoxLayout, QWidget

from app.core.constants import APP_NAME, APP_VERSION, PROJECT_FILE_EXTENSION

_MANUAL_HTML: str = f"""
<h2>{APP_NAME} — User Manual</h2>
<p>Version {APP_VERSION}</p>

<h3>1. Create a project</h3>
<ol>
<li><b>File → New Project</b> (Ctrl+N).</li>
<li>Enter Project Name (required), number, designer, checker, organization and date.</li>
<li>Select the <b>Design Standard</b> and <b>Unit System</b>, then press <b>Create</b>.</li>
<li>The <b>Design Selection</b> page opens. Click a card (Column, Beam, Slab, Stair, Footing).</li>
</ol>

<h3>2. Design members</h3>
<ul>
<li><b>Add</b> creates a member (C1, B1, S1, ST1, F1 ...). Duplicate / Rename / Delete manage the list.</li>
<li>Fill in the form. Fields marked * are required. Invalid fields turn red.</li>
<li><b>Apply</b> (Ctrl+Enter) validates and stores the input. <b>Calculate</b> (F5) also runs the engine.</li>
<li><b>Report...</b> shows a text calculation sheet that can be copied or saved.</li>
</ul>
<p><b>Units:</b> section dimensions in mm, spans in m; loads follow the project unit system.
Changing the unit system later does not convert existing values.</p>

<h3>3. Save and open</h3>
<ul>
<li><b>File → Save Project</b> (Ctrl+S) writes a <code>{PROJECT_FILE_EXTENSION}</code> file (JSON).
The previous version is kept as <code>{PROJECT_FILE_EXTENSION}.bak</code>.</li>
<li><b>File → Open Project</b> (Ctrl+O) restores all project data, members and results.</li>
<li>Unsaved changes are marked with * in the title bar; you are asked before closing.</li>
</ul>

<h3>4. Material Database</h3>
<p><b>Tools → Material Database / Reinforcement Database</b> has one tab per kind
(Concrete, Reinforcement Grades, Bar Sizes) with two tables:</p>
<ul>
<li><b>Material Library</b> — shared by all projects. Built-in items (TIS 20/24 steel,
common f'c grades) are read-only; use <i>Duplicate</i> to make an editable copy.
New, Edit, Delete; <i>Import/Export Library</i> shares user materials as JSON.</li>
<li><b>Project Materials</b> — stored inside the project file. <i>Add to Project</i> copies
library items. Editing a material updates all members using it (renames included) and
clears their old results. Used materials cannot be removed. Set project defaults here.</li>
<li>Ec / Es left blank will be taken from the selected design standard in later phases.</li>
</ul>

<h3>5. Current limitations</h3>
<p style="color:#C62828">Only geometric quantities are calculated. Structural design checks
according to the selected standard are <b>not implemented yet</b>
(Column: Phase 3, Beam: Phase 4, Slab: Phase 5, Stair: Phase 6, Footing: Phase 7).
Do not use the results for construction.</p>

<h3>6. Troubleshooting</h3>
<p>Errors are written to the log file shown in <b>Tools → Settings</b>. If the program
encounters an unexpected error, a recovery copy of the open project is saved in the
<i>recovery</i> folder of the data directory.</p>
"""


class UserManualDialog(QDialog):
    """Shows the HTML user manual."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — User Manual")
        self.resize(720, 620)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(_MANUAL_HTML)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(browser)
        layout.addWidget(buttons)
