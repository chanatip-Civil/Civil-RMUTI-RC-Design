"""Tests for the core layer (no GUI required).

Run with:  python -m pytest   or   python -m unittest discover tests
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from app.core.constants import FILE_FORMAT_ID, DesignStandard, DesignType, UnitSystem
from app.core.exceptions import ProjectFileError, ProjectStateError
from app.core.project_manager import ProjectEvent, ProjectManager
from app.core.project_model import DesignMember, DesignSettings, Project, ProjectInformation
from app.core.settings import HOME_ENV_VAR, SettingsManager
from app.utils.validators import ValidationResult, parse_number, validate_number


class TempDirTestCase(unittest.TestCase):
    """Provides an isolated temporary directory and data folder."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._old_home = os.environ.get(HOME_ENV_VAR)
        os.environ[HOME_ENV_VAR] = str(self.tmp / "home")

    def tearDown(self) -> None:
        if self._old_home is None:
            os.environ.pop(HOME_ENV_VAR, None)
        else:
            os.environ[HOME_ENV_VAR] = self._old_home
        self._tmp.cleanup()


class ProjectModelTests(unittest.TestCase):
    def test_roundtrip_preserves_all_sections(self) -> None:
        project = Project(
            information=ProjectInformation(project_name="Office", designer="A", checker="B"),
            settings=DesignSettings(design_standard=DesignStandard.ACI_318_19.value,
                                    unit_system=UnitSystem.MKS.value),
        )
        project.add_member(DesignMember(DesignType.BEAM, "B1", {"width": 250.0}))
        data = json.loads(json.dumps(project.to_dict()))
        restored = Project.from_dict(data)
        self.assertEqual(restored.to_dict(), project.to_dict())
        for key in ("project_information", "design_standard", "materials", "reinforcement",
                    "columns", "beams", "slabs", "stairs", "footings"):
            self.assertIn(key, data)

    def test_from_dict_tolerates_missing_keys(self) -> None:
        project = Project.from_dict({})
        self.assertEqual(project.member_count(DesignType.COLUMN), 0)
        self.assertTrue(project.concretes)

    def test_member_names(self) -> None:
        project = Project()
        self.assertEqual(project.next_member_name(DesignType.COLUMN), "C1")
        project.add_member(DesignMember(DesignType.COLUMN, "C1"))
        self.assertEqual(project.next_member_name(DesignType.COLUMN), "C2")
        self.assertTrue(project.is_name_taken(DesignType.COLUMN, "c1"))


class ProjectManagerTests(TempDirTestCase):
    def test_new_save_open_cycle(self) -> None:
        events: list[ProjectEvent] = []
        manager = ProjectManager()
        manager.add_listener(events.append)
        manager.new_project(ProjectInformation(project_name="Test"))
        self.assertTrue(manager.is_modified)
        path = manager.save_project(self.tmp / "test")  # extension added
        self.assertEqual(path.suffix, ".rcproj")
        self.assertFalse(manager.is_modified)

        reopened = ProjectManager()
        project = reopened.open_project(path)
        self.assertEqual(project.information.project_name, "Test")
        self.assertEqual([ProjectEvent.OPENED, ProjectEvent.SAVED], events)

    def test_save_keeps_backup(self) -> None:
        manager = ProjectManager()
        manager.new_project(ProjectInformation(project_name="One"))
        path = manager.save_project(self.tmp / "p.rcproj")
        manager.project.information.project_name = "Two"
        manager.save_project()
        self.assertTrue(path.with_name(path.name + ".bak").exists())

    def test_save_without_path_raises(self) -> None:
        manager = ProjectManager()
        manager.new_project(ProjectInformation(project_name="X"))
        with self.assertRaises(ProjectStateError):
            manager.save_project()

    def test_open_rejects_invalid_files(self) -> None:
        bad_json = self.tmp / "bad.rcproj"
        bad_json.write_text("{not json", encoding="utf-8")
        foreign = self.tmp / "foreign.rcproj"
        foreign.write_text(json.dumps({"file_format": "OTHER"}), encoding="utf-8")
        newer = self.tmp / "newer.rcproj"
        newer.write_text(json.dumps({"file_format": FILE_FORMAT_ID, "format_version": 999,
                                     "project": {}}), encoding="utf-8")
        manager = ProjectManager()
        for path in (bad_json, foreign, newer, self.tmp / "missing.rcproj", self.tmp / "x.txt"):
            with self.subTest(path=path.name), self.assertRaises(ProjectFileError):
                manager.open_project(path)
        self.assertFalse(manager.has_project)

    def test_recovery_copy(self) -> None:
        manager = ProjectManager()
        manager.new_project(ProjectInformation(project_name="Crash test"))
        recovery = manager.save_recovery_copy(self.tmp / "recovery")
        self.assertIsNotNone(recovery)
        self.assertEqual(ProjectManager.load_file(recovery).information.project_name, "Crash test")

    def test_close(self) -> None:
        manager = ProjectManager()
        manager.new_project(ProjectInformation(project_name="X"))
        manager.close_project()
        self.assertFalse(manager.has_project)


class SettingsTests(TempDirTestCase):
    def test_recent_projects(self) -> None:
        manager = SettingsManager(self.tmp)
        manager.add_recent_project(self.tmp / "a.rcproj")
        manager.add_recent_project(self.tmp / "b.rcproj")
        manager.add_recent_project(self.tmp / "a.rcproj")
        reloaded = SettingsManager(self.tmp)
        self.assertEqual(reloaded.settings.recent_projects[0], str(self.tmp / "a.rcproj"))
        self.assertEqual(len(reloaded.settings.recent_projects), 2)


class SettingsResetTests(TempDirTestCase):
    def test_reset_restores_defaults(self) -> None:
        manager = SettingsManager(self.tmp)
        manager.settings.default_designer = "Somchai"
        manager.add_recent_project(self.tmp / "a.rcproj")
        manager.reset()
        reloaded = SettingsManager(self.tmp)
        self.assertEqual(reloaded.settings.default_designer, "")
        self.assertEqual(reloaded.settings.recent_projects, [])


class ValidatorTests(unittest.TestCase):
    def test_parse_number(self) -> None:
        self.assertEqual(parse_number("2,5"), 2.5)
        self.assertEqual(parse_number("1,200.5"), 1200.5)
        self.assertIsNone(parse_number("abc"))
        self.assertIsNone(parse_number("nan"))
        self.assertIsNone(parse_number(True))

    def test_messages(self) -> None:
        result = ValidationResult()
        validate_number(-5, "Column width", "mm", result, minimum=0.0)
        validate_number("", "Column depth", "mm", result, minimum=0.0)
        validate_number("x", "Load", "kN", result)
        self.assertEqual(result.errors, [
            "Column width must be greater than 0 mm.",
            "Column depth is required.",
            "Load must be a number (got 'x').",
        ])


if __name__ == "__main__":
    unittest.main()
