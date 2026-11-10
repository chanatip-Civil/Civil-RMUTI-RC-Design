# การทำงานเป็นทีม — Civil RMUTI Rc Design

เอกสารนี้สำหรับสมาชิกทุกคนที่ช่วยพัฒนาโปรแกรม อ่านให้จบก่อนเริ่มแก้โค้ด
(ถ้าใช้ Claude ช่วยเขียนโค้ด ให้ส่ง [docs/CLAUDE_HANDOFF.md](docs/CLAUDE_HANDOFF.md) ให้ Claude อ่านก่อนทุกครั้ง)

---

## 1. หลักสำคัญ 5 ข้อ

1. **ต่อยอดจากโค้ดเดิม ห้ามเขียนระบบใหม่ทับ** — โครงสร้าง, รูปแบบไฟล์ `.rcproj`, หน้าจอ และระบบวัสดุมีอยู่แล้ว
2. **แก้เฉพาะไฟล์ของ module ตัวเอง** (ตารางข้อ 2) ไฟล์ส่วนกลางต้องตกลงกับหัวหน้าทีมก่อน
3. **ทุกสูตรต้องมีแหล่งอ้างอิง** — ระบุมาตรฐาน + เลขข้อ (clause) ในโค้ด ห้ามใส่สูตรหรือค่าคงที่ที่ไม่มีที่มา
4. **ทุกสูตรต้องมี test** — เทียบกับตัวอย่างในตำรา/มาตรฐาน หรือการคำนวณมือที่ตรวจแล้ว
5. **รัน test ทั้งหมดให้ผ่านก่อนส่งงานทุกครั้ง** — `python -m pytest`

---

## 2. แบ่งงานตาม module

| Module | ผู้รับผิดชอบ | ไฟล์ที่แก้ได้ |
|---|---|---|
| Column (เสา) | ………… | `app/design/column/`, `app/calculations/column_calculation.py`, `tests/test_column*.py` |
| Beam (คาน) | ………… | `app/design/beam/`, `app/calculations/beam_calculation.py`, `tests/test_beam*.py` |
| Slab (พื้น) | ………… | `app/design/slab/`, `app/calculations/slab_calculation.py`, `tests/test_slab*.py` |
| Stair (บันได) | ………… | `app/design/stair/`, `app/calculations/stair_calculation.py`, `tests/test_stair*.py` |
| Footing (ฐานราก) | ………… | `app/design/footing/`, `app/calculations/footing_calculation.py`, `tests/test_footing*.py` |
| ส่วนกลาง (หัวหน้าทีม) | ………… | `app/core/`, `app/design/base.py`, `fields.py`, `results.py`, `report.py`, `registry.py`, `app/materials/`, `app/gui/`, `web/src/ui.js`, `packaging/`, `tools/` |

**ไฟล์ที่ทุกคนแก้ร่วมกัน (ระวังชนกัน)** — แก้เฉพาะ "บล็อกของ module ตัวเอง" เท่านั้น

| ไฟล์ | บล็อกของแต่ละคน |
|---|---|
| `web/src/core.js` | `SPECIFIC.<type>` และ `ENGINES.<type>` |
| `tests/test_web_parity.py` | บรรทัดใน `CASES` ที่ขึ้นต้นด้วยชื่อ module ตัวเอง |

ต้องการเปลี่ยนไฟล์ส่วนกลาง (เช่นเพิ่ม field ชนิดใหม่ใน `FieldSpec`, เพิ่มหน่วยใน `Quantity`,
แก้ `BaseDesign`) → เปิด Issue / แจ้งหัวหน้าทีมก่อน แล้วให้หัวหน้าทีมเป็นคนแก้

---

## 3. เตรียมเครื่อง

```bash
git clone <ลิงก์ repository ของทีม>
cd Civil_RMUTI_Rc_Design
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m pytest                   # ต้องผ่านทั้งหมดก่อนเริ่มงาน
python main.py                     # เปิดโปรแกรม
```

