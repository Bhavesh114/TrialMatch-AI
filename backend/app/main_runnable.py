"""
TrialMatch AI — FastAPI Backend
Endpoints: /api/extract-criteria, /api/screen-patient, /api/export-report
"""
import os, json, io, re, tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import anthropic
import fitz  # PyMuPDF
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import datetime

# ─── Config ───────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-6"

app = FastAPI(title="TrialMatch AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ─── Models ───────────────────────────────────────────────────────────────────
class PatientScreenRequest(BaseModel):
    criteria: list[dict]
    patient_summary: str
    trial_id: Optional[str] = "Unknown"
    trial_name: Optional[str] = "Clinical Trial"

class ReportRequest(BaseModel):
    trial_id: Optional[str] = "Unknown"
    trial_name: Optional[str] = "Clinical Trial"
    patient_summary: str
    criteria: list[dict]
    results: list[dict]
    overall_status: str
    meets_count: int
    fails_count: int
    review_count: int

# ─── PDF Text Extraction ───────────────────────────────────────────────────────
def extract_pdf_text(pdf_bytes: bytes) -> tuple[str, str]:
    """Returns (text, method) where method is 'digital' or 'ocr'."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    if len(text.strip()) > 200:
        return text[:40000], "digital"  # cap at ~40k chars

    # Fallback: OCR via fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        blocks = page.get_text("blocks")
        for b in blocks:
            text += b[4] + "\n"
    doc.close()
    return text[:40000], "ocr-fallback"

# ─── Prompts ──────────────────────────────────────────────────────────────────
EXTRACTION_SYSTEM = """You are a clinical trial protocol analyst with deep expertise in FDA regulations and clinical research.
Extract ALL inclusion and exclusion eligibility criteria from the protocol text provided.

For each criterion return a JSON object with these exact fields:
- criterion_id: string (I1, I2... for inclusion; E1, E2... for exclusion)
- type: "inclusion" or "exclusion"
- description: clear plain-language description (1-2 sentences)
- category: one of ["demographics", "diagnosis", "lab_values", "medications", "medical_history", "procedures", "functional_status", "other"]
- data_points_needed: array of strings listing specific data items needed to evaluate this criterion
- logic: string describing any compound conditions (AND/OR/temporal), or "simple" if straightforward

Return ONLY a JSON object: {"criteria": [...array of criterion objects...], "trial_name": "...", "trial_id_hint": "..."}
Be exhaustive — a missed exclusion criterion could mean an ineligible patient gets enrolled."""

SCREENING_SYSTEM = """You are a clinical research screening assistant. Evaluate whether a patient's medical summary meets each eligibility criterion for a clinical trial.

For each criterion assess:
- status: "MEETS" | "DOES_NOT_MEET" | "INSUFFICIENT_DATA"
- confidence: "high" | "medium" | "low"
- reasoning: 2-3 sentences citing specific evidence from the patient summary
- missing_data: array of strings — specific data points needed (only if INSUFFICIENT_DATA)
- follow_up_question: a specific question for the coordinator to ask (only if INSUFFICIENT_DATA or low confidence)

CRITICAL RULES:
1. If in doubt, return INSUFFICIENT_DATA — never guess
2. For exclusion criteria: MEETS means the exclusion is NOT triggered (patient passes)
3. For exclusion criteria: DOES_NOT_MEET means the exclusion IS triggered (patient fails)
4. Always cite specific values from the patient summary in your reasoning
5. Temporal criteria (e.g. "within 6 months") require date information to confirm

Return ONLY a JSON object: {"results": [...array of result objects...], "overall_status": "LIKELY_ELIGIBLE"|"LIKELY_INELIGIBLE"|"NEEDS_REVIEW", "summary": "2-3 sentence overall assessment"}"""

# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.post("/api/extract-criteria")
async def extract_criteria(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > 52_428_800:  # 50MB
        raise HTTPException(400, "File too large (max 50MB)")

    text, method = extract_pdf_text(pdf_bytes)
    if len(text.strip()) < 100:
        raise HTTPException(422, "Could not extract readable text from this PDF")

    # Call Claude
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=EXTRACTION_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Extract all eligibility criteria from this clinical trial protocol:\n\n{text}"
            }]
        )
    except anthropic.APIError as e:
        raise HTTPException(502, f"Claude API error: {str(e)}")

    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise HTTPException(502, "Claude returned malformed JSON")

    return {
        "criteria": data.get("criteria", []),
        "trial_name": data.get("trial_name", file.filename.replace(".pdf", "")),
        "trial_id": data.get("trial_id_hint", ""),
        "extraction_method": method,
        "pages_analyzed": len(pdf_bytes) // 3000,
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
    }


@app.post("/api/screen-patient")
async def screen_patient(req: PatientScreenRequest):
    if not req.criteria:
        raise HTTPException(400, "No criteria provided")
    if not req.patient_summary.strip():
        raise HTTPException(400, "Patient summary is empty")

    criteria_text = json.dumps(req.criteria, indent=2)

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=8192,
            system=SCREENING_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Eligibility criteria:\n{criteria_text}\n\n"
                    f"Patient summary:\n{req.patient_summary}\n\n"
                    "Evaluate this patient against each criterion."
                )
            }]
        )
    except anthropic.APIError as e:
        raise HTTPException(502, f"Claude API error: {str(e)}")

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise HTTPException(502, "Claude returned malformed JSON")

    results = data.get("results", [])
    overall = data.get("overall_status", "NEEDS_REVIEW")
    summary = data.get("summary", "")

    meets = sum(1 for r in results if r.get("status") == "MEETS")
    fails = sum(1 for r in results if r.get("status") == "DOES_NOT_MEET")
    review = sum(1 for r in results if r.get("status") == "INSUFFICIENT_DATA")

    return {
        "results": results,
        "overall_status": overall,
        "summary": summary,
        "meets_count": meets,
        "fails_count": fails,
        "review_count": review,
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
    }


@app.post("/api/export-report")
async def export_report(req: ReportRequest):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle('Title', parent=styles['Title'],
                                  fontSize=18, spaceAfter=4,
                                  textColor=colors.HexColor("#1e1b4b"))
    story.append(Paragraph("TrialMatch AI — Eligibility Screening Report", title_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#6366f1")))
    story.append(Spacer(1, 8))

    # Meta
    meta_style = ParagraphStyle('Meta', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor("#475569"))
    story.append(Paragraph(f"<b>Trial:</b> {req.trial_name} ({req.trial_id})", meta_style))
    story.append(Paragraph(f"<b>Generated:</b> {datetime.datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}", meta_style))
    story.append(Paragraph(f"<b>Report ID:</b> TM-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}", meta_style))
    story.append(Spacer(1, 10))

    # Overall result banner
    status_color = {"LIKELY_ELIGIBLE": "#dcfce7", "LIKELY_INELIGIBLE": "#fee2e2", "NEEDS_REVIEW": "#fef3c7"}
    text_color = {"LIKELY_ELIGIBLE": "#15803d", "LIKELY_INELIGIBLE": "#dc2626", "NEEDS_REVIEW": "#d97706"}
    banner_data = [[
        Paragraph(f'<b>{req.overall_status.replace("_", " ")}</b>', ParagraphStyle('BannerText', parent=styles['Normal'], fontSize=14, textColor=colors.HexColor(text_color.get(req.overall_status, "#374151")), alignment=TA_CENTER)),
        Paragraph(f'<b>Meets:</b> {req.meets_count}  <b>Fails:</b> {req.fails_count}  <b>Review:</b> {req.review_count}', ParagraphStyle('BannerSub', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor("#374151"), alignment=TA_CENTER)),
    ]]
    banner_table = Table(banner_data, colWidths=[3*inch, 4*inch])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(status_color.get(req.overall_status, "#f8fafc"))),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#e2e8f0")),
        ('ROUNDEDCORNERS', [6]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 12))

    # Summary table
    h2_style = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor("#1e293b"), spaceAfter=6)
    story.append(Paragraph("Screening Summary", h2_style))

    table_data = [["ID", "Criterion", "Assessment", "Confidence"]]
    for r in req.results:
        cid = r.get("criterion_id", "")
        # find matching criterion description
        desc = next((c.get("description","") for c in req.criteria if c.get("criterion_id") == cid), cid)
        desc_short = desc[:60] + "..." if len(desc) > 60 else desc
        status = r.get("status", "")
        conf = r.get("confidence", "").capitalize()
        table_data.append([cid, desc_short, status.replace("_", " "), conf])

    t = Table(table_data, colWidths=[0.6*inch, 3.8*inch, 1.6*inch, 1*inch])
    row_colors = {"MEETS": "#dcfce7", "DOES NOT MEET": "#fee2e2", "INSUFFICIENT DATA": "#fef3c7"}
    style_cmds = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#fafafa")]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]
    for i, row in enumerate(table_data[1:], 1):
        bg = row_colors.get(row[2], "#ffffff")
        if bg != "#ffffff":
            style_cmds.append(('BACKGROUND', (2, i), (2, i), colors.HexColor(bg)))
    t.setStyle(TableStyle(style_cmds))
    story.append(t)
    story.append(Spacer(1, 14))

    # Detailed results
    story.append(Paragraph("Detailed Assessments", h2_style))
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor("#374151"))
    label_style = ParagraphStyle('Label', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.HexColor("#1e293b"))

    for r in req.results:
        cid = r.get("criterion_id","")
        desc = next((c.get("description","") for c in req.criteria if c.get("criterion_id") == cid), cid)
        status = r.get("status","")
        conf = r.get("confidence","")
        reasoning = r.get("reasoning","")
        missing = r.get("missing_data", [])
        follow_up = r.get("follow_up_question","")

        status_bg = {"MEETS": "#dcfce7", "DOES_NOT_MEET": "#fee2e2", "INSUFFICIENT_DATA": "#fef3c7"}.get(status, "#f8fafc")

        block = [[
            Paragraph(f"<b>{cid}</b>", label_style),
            Paragraph(desc, body_style),
            Paragraph(f'<b>{status.replace("_"," ")}</b> · {conf.capitalize()} confidence',
                     ParagraphStyle('Stat', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor("#475569")))
        ]]
        if reasoning:
            block.append(["", Paragraph(f"<i>Reasoning:</i> {reasoning}", body_style), ""])
        if missing:
            block.append(["", Paragraph(f"<i>Missing data:</i> {', '.join(missing)}", body_style), ""])
        if follow_up:
            block.append(["", Paragraph(f"<i>Follow-up:</i> {follow_up}", body_style), ""])

        bt = Table(block, colWidths=[0.5*inch, 5.2*inch, 1.3*inch])
        bt.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(status_bg)),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(bt)
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 6))
    disc_style = ParagraphStyle('Disc', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor("#94a3b8"), leading=11)
    story.append(Paragraph(
        "<b>NOT FOR CLINICAL USE.</b> This report is generated by TrialMatch AI for research coordination efficiency only. "
        "It does not constitute clinical advice, a medical decision, or regulatory documentation. "
        "All assessments must be reviewed and verified by qualified clinical personnel before any enrollment action is taken. "
        f"TrialMatch AI v1.0 · Model: {MODEL}",
        disc_style
    ))

    doc.build(story)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=TrialMatch_Report_{req.trial_id}_{datetime.datetime.utcnow().strftime('%Y%m%d')}.pdf"}
    )


# ─── Serve Frontend ───────────────────────────────────────────────────────────
app.mount("/", StaticFiles(directory="static", html=True), name="static")
