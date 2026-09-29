"""Generate the bundled sample tender documents (text + PDF).

Run with the backend virtualenv:
    python3 scripts/create_sample_tenders.py

Produces, under ``data/sample_tenders``:
  * industrial_electrical_control_panel_tender.txt / .pdf   (primary demo)
  * cement_supply_for_concrete_works_tender.txt / .pdf
  * water_supply_upvc_piping_tender.txt / .pdf
  * scanned_tender_image_only.pdf                            (image-only, for the OCR path)
"""

from __future__ import annotations

import textwrap
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_tenders"

CONTROL_PANEL_TENDER = """
TENDER FOR SUPPLY, INSTALLATION AND COMMISSIONING OF INDUSTRIAL ELECTRICAL CONTROL PANEL

Tender Reference No: SISAP/DEMO/CP-2026/01
Issuing Authority: Procurement Division, State Public Works Department (demonstration document)

1. SCOPE OF SUPPLY

1.1 The scope of this tender covers design, manufacture, supply, installation, testing and
commissioning of a floor mounted industrial electrical control panel for a 415 V, 50 Hz, three
phase power distribution and motor control application.

1.2 The control panel shall be suitable for indoor industrial installation and shall house
incoming switchgear, outgoing feeders, busbars, protective devices and a control section.

1.3 The purchaser reserves the right to inspect the panel at the manufacturer's works before
dispatch.

2. TECHNICAL SPECIFICATION

2.1 The control panel shall be a low voltage switchgear and controlgear assembly rated for a
system voltage of 415 V, 50 Hz and a busbar current rating of not less than 800 A.

2.2 The panel shall be designed for a short circuit withstand strength of 50 kA for one second.

2.3 The enclosure shall be fabricated from sheet steel of not less than 2 mm thickness and shall
be provided with a degree of protection of IP54 for indoor use. The enclosure finish shall be
powder coated after phosphate pretreatment.

2.4 Busbars shall be of aluminium or copper and shall be adequately supported to withstand the
short circuit forces. Creepage distances and clearances shall be maintained in accordance with
the applicable standard for the degree of pollution expected.

2.5 Temperature rise limits of all current carrying parts shall be within the limits specified
for the applicable class of equipment.

2.6 The panel shall be provided with an earthing busbar of adequate cross section, and all
metallic parts of the enclosure shall be bonded to the earthing system.

2.7 The ambient conditions at site are: temperature range 5 degrees C to 45 degrees C, relative
humidity up to 95 percent, and altitude below 1000 m above mean sea level.

3. PROTECTIVE DEVICES

3.1 The incoming feeder shall be provided with a moulded case circuit breaker or a switch fuse
unit of suitable breaking capacity.

3.2 Outgoing feeders shall be protected by miniature circuit breakers with suitable current
ratings and tripping characteristics.

3.3 All protective devices shall have a rated short circuit capacity adequate for the fault level
at the point of installation.

4. SAFETY REQUIREMENTS

4.1 The control panel shall provide protection against direct contact and indirect contact in
accordance with the applicable code of practice for electrical installations.

4.2 All doors and covers shall be interlocked or provided with means of preventing inadvertent
contact with live parts.

4.3 Earthing shall be provided in accordance with the applicable code of practice for earthing,
and earth continuity shall be verified before energisation.

4.4 The panel shall be installed with adequate ventilation clearance and shall not obstruct
access for maintenance.

5. TESTING AND INSPECTION

5.1 All routine tests shall be carried out at the manufacturer's works and test certificates
shall be furnished.

5.2 Type test reports for the assembly shall be made available for scrutiny on request.

5.3 A high voltage test and an insulation resistance test shall be performed before the panel is
energised at site.

6. INSTALLATION AND COMMISSIONING

6.1 The panel shall be installed on a foundation suitable for the equipment, with cable entry
from the bottom unless otherwise agreed.

6.2 Cable glands, lugs and terminations shall be provided by the supplier.

6.3 The installation shall be carried out in accordance with the applicable code of practice for
electrical wiring installations.

7. DRAWINGS AND DOCUMENTATION

7.1 The supplier shall furnish dimensional drawings, schematic diagrams and a general
arrangement drawing showing clearances for approval before manufacture.

7.2 As built drawings and an operation and maintenance manual shall be supplied on completion.

8. WARRANTY

8.1 The control panel shall be warranted against defects in material and workmanship for a
period of 24 months from the date of commissioning.

Note for evaluators: this is a demonstration tender prepared for SISAP. It intentionally omits
certain clauses (for example a stated certification requirement) so that the specification gap
detector has something to report.
""".strip()

