"""Tests for Phase 2 material database (no GUI required)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.core.constants import DesignType
from app.core.exceptions import MaterialError, ProjectFileError
from app.core.project_manager import ProjectManager
from app.core.project_model import DesignMember, Project, ProjectInformation
from app.materials.concrete import Concrete
from app.materials.database import MaterialLibrary
from app.materials.project_materials import ROLE_MAIN_REBAR, ProjectMaterials
from app.materials.reinforcement import RebarGrade, RebarSize
from app.materials.schema import SCHEMAS, MaterialKind


class SchemaTests(unittest.TestCase):
    def test_valid_values_build_item(self) -> None:
        result, item = SCHEMAS[MaterialKind.CONCRETE].validate(
            {"name": " fc' 350 ksc ", "fc_ksc": "350", "unit_weight_kg_m3": 2400,
             "ec_ksc": "", "description": ""})
        self.assertTrue(result.is_valid, result.errors)
        self.assertEqual(item, Concrete("fc' 350 ksc", 350.0))

    def test_error_messages(self) -> None:
        result, item = SCHEMAS[MaterialKind.CONCRETE].validate(
            {"name": "", "fc_ksc": -10, "unit_weight_kg_m3": "abc"})
        self.assertIsNone(item)
        self.assertIn("Concrete grade name is required.", result.errors)
        self.assertIn("Concrete grade compressive strength f'c must be greater than 0 ksc.",
                      result.errors)
        self.assertTrue(any("must be a number" in e for e in result.errors))

    def test_rebar_cross_check(self) -> None:
        result, _ = SCHEMAS[MaterialKind.REBAR_GRADE].validate(
            {"name": "X", "bar_type": "Deformed", "fy_ksc": 4000, "fu_ksc": 3000})
        self.assertTrue(any("fu" in e for e in result.errors))

    def test_rows_match_columns(self) -> None:
        for kind, schema in SCHEMAS.items():
            for item in MaterialLibrary().items(kind):
                self.assertEqual(len(schema.row(item)), len(schema.columns))

    def test_old_dicts_still_load(self) -> None:
        concrete = Concrete.from_dict({"name": "A", "fc_ksc": 200})
        self.assertIsNone(concrete.ec_ksc)
        grade = RebarGrade.from_dict({"name": "G", "fy_ksc": 3000, "bar_type": "Deformed"})
        self.assertIsNone(grade.fu_ksc)


class LibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "lib.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_crud_and_persistence(self) -> None:
        library = MaterialLibrary(self.path)
        library.add(MaterialKind.CONCRETE, Concrete("C350", 350.0))
        library.add(MaterialKind.REBAR_SIZE, RebarSize("DB36", 36.0, "Deformed"))
        with self.assertRaises(MaterialError):
            library.add(MaterialKind.CONCRETE, Concrete("c350", 300.0))
        library.update(MaterialKind.CONCRETE, "C350", Concrete("C360", 360.0))
        library.save()

        reloaded = MaterialLibrary(self.path)
        self.assertEqual(reloaded.find(MaterialKind.CONCRETE, "C360").fc_ksc, 360.0)
        self.assertIsNotNone(reloaded.find(MaterialKind.REBAR_SIZE, "DB36"))
        reloaded.remove(MaterialKind.CONCRETE, "C360")
        self.assertIsNone(reloaded.find(MaterialKind.CONCRETE, "C360"))

    def test_builtins_are_protected(self) -> None:
        library = MaterialLibrary(self.path)
        with self.assertRaises(MaterialError):
            library.remove(MaterialKind.REBAR_GRADE, "SD40")
        with self.assertRaises(MaterialError):
            library.update(MaterialKind.REBAR_GRADE, "SD40", RebarGrade("SD40", 1.0, "Deformed"))
        self.assertEqual(library.unique_name(MaterialKind.REBAR_GRADE, "SD40"), "SD40 (2)")

    def test_export_import(self) -> None:
        source = MaterialLibrary(None)
        source.add(MaterialKind.CONCRETE, Concrete("Shared", 300.0))
        exported = source.export_to(Path(self._tmp.name) / "share.json")
        target = MaterialLibrary(self.path)
        self.assertEqual(target.import_from(exported), (1, 0))
        self.assertEqual(target.import_from(exported), (0, 1))

    def test_invalid_files(self) -> None:
        self.path.write_text("{broken", encoding="utf-8")
        library = MaterialLibrary(self.path)  # must not raise
        self.assertEqual(library.user_items(MaterialKind.CONCRETE), [])
        other = Path(self._tmp.name) / "other.json"
        other.write_text(json.dumps({"file_format": "X"}), encoding="utf-8")
        with self.assertRaises(ProjectFileError):
            library.import_from(other)


class ProjectMaterialsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = Project()
        self.member = self.project.add_member(DesignMember(
            DesignType.BEAM, "B1", concrete="fc' 240 ksc", main_rebar="SD40",
            tie_rebar="SR24", result={"status": "not_implemented"}))
        self.materials = ProjectMaterials(self.project)

    def test_rename_propagates_and_clears_results(self) -> None:
        affected = self.materials.update(MaterialKind.REBAR_GRADE, "SD40",
                                         RebarGrade("SD40-X", 4000.0, "Deformed"))
        self.assertEqual(affected, 1)
        self.assertEqual(self.member.main_rebar, "SD40-X")
        self.assertIsNone(self.member.result)
        self.assertEqual(self.project.settings.default_main_rebar, "SD40-X")

    def test_rename_only_keeps_results_when_properties_equal(self) -> None:
        same = self.materials.find(MaterialKind.CONCRETE, "fc' 240 ksc")
        self.materials.update(MaterialKind.CONCRETE, "fc' 240 ksc", same)
        self.assertIsNotNone(self.member.result)

    def test_remove_rules(self) -> None:
        with self.assertRaises(MaterialError) as ctx:
            self.materials.remove(MaterialKind.CONCRETE, "fc' 240 ksc")
        self.assertIn("Beam B1", str(ctx.exception))
        self.materials.remove(MaterialKind.CONCRETE, "fc' 180 ksc")
        self.assertIsNone(self.materials.find(MaterialKind.CONCRETE, "fc' 180 ksc"))

    def test_import_and_default(self) -> None:
        library = MaterialLibrary(None)
        library.add(MaterialKind.REBAR_GRADE, RebarGrade("SD60", 6000.0, "Deformed"))
        self.assertEqual(self.materials.import_from_library(
            library, MaterialKind.REBAR_GRADE, ["SD60", "SD40"]), (1, 1))
        self.materials.set_default(ROLE_MAIN_REBAR, "SD60")
        self.assertEqual(self.project.settings.default_main_rebar, "SD60")
        with self.assertRaises(MaterialError):
            self.materials.set_default(ROLE_MAIN_REBAR, "missing")

    def test_project_roundtrip_with_custom_materials(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            manager = ProjectManager()
            manager.new_project(ProjectInformation(project_name="M"), materials={
                "concretes": [Concrete("C300", 300.0, ec_ksc=250000.0)]})
            manager.project.rebar_sizes.append(RebarSize("DB36", 36.0, "Deformed"))
            path = manager.save_project(Path(folder) / "m.rcproj")
            project = ProjectManager().open_project(path)
        self.assertEqual(project.concretes, [Concrete("C300", 300.0, ec_ksc=250000.0)])
        self.assertIsNotNone(project.find_rebar_size("DB36"))

    def test_phase1_project_without_sizes_loads(self) -> None:
        data = self.project.to_dict()
        del data["reinforcement"]["sizes"]
        self.assertTrue(Project.from_dict(data).rebar_sizes)


if __name__ == "__main__":
    unittest.main()
