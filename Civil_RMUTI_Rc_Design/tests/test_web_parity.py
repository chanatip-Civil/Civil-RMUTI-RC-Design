"""The web core (web/src/core.js) must give the same results as Python.

Runs the JavaScript in Node.js; skipped when Node is not installed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from app.core.constants import DesignType
from app.core.project_manager import ProjectManager
from app.core.project_model import DesignMember, Project
from app.design.registry import DESIGN_REGISTRY, create_design
from tools.build_web import SPEC_PLACEHOLDER, SRC, build_spec

NODE = shutil.which("node")

CASES: list[tuple[str, dict]] = [
    ("column", {}),
    ("column", {"shape": "Circular", "width": 400, "depth": ""}),
    ("column", {"width": -300}),
    ("column", {"width": "abc", "cover": 200}),
    ("column", {"width": 120, "depth": 400, "cover": 20}),
    ("column", {"width": "2,5", "depth": "1,200.5", "cover": 0.5}),
    ("beam", {}),
    ("beam", {"width": 600, "depth": 400}),
    ("beam", {"cover": 300, "moment_positive": -1}),
    ("slab", {}),
    ("slab", {"short_span": 6, "long_span": 4}),
    ("slab", {"thickness": 30, "cover": 20}),
    ("stair", {}),
    ("stair", {"floor_height": 3200, "riser": 175, "tread": 280}),
    ("stair", {"riser": 2000}),
    ("footing", {}),
    ("footing", {"column_width": 2000, "service_load": 450.5}),
    ("footing", {"embedment": 0.2, "allowable_bearing": 0}),
    ("footing", {"width": 1e7}),
]


def _python_case(dt_value: str, overrides: dict) -> dict:
    project = Project()
    design_type = DesignType(dt_value)
    member = DESIGN_REGISTRY[design_type].create_member(project)
    member.inputs.update(overrides)
    project.add_member(member)
    design = create_design(member, project)
    validation = design.validate()
    out = {"errors": validation.errors, "warnings": validation.warnings, "items": None}
    if validation.is_valid:
        result = design.calculate()
        out["items"] = [[i.label, i.value, i.unit, i.note, i.formatted_value()] for i in result.items]
        out["messages"] = result.messages
        out["status"] = result.status.value
    return out


@unittest.skipIf(NODE is None, "Node.js is not installed")
class WebParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        source = (SRC / "core.js").read_text(encoding="utf-8")
        spec = json.dumps(build_spec(), ensure_ascii=False)
        cls.core_path = Path(cls._tmp.name) / "core.js"
        cls.core_path.write_text(source.replace(SPEC_PLACEHOLDER, spec), encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _node(self, script: str, payload: object) -> object:
        runner = Path(self._tmp.name) / "run.js"
        runner.write_text(script, encoding="utf-8")
        completed = subprocess.run(
            [NODE, str(runner), str(self.core_path)], input=json.dumps(payload),
            capture_output=True, text=True, timeout=60, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_validation_and_geometry_match(self) -> None:
        script = """
const RC = require(process.argv[2]);
const cases = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const out = cases.map(([dt, overrides]) => {
  const p = RC.newProject({project_name: 'T'});
  const m = RC.newMember(p, dt);
  Object.assign(m.inputs, overrides);
  RC.members(p, dt).push(m);
  const v = RC.validateMember(p, dt, m);
  const o = {errors: v.errors, warnings: v.warnings, items: null};
  if (!v.errors.length) {
    const r = RC.calculate(p, dt, m).result;
    o.items = r.items.map(i => [i.label, i.value, i.unit, i.note, RC.formatValue(i.value)]);
    o.messages = r.messages; o.status = r.status;
  }
  return o;
});
process.stdout.write(JSON.stringify(out));
"""
        js_results = self._node(script, CASES)
        for (dt_value, overrides), js in zip(CASES, js_results):
            with self.subTest(design=dt_value, inputs=overrides):
                py = _python_case(dt_value, overrides)
                self.assertEqual(js["errors"], py["errors"])
                self.assertEqual(js["warnings"], py["warnings"])
                if py["items"] is None:
                    self.assertIsNone(js["items"])
                    continue
                self.assertEqual(js["status"], py["status"])
                self.assertEqual(js["messages"], py["messages"])
                self.assertEqual(len(js["items"]), len(py["items"]))
                for js_item, py_item in zip(js["items"], py["items"]):
                    self.assertEqual(js_item[0], py_item[0])
                    self.assertAlmostEqual(js_item[1], py_item[1], places=9)
                    self.assertEqual(js_item[2:], py_item[2:])

    def test_web_file_opens_in_desktop_and_back(self) -> None:
        script = """
const RC = require(process.argv[2]);
const p = RC.newProject({project_name: 'Web'}, {unit_system: 'MKS'});
const m = RC.newMember(p, 'beam'); RC.members(p, 'beam').push(m); RC.calculate(p, 'beam', m);
process.stdout.write(JSON.stringify(RC.serialize(p)));
"""
        web_file = self._node(script, None)
        path = Path(self._tmp.name) / "web.rcproj.json"
        path.write_text(json.dumps(web_file), encoding="utf-8")
        project = ProjectManager().open_project(path)
        self.assertEqual(project.information.project_name, "Web")
        self.assertEqual(project.settings.unit_system, "MKS")
        beam = project.members_of(DesignType.BEAM)[0]
        self.assertEqual(beam.result["status"], "not_implemented")
        self.assertEqual(Project.from_dict(web_file["project"]).to_dict()["beams"][0]["name"], "B1")

        desktop = ProjectManager.serialize(project)
        back = self._node("""
const RC = require(process.argv[2]);
const data = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const p = RC.deserialize(data);
process.stdout.write(JSON.stringify({name: p.project_information.project_name, beams: p.beams.length}));
""", desktop)
        self.assertEqual(back, {"name": "Web", "beams": 1})

    def test_number_formatting(self) -> None:
        values = [0.0, 1.0, 2.5, 300.0, 1500000.0, 0.00001234, 166.66666666, 90000.0, 1234567.891]
        js = self._node("""
const RC = require(process.argv[2]);
const v = JSON.parse(require('fs').readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(v.map(x => [RC.g(x), RC.formatValue(x)])));
""", values)
        from app.design.results import ResultItem
        for value, (g_text, formatted) in zip(values, js):
            self.assertEqual(g_text, f"{value:g}")
            self.assertEqual(formatted, ResultItem("x", value).formatted_value())


if __name__ == "__main__":
    unittest.main()
