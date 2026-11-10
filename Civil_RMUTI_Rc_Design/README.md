# Civil RMUTI Rc Design

โปรแกรมออกแบบโครงสร้างคอนกรีตเสริมเหล็ก (Desktop Application, Python + PySide6)

**Version 0.2.3 — Phase 2: Material Database** · ทำงานเป็นทีม: อ่าน [CONTRIBUTING.md](CONTRIBUTING.md)

> ⚠️ ปัจจุบันคำนวณเฉพาะค่าทางเรขาคณิต (พื้นที่หน้าตัด ปริมาตร อัตราส่วน ฯลฯ) เท่านั้น
> ยังไม่มีการตรวจสอบการออกแบบตามมาตรฐาน — ห้ามนำผลไปใช้ก่อสร้าง

---

## 1. ความต้องการของระบบ

- Python 3.12+ (รองรับ 3.10 ขึ้นไป)
- Windows 10/11, macOS หรือ Linux (มีหน้าจอ)

## 2. ติดตั้ง

```bash
cd Civil_RMUTI_Rc_Design
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## 3. Run โปรแกรม

**Windows แบบง่าย:** ดับเบิลคลิก `run.bat` — ครั้งแรกจะสร้าง `.venv` และติดตั้ง library ให้อัตโนมัติ (ต้องต่อเน็ต) ครั้งต่อไปเปิดโปรแกรมทันที

**แบบพิมพ์คำสั่ง:**

```bash
python main.py
python main.py path/to/project.rcproj   # เปิดโปรเจกต์ทันที
```

## 4. Run Tests

```bash
python -m pytest
# หรือ (ไม่ต้องใช้ pytest)
python -m unittest discover tests
```

Tests ครอบคลุม core layer และ design modules ทั้งหมด (ไม่ต้องใช้ GUI)

---

## 5. Architecture

```
GUI (PySide6)  ──►  ProjectManager  ──►  Project model (dataclasses)  ──►  .rcproj (JSON)
     │
     └──►  Design module (FIELD_SPECS + validate)  ──►  Calculation engine  ──►  DesignResult  ──►  Report