CEMENT_TENDER = """
TENDER FOR SUPPLY OF PORTLAND POZZOLANA CEMENT FOR CONCRETE WORKS

Tender Reference No: SISAP/DEMO/CEM-2026/02
Issuing Authority: Municipal Engineering Wing (demonstration document)

1. SCOPE OF SUPPLY

1.1 Supply of ordinary Portland cement and Portland pozzolana cement for use in reinforced
concrete and plain concrete works at various sites under the department.

2. TECHNICAL SPECIFICATION

2.1 Cement shall be supplied in bags of 50 kg nominal mass and shall be free from lumps.

2.2 The fineness, soundness, setting time and compressive strength of the cement at 3, 7 and 28
days shall conform to the values specified in the applicable Indian Standard.

2.3 The chemical composition of the cement shall be within the limits specified in the
applicable Indian Standard.

3. TESTING AND SAMPLING

3.1 Samples of cement shall be drawn at the point of delivery and tested for physical and
chemical properties.

3.2 Test certificates shall accompany each consignment.

4. STORAGE AND HANDLING

4.1 Cement shall be stored in a dry, weatherproof shed on a raised platform and used on a
first-in first-out basis.

5. CONCRETE WORKMANSHIP

5.1 Concrete shall be designed for the characteristic compressive strength stated in the
structural drawings and shall be placed, compacted and cured in accordance with the applicable
code of practice.

5.2 Aggregates shall be clean, hard and graded, and shall conform to the applicable standard.

5.3 Reinforcement steel bars shall conform to the applicable standard for high strength
deformed steel bars.

6. SAFETY

6.1 Workers handling cement shall wear appropriate personal protective equipment including eye
protectors and leather gloves.
""".strip()

WATER_TENDER = """
TENDER FOR SUPPLY AND LAYING OF uPVC PRESSURE PIPES FOR WATER SUPPLY

Tender Reference No: SISAP/DEMO/WTR-2026/03
Issuing Authority: Urban Water Supply Board (demonstration document)

1. SCOPE OF WORK

1.1 Supply, laying, jointing, testing and commissioning of unplasticized polyvinyl chloride
(uPVC) pressure pipes for a potable water distribution network.

2. TECHNICAL SPECIFICATION

2.1 Pipes shall be unplasticized PVC pressure pipes of the pressure class stated in the bill of
quantities, suitable for potable water.

2.2 Pipes shall be supplied in standard lengths with spigot and socket ends suitable for solvent
cement jointing.

2.3 The hydrostatic design stress of the pipe material shall be adequate for the design working
pressure with an appropriate factor of safety.

3. INSTALLATION

3.1 Pipes shall be laid in a prepared trench on a bed of approved material with a minimum cover
as specified in the applicable code of practice for laying of service pipes.

3.2 Thrust blocks shall be provided at all bends, tees and valves.

3.3 The pipeline shall be snaked slightly in the trench to accommodate thermal movement.

4. TESTING

4.1 The laid pipeline shall be subjected to a hydrostatic pressure test before being charged.

4.2 The pipeline shall be disinfected and flushed before being put into service.

5. SAFETY

5.1 Trench excavation shall be properly supported and barricaded.

5.2 Workers shall be provided with safety helmets, safety shoes and high visibility clothing.
""".strip()

SCANNED_NOTE = """
This document is an image-only (scanned) PDF. SISAP cannot extract a text layer from it and
reports that OCR is required.
""".strip()


def write_text_files() -> list[Path]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "industrial_electrical_control_panel_tender.txt": CONTROL_PANEL_TENDER,
        "cement_supply_for_concrete_works_tender.txt": CEMENT_TENDER,
        "water_supply_upvc_piping_tender.txt": WATER_TENDER,
    }
    written = []
    for name, content in files.items():
        path = DATA_DIR / name
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
        written.append(path)
    return written


def build_pdfs() -> list[Path]:
    """Render each text tender to PDF using ReportLab (no OCR needed)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TenderTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=14, leading=18, spaceAfter=8
    )
    body = ParagraphStyle(
        "TenderBody", parent=styles["Normal"], fontName="Helvetica", fontSize=9.5, leading=13.5, spaceAfter=5
    )

    written: list[Path] = []
    for text_path in sorted(DATA_DIR.glob("*.txt")):
        output = text_path.with_suffix(".pdf")
        doc = SimpleDocTemplate(
            str(output), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm
        )
        story = []
        for line in text_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                story.append(Spacer(1, 3))
                continue
            style = title if stripped.isupper() and len(stripped) < 90 else body
            story.append(Paragraph(stripped.replace("&", "&amp;").replace("<", "&lt;"), style))
        doc.build(story)
        written.append(output)
    return written


def build_scanned_pdf() -> Path:
    """Create an image-only PDF (no text layer) to exercise the OCR detection path."""
    import pymupdf

    output = DATA_DIR / "scanned_tender_image_only.pdf"
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)

    # Draw shapes and a scanned-page look; crucially, no text is inserted.
    page.draw_rect(pymupdf.Rect(60, 80, 535, 200), color=(0.75, 0.75, 0.75), fill=(0.93, 0.93, 0.93))
    for index in range(12):
        y = 260 + index * 42
        page.draw_line(pymupdf.Point(70, y), pymupdf.Point(520 - index * 12, y), color=(0.6, 0.6, 0.6), width=1.2)
    page.draw_rect(pymupdf.Rect(70, 240, 130, 700), color=(0.6, 0.6, 0.6), fill=None, width=0.8)
    page.draw_circle(pymupdf.Point(500, 740), 18, color=(0.55, 0.55, 0.55), fill=(0.85, 0.85, 0.85))
    document.save(str(output))
    document.close()
    return output


def main() -> None:
    text_files = write_text_files()
    pdfs = build_pdfs()
    scanned = build_scanned_pdf()
    print("Created sample tenders:")
    for path in text_files + pdfs + [scanned]:
        print(f"  {path.relative_to(path.parents[2])}  ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