ติดตั้ง Node.js (https://nodejs.org) ด้วย เพื่อให้ test เทียบผลเว็บกับ Python (`test_web_parity.py`) ทำงาน
ถ้าไม่มี Node test นี้จะถูกข้าม (skip) — แต่ก่อน merge ต้องมีคนรันให้ผ่าน

---

## 4. ขั้นตอนทำงานด้วย Git (GitHub)

```bash
git checkout main
git pull                                  # เอาโค้ดล่าสุดก่อนเริ่มทุกครั้ง
git checkout -b feature/column-sdm        # 1 branch ต่อ 1 งาน: feature/<module>-<เรื่อง>
# ... แก้โค้ด + เขียน test ...
python -m pytest
python tools/build_web.py                 # ถ้าแก้ FIELD_SPECS หรือ web/src/*
git add -A
git commit -m "column: axial capacity per EIT 1008-38 clause x.x"
git push -u origin feature/column-sdm
```

แล้วเปิด **Pull Request** บน GitHub ให้หัวหน้าทีมหรือเพื่อนอีก 1 คนตรวจก่อน merge เข้า `main`
**ห้าม push ตรงเข้า `main`**

ข้อความ commit ขึ้นต้นด้วยชื่อ module: `column:`, `beam:`, `slab:`, `stair:`, `footing:`, `core:`, `gui:`, `web:`

---

## 5. วิธีเพิ่มการคำนวณออกแบบ (ตัวอย่าง: Column)

ลำดับข้อมูลในโปรแกรม (ห้ามข้ามขั้น):

```
GUI / Web → Input (FIELD_SPECS) → Validation → Calculation Engine → DesignResult → Report
```

### 5.1 เพิ่มช่องกรอก — `app/design/column/column_design.py`

เพิ่ม `FieldSpec` ใน `FIELD_SPECS` (หน้าจอ desktop และเว็บสร้างช่องให้อัตโนมัติ ไม่ต้องแก้ GUI)

```python
FieldSpec("bar_count", "Number of main bars", Quantity.NONE, 8.0, kind=INTEGER,
          group="Reinforcement", minimum=4.0, min_inclusive=True, maximum=64.0),
```

ตรวจความสัมพันธ์ระหว่างช่องใน `_validate_specific()` (error = คำนวณไม่ได้, warning = แจ้งเตือน)

### 5.2 เขียน engine — `app/calculations/column_calculation.py`

- สืบทอดจาก `CalculationEngine` (ไม่ใช่ `GeometryOnlyEngine` แล้ว)
- ระบุมาตรฐานที่รองรับใน `supported_standards`
- ถ้าโครงการเลือกมาตรฐานที่ยังไม่รองรับ → คืน `DesignStatus.NOT_IMPLEMENTED` พร้อมข้อความ
- คืนค่า `PASS` / `FAIL` ตามผลตรวจ ทุก `ResultItem` ที่เป็นผลตามมาตรฐานให้ใส่เลขข้อใน `note`

```python
class ColumnCalculationEngine(CalculationEngine):
    design_type = DesignType.COLUMN
    engine_name = "Column engine v1.0"
    supported_standards = (DesignStandard.EIT_1008,)

    def run(self, inputs, context):
        if not self.supports(context.standard):
            ...  # คืน NOT_IMPLEMENTED เหมือนเดิม
        # สูตรแต่ละบรรทัดต้องมี comment อ้างอิง เช่น
        # วสท. 1008-38 ข้อ ...: <ชื่อสูตร>
        ...
        return DesignResult(status=DesignStatus.PASS, items=[...], messages=[...],
                            standard=context.standard.value, engine=self.engine_name)
```

หน่วย: ภายใน engine ให้แปลงเป็นหน่วยเดียวกันก่อนคำนวณ (`context.unit_system`, ค่าคงที่ใน
`app/core/constants.py` เช่น `KSC_TO_MPA`, `KGF_TO_N`) และระบุหน่วยใน `ResultItem.unit` เสมอ
วัสดุ: ใช้ `context.concrete`, `context.main_rebar`, `context.tie_rebar` (ค่า Ec/Es ที่ผู้ใช้ override อยู่ใน
`ec_ksc` / `es_ksc` ถ้าเป็น `None` ให้คำนวณตามมาตรฐานพร้อมอ้างอิงข้อ)

### 5.3 เขียน test — `tests/test_column_<เรื่อง>.py`

```python
class ColumnSdmTests(unittest.TestCase):
    def test_textbook_example_x(self):
        """ตัวอย่าง x.x หน้า yy จาก <ชื่อตำรา/มาตรฐาน>"""
        ...
        self.assertAlmostEqual(result_value, expected_value, delta=tolerance)
```

ต้องมีอย่างน้อย: กรณีผ่าน (PASS), กรณีไม่ผ่าน (FAIL), กรณีค่าขอบ และกรณีมาตรฐานที่ไม่รองรับ

### 5.4 เว็บ — `web/src/core.js`

แก้ `ENGINES.column` และ `SPECIFIC.column` ให้ได้ผลเหมือน Python ทุกตัวอักษร (ข้อความ error/warning ด้วย)
แล้วเพิ่มกรณีใน `CASES` ของ `tests/test_web_parity.py` จากนั้น:

```bash
python tools/build_web.py
python -m pytest tests/test_web_parity.py
```

### 5.5 รายงาน

`TextReportBuilder` (`app/design/report.py`) แสดง input, validation และ `DesignResult` ให้อัตโนมัติ
ถ้าต้องการหัวข้อรายงานเฉพาะ module ให้แจ้งหัวหน้าทีม (เป็นไฟล์ส่วนกลาง)

---

## 6. Checklist ก่อนเปิด Pull Request

- [ ] แก้เฉพาะไฟล์ของ module ตัวเอง (หรือได้ตกลงกับหัวหน้าทีมแล้ว)
- [ ] ทุกสูตรมี comment อ้างอิง มาตรฐาน + เลขข้อ
- [ ] มี test จากตัวอย่างในตำรา/มาตรฐาน และระบุแหล่งที่มาใน docstring
- [ ] `python -m pytest` ผ่านทั้งหมด (รวม `test_web_parity.py`)
- [ ] เปิดโปรแกรมจริง ลองกรอกค่า → Calculate → Report → Save → Open ได้
- [ ] ไฟล์ `.rcproj` เดิมยังเปิดได้ (ห้ามเปลี่ยนรูปแบบไฟล์โดยไม่ได้คุยกัน)
- [ ] ไม่มีไฟล์ที่ไม่เกี่ยวข้อง (`.venv`, `dist`, `__pycache__`) — `.gitignore` กันไว้แล้ว

---

## 7. ใครทำอะไรต่อ (Roadmap)

| Phase | งาน | สถานะ |
|---|---|---|
| 1 | Application framework | ✅ |
| 2 | Material Database | ✅ |
| 3–7 | Column / Beam / Slab / Stair / Footing design | 🔜 ทำพร้อมกันได้ คนละ module |
| 8 | Calculation report (HTML/PDF) | ส่วนกลาง |
| 9 | Drawing / detailing | ส่วนกลาง + ทุก module |
| 10 | Export PDF / Excel | ส่วนกลาง |

**ต้องตกลงร่วมกันก่อนเริ่ม Phase 3–7:** มาตรฐานที่ใช้ (เช่น วสท. 1008-38 SDM) และตำราที่ใช้เป็นตัวอย่างทดสอบ
บันทึกการตัดสินใจไว้ใน `docs/DECISIONS.md`