```

| Layer | Package | Qt? | หน้าที่ |
|---|---|---|---|
| Core | `app/core` | ✗ | constants, project model, project manager, settings, logging, exceptions |
| Materials | `app/materials` | ✗ | concrete grades, steel grades (SR24/SD30/SD40/SD50), bar sizes |
| Design | `app/design` | ✗ | input spec, validation, calculate(), generate_report() ต่อ member type |
| Calculations | `app/calculations` | ✗ | calculation engines (แยกจาก GUI 100 %) |
| Utils | `app/utils` | ✗ | atomic file I/O, validators |
| GUI | `app/gui` | ✓ | main window, dialogs, pages, widgets |

หลักการสำคัญ

- **Data-driven forms** — ฟอร์มกรอกข้อมูลสร้างจาก `FIELD_SPECS` ของแต่ละ design class อัตโนมัติ
  เพิ่ม member type ใหม่ไม่ต้องเขียน GUI ใหม่
- **Registry** — `app/design/registry.py` จับคู่ `DesignType` → design class
- **Core ไม่ import Qt** — นำไปใช้กับ CLI, test, web หรือ SQLite back-end ได้
- **Safe save** — เขียนไฟล์แบบ atomic + เก็บ `.bak`, crash จะสร้าง recovery copy

## 6. โครงสร้างไฟล์

```
Civil_RMUTI_Rc_Design/
├── main.py                          Entry point (High-DPI, logging, error hook)
├── run.bat                          Windows: ดับเบิลคลิกเพื่อติดตั้ง + เปิดโปรแกรม (สำหรับนักพัฒนา)
├── packaging/                       สคริปต์ทำตัวติดตั้ง Windows (ดูหัวข้อ 11)
├── requirements.txt
├── README.md
├── app/
│   ├── core/
│   │   ├── constants.py             ชื่อโปรแกรม, DesignType, DesignStandard, UnitSystem, unit labels
│   │   ├── exceptions.py            ProjectFileError, InputValidationError, CalculationError ...
│   │   ├── logger.py                Rotating error log
│   │   ├── project_model.py         Project, ProjectInformation, DesignSettings, DesignMember
│   │   ├── project_manager.py       New / Open / Save / Close, .rcproj format, recovery
│   │   └── settings.py              User settings + recent projects (JSON)
│   ├── materials/
│   │   ├── concrete.py              Concrete grade (f'c, unit weight, Ec override)
│   │   ├── reinforcement.py         RebarGrade (fy, fu, Es override), RebarSize (TIS 20 / TIS 24)
│   │   ├── schema.py                MaterialKind + field schema → validation / forms / tables
│   │   ├── database.py              MaterialLibrary: built-in + user library (JSON), import/export
│   │   └── project_materials.py     ProjectMaterials: add/edit/remove, rename propagation, usage check
│   ├── design/
│   │   ├── fields.py                FieldSpec (input definition)
│   │   ├── results.py               DesignStatus, ResultItem, DesignResult
│   │   ├── base.py                  BaseDesign (validate / calculate / generate_report)
│   │   ├── report.py                Text calculation report
│   │   ├── registry.py              DesignType → design class
│   │   ├── column/column_design.py  ColumnDesign
│   │   ├── beam/beam_design.py      BeamDesign
│   │   ├── slab/slab_design.py      SlabDesign
│   │   ├── stair/stair_design.py    StairDesign
│   │   └── footing/footing_design.py FootingDesign
│   ├── calculations/
│   │   ├── base_engine.py           CalculationEngine, CalculationContext, GeometryOnlyEngine
│   │   ├── column_calculation.py    ... beam/slab/stair/footing_calculation.py
│   ├── gui/
│   │   ├── main_window.py           Menu, Toolbar, Sidebar, Workspace, Status bar
│   │   ├── new_project_dialog.py    New Project / Project Properties
│   │   ├── open_project_dialog.py   Open / Save As file dialogs
│   │   ├── design_selection.py      Design Selection cards
│   │   ├── error_handler.py         Global exception hook
│   │   ├── styles.py                Theme (QSS)
│   │   ├── pages/                   welcome, project overview, design editor
│   │   ├── dialogs/                 about, settings, material DB + material edit, user manual, report
│   │   └── widgets/                 icons, design card, sidebar, section preview
│   └── utils/
│       ├── file_manager.py          Atomic write, JSON read/write
│       └── validators.py            ValidationResult, validate_number ...
└── tests/
    ├── test_core.py
    ├── test_design.py
    ├── test_materials.py
    └── test_web_parity.py           เทียบผล web (JS) กับ Python
├── tools/build_web.py               สร้างเว็บเวอร์ชันไฟล์เดียว
└── web/                             เว็บเวอร์ชัน (ดูหัวข้อ 10)
```

## 7. Project file (`.rcproj`)

UTF-8 JSON:

```json
{
  "file_format": "CIVIL_RMUTI_RC_DESIGN_PROJECT",
  "format_version": 1,
  "application": {"name": "Civil RMUTI Rc Design", "version": "0.2.3"},
  "saved_at": "2026-11-10T10:00:00",
  "project": {
    "project_information": {...},
    "design_settings": {...},
    "design_standard": {"code": "EIT 1008-38", "label": "..."},
    "materials": {"concrete": [...]},
    "reinforcement": {"grades": [...]},
    "metadata": {...},
    "columns": [...], "beams": [...], "slabs": [...], "stairs": [...], "footings": [...]
  }
}
```

`format_version` + `ProjectManager._migrate()` รองรับการอัปเกรดไฟล์รุ่นเก่าในอนาคต

## 8. วิธีทดสอบด้วยมือ

**New Project**
1. `File → New Project` (Ctrl+N) → เว้น Project Name ว่างแล้วกด Create → ต้องขึ้น *Invalid Input*
2. กรอก Project Name → Create → เข้าหน้า **Select Design Type**; title bar มี `*`
3. คลิก Card *Column* → `Add` → แก้ Width เป็น `-300` → `Apply` → ต้องขึ้น
   *Column width b / diameter D must be greater than 0 mm.* และช่องเป็นสีแดง
4. แก้เป็น `400` → `Calculate` (F5) → ตาราง Results แสดงค่า, status *Design check not implemented*

**Save Project**
1. `File → Save Project` (Ctrl+S) → ครั้งแรกจะถามชื่อไฟล์ → ได้ไฟล์ `*.rcproj`
2. `*` ใน title bar หายไป; แก้ข้อมูลแล้ว Save อีกครั้ง → มีไฟล์ `*.rcproj.bak`
3. `Save Project As` บันทึกเป็นชื่อใหม่ได้

**Open Project**
1. `File → Close Project` → `File → Open Project` (Ctrl+O) → เลือกไฟล์ที่บันทึกไว้
2. ตรวจว่า Project Information, members ทุกประเภท, inputs และ results กลับมาครบ
3. แก้ไขแล้ว Save ทับได้ / เปิดจาก `File → Open Recent` หรือหน้า Welcome ได้
4. ลองเปิดไฟล์ที่ไม่ใช่ project (เปลี่ยนนามสกุล .txt เป็น .rcproj) → ต้องขึ้นข้อความ error และโปรแกรมไม่ปิด

## 9. Material Database (Phase 2)

`Tools → Material Database` (หรือ `Reinforcement Database`) มี 3 แท็บ: Concrete, Reinforcement Grades, Bar Sizes
แต่ละแท็บมี 2 ตาราง

| ตาราง | เก็บที่ | ทำอะไรได้ |
|---|---|---|
| **Material Library** | `material_library.json` ใน data folder (ใช้ร่วมทุกโครงการ) | New / Edit / Duplicate / Delete, Import / Export (แชร์ให้เพื่อน), Add to Project |
| **Project Materials** | ในไฟล์ `.rcproj` | New / Edit / Remove, Save to Library, ตั้ง Default |

กฎของระบบ (อยู่ใน core — เวอร์ชันเว็บใช้ร่วมได้)

- วัสดุ Built-in (SR24, SD30, SD40, SD50, f'c 180–320 ksc, RB6–DB32) แก้/ลบไม่ได้ → ใช้ Duplicate
- ชื่อซ้ำไม่ได้ (ไม่สนตัวพิมพ์เล็ก-ใหญ่)
- แก้วัสดุในโครงการ → ทุก member ที่ใช้อยู่อัปเดตตาม (รวมการเปลี่ยนชื่อ) และผลคำนวณเดิมถูกล้าง
- วัสดุที่ถูกใช้หรือเป็น default ลบไม่ได้ และต้องเหลืออย่างน้อย 1 รายการ
- New Project คัดลอกวัสดุทั้งหมดจาก Library ไว้ในโครงการ → ไฟล์ `.rcproj` เปิดเครื่องอื่นได้ครบ
- Ec / Es เว้นว่าง = ใช้ค่าตามมาตรฐานที่เลือก (คำนวณใน Phase 3+ พร้อมอ้างอิงข้อกำหนด)
- เปิดไฟล์ Phase 1 ได้ (bar sizes จะใช้ค่า built-in)

**ทดสอบ Material Database**
1. Tools → Material Database → แท็บ Concrete → ตาราง Library กด **New** → ชื่อ `fc' 350 ksc`, f'c `350` → OK
2. ลองกรอก f'c = `-5` → ต้องขึ้น *Invalid Input*
3. เลือก `SD40` (Built-in) แล้วกด Edit → ปุ่มกดไม่ได้ / ใช้ Duplicate แทน
4. เปิดโครงการ → เลือก `fc' 350 ksc` ใน Library → **Add to Project →**
5. ในหน้า Beam เลือก Concrete ใหม่ได้ทันที → Calculate
6. กลับไปแก้ f'c ของวัสดุนั้นในตาราง Project → ผลคำนวณของ Beam ถูกล้าง ต้องคำนวณใหม่
7. ลอง Remove วัสดุที่ Beam ใช้อยู่ → ต้องขึ้นข้อความว่าใช้งานอยู่

## 10. Web version (เปิดใน Claude / เบราว์เซอร์ / มือถือ)

```
web/
├── src/index.html   โครงหน้าเว็บ
├── src/styles.css   ธีม (สว่าง/มืด, รองรับมือถือ)
├── src/core.js      validation + geometry engine + report + รูปแบบไฟล์ .rcproj (ไม่ใช้ DOM)
├── src/ui.js        หน้าจอ
└── dist/civil_rmuti_rc_design.html   ไฟล์เดียวที่ build แล้ว (เปิดด้วยเบราว์เซอร์ได้เลย)
tools/build_web.py   export field / unit / material spec จาก Python แล้วประกอบเป็นไฟล์เดียว
```

- **ใช้ spec เดียวกับ desktop** — ช่องกรอก, ขอบเขตค่า, หน่วย, วัสดุ built-in มาจากโค้ด Python โดยตรง
- **ผลคำนวณต้องตรงกับ Python** — `tests/test_web_parity.py` รัน `core.js` ด้วย Node.js แล้วเทียบผลกับ Python
  ทุกกรณี (ข้อความ error, warning, ค่าที่คำนวณ, การจัดรูปแบบตัวเลข) และทดสอบเปิดไฟล์ข้ามกัน
- **ไฟล์ใช้ร่วมกันได้** — เว็บบันทึกเป็น `ชื่อโครงการ.rcproj.json` ซึ่งโปรแกรม desktop เปิดได้ และเว็บเปิดไฟล์ `.rcproj` จาก desktop ได้
- งานที่ค้างอยู่จะถูกเก็บไว้ในเบราว์เซอร์เครื่องนั้นอัตโนมัติ (ควรกด Save เพื่อเก็บเป็นไฟล์)
- แก้ไขวัสดุทำได้ในโปรแกรม desktop; หน้าเว็บแสดงวัสดุของโครงการ

หลังแก้โค้ด Python (เช่นเพิ่ม field) หรือ `web/src/*` ให้ build ใหม่:

```bash
python tools/build_web.py
python -m pytest tests/test_web_parity.py
```

### ใช้บน iPad

- **ผ่านแอป Claude / Safari:** เปิดลิงก์ artifact ได้ทันที
- **ไฟล์ standalone:** `web/dist/civil_rmuti_rc_design_standalone.html` เป็นไฟล์ HTML สมบูรณ์ (มีโลโก้, ไอคอน Home Screen)
  นำไปวางบน web server ใดก็ได้ (เช่น GitHub Pages / server มหาวิทยาลัย) แล้วเปิดใน Safari → แชร์ → **Add to Home Screen**
- รองรับแนวตั้ง แนวนอน และ Split View; ปุ่มแตะขนาด ≥ 44 px; ช่องกรอกไม่ซูมเอง;
  ช่องที่รับค่าติดลบ (เช่น Moment) ใช้คีย์บอร์ดที่มีเครื่องหมายลบ
- คีย์บอร์ด (Magic Keyboard): ⌘S = Save, ⌘Enter = Calculate
- ปุ่ม Open บน iPad เลือกไฟล์ `.rcproj` / `.rcproj.json` จากแอป Files ได้

Build: `python tools/build_web.py` (ใส่ `--no-logo` เพื่อใช้เครื่องหมาย RC แทนโลโก้)

## 11. ทำตัวติดตั้ง Windows (ไม่ต้องลง Python บนเครื่องผู้ใช้)

ทำบนเครื่อง Windows 10/11 ที่มี Python 3.12+ และ [Inno Setup 6](https://jrsoftware.org/isinfo.php)
(`winget install JRSoftware.InnoSetup`) แล้วดับเบิลคลิก:

```
packaging\build_installer.bat
```

สคริปต์จะ: สร้าง `.venv-build` → ติดตั้ง library → รัน tests (ถ้าไม่ผ่านจะหยุด) → สร้างไอคอนจากโลโก้ →
build ด้วย PyInstaller → ทำตัวติดตั้งด้วย Inno Setup

ผลลัพธ์: `dist_installer\CivilRMUTIRcDesign_Setup_<version>.exe`

| ไฟล์ | หน้าที่ |
|---|---|
| `packaging/build_installer.bat` | สคริปต์ build ทั้งหมด |
| `packaging/civil_rmuti_rc_design.spec` | สูตร PyInstaller (one-folder, ไม่มีหน้าต่าง console, ใส่ไอคอน + version info) |
| `packaging/installer.iss` | ตัวติดตั้ง: Start Menu, Desktop icon, เปิดไฟล์ `.rcproj` ด้วยดับเบิลคลิก, Uninstall |
| `packaging/make_icon.py` | แปลง `rmuti_logo.png` → `app.ico` |
| `app/core/paths.py` | หาไฟล์ resource ได้ทั้งตอนรันจาก source และจากโปรแกรมที่ติดตั้ง |

ตัวติดตั้งรองรับการติดตั้งแบบไม่ใช้สิทธิ์ admin (เลือก "Install for me only"), อัปเกรดทับเวอร์ชันเดิมได้
และการถอนการติดตั้งจะ **ไม่ลบ** ข้อมูลผู้ใช้ (settings, คลังวัสดุ) ใน `%USERPROFILE%\.civil_rmuti_rc_design`

ถ้าจะออกเวอร์ชันใหม่: แก้ `APP_VERSION` ใน `app/core/constants.py` แล้วรัน `build_installer.bat` อีกครั้ง

## 12. ไฟล์ข้อมูลผู้ใช้

`~/.civil_rmuti_rc_design/` (เปลี่ยนได้ด้วย env `RCDESIGN_HOME`)

- `settings.json` — ค่า default, recent projects, ขนาดหน้าต่าง
- `material_library.json` — วัสดุที่ผู้ใช้เพิ่มเอง
- `logs/rcdesign.log` — error log
- `recovery/` — สำเนาฉุกเฉินเมื่อเกิด error ที่ไม่คาดคิด

## 13. Roadmap

| Phase | งาน |
|---|---|
| 1 ✅ | Application framework |
| 2 ✅ | Material Database (ฉบับนี้) |
| 3 | Column design |
| 4 | Beam design |
| 5 | Slab design |
| 6 | Stair design |
| 7 | Footing design |
| 8 | Calculation report (HTML/PDF) |
| 9 | Drawing / detailing |
| 10 | Export PDF / Excel |

ทุก Phase ที่มีสูตรออกแบบต้องระบุมาตรฐานและเลขข้อ (clause) ที่อ้างอิงก่อน implement
ใน `CalculationEngine` ของ member นั้น (เช่น `supported_standards`)
