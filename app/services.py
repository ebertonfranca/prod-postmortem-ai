import os
import json
import logging
from datetime import datetime
from fastapi import HTTPException
import google.generativeai as genai
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Frame, PageTemplate
from reportlab.lib.units import inch

from app.schemas import AnalyzeRequest, IncidentReport

logger = logging.getLogger(__name__)

# Configure Gemini globally
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    logger.warning("Neither GEMINI_API_KEY nor GOOGLE_API_KEY found in environment.")


async def process_incident_data(request: AnalyzeRequest) -> IncidentReport:
    """Sends incident data to the Gemini model and returns a structured JSON."""
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY or GOOGLE_API_KEY not configured. Set the environment variable.")

    optional_context = []
    if request.time_range:
        optional_context.append(f"Time Range: {request.time_range}")
    if request.affected_services:
        optional_context.append(f"Affected Services: {request.affected_services}")
    if request.impact:
        optional_context.append(f"Impact Classification: {request.impact}")
    if request.key_stakeholders:
        optional_context.append(f"Key Stakeholders: {request.key_stakeholders}")
    if request.customers:
        optional_context.append(f"Affected Customers: {request.customers}")
    
    context_str = "\n".join(optional_context) if optional_context else "None provided."

    prompt = f"""
    You are an expert SRE. Analyze the following incident logs, team transcriptions, and context.
    Generate a post-mortem report in STANDARD JSON format exactly matching this schema.
    DO NOT output markdown, ONLY pure JSON.
    
    [LOGS]
    {request.logs}
    
    [TRANSCRIPTION]
    {request.transcription}

    [ADDITIONAL CONTEXT]
    {context_str}

    Required JSON structure:
    {{
        "executive_summary": {{
            "impact": "description of the impact",
            "root_cause": "description of the root cause",
            "resolution": "description of how it was resolved"
        }},
        "metrics": {{
            "incident_title": "Short title, e.g. Checkout Service Outage",
            "total_downtime": "e.g. 61 minutes",
            "downtime_minutes": 61,
            "service_status": "Resolved",
            "affected_requests": 1247,
            "affected_users": 892
        }},
        "timeline": [
            {{"timestamp": "09:00:00", "event": "Panic started"}}
        ],
        "next_steps": [
            "Implement nil pointer validation",
            "Add integration tests"
        ]
    }}
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
        response = model.generate_content(prompt)
        report_data = json.loads(response.text)
        return IncidentReport.model_validate(report_data)
    except Exception as e:
        logger.error(f"Error invoking Gemini: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- ReportLab PDF Engine ---

class ReportGenerator:
    def __init__(self, request: AnalyzeRequest):
        self.request = request
        self.styles = getSampleStyleSheet()
        
        # Define Custom Styles to match the Premium Retro / Executive Look
        self.styles.add(ParagraphStyle(name='HeaderLeft', parent=self.styles['Normal'], fontSize=16, leading=20, textColor=colors.whitesmoke, fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='HeaderRight', parent=self.styles['Normal'], fontSize=10, leading=14, textColor=colors.whitesmoke, alignment=2))
        
        self.styles.add(ParagraphStyle(name='MainTitle', parent=self.styles['Title'], fontSize=28, leading=34, textColor=colors.HexColor("#1D4ED8"), alignment=0, spaceAfter=2))
        self.styles.add(ParagraphStyle(name='SubTitle', parent=self.styles['Normal'], fontSize=16, leading=22, textColor=colors.HexColor("#4B5563"), spaceAfter=20))
        
        self.styles.add(ParagraphStyle(name='CardTitle', parent=self.styles['Normal'], fontSize=11, leading=14, textColor=colors.HexColor("#6B7280"), fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='CardValue', parent=self.styles['Normal'], fontSize=22, leading=28, textColor=colors.HexColor("#111827"), fontName='Helvetica-Bold', spaceBefore=6, spaceAfter=6))
        self.styles.add(ParagraphStyle(name='CardValueGreen', parent=self.styles['Normal'], fontSize=22, leading=28, textColor=colors.HexColor("#10B981"), fontName='Helvetica-Bold', spaceBefore=6, spaceAfter=6))
        self.styles.add(ParagraphStyle(name='CardSub', parent=self.styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor("#9CA3AF")))
        
        self.styles.add(ParagraphStyle(name='SectionTitle', parent=self.styles['Heading2'], fontSize=16, leading=20, textColor=colors.HexColor("#1D4ED8"), spaceAfter=10))
        self.styles.add(ParagraphStyle(name='ExecText', parent=self.styles['Normal'], fontSize=11, leading=16, textColor=colors.HexColor("#374151"), spaceAfter=14))
        
        self.styles.add(ParagraphStyle(name='SlaPercent', parent=self.styles['Normal'], fontSize=34, leading=40, textColor=colors.HexColor("#111827"), fontName='Helvetica-Bold', alignment=1))
        self.styles.add(ParagraphStyle(name='SlaLabel', parent=self.styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor("#6B7280"), fontName='Helvetica-Bold', alignment=1, spaceAfter=15))
        self.styles.add(ParagraphStyle(name='NextStepBullet', parent=self.styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor("#4B5563"), spaceAfter=8))


    def _header_footer(self, canvas, doc):
        canvas.saveState()
        # Draw Dark Top Header background
        canvas.setFillColor(colors.HexColor("#0F172A"))
        canvas.rect(0, 720, letter[0], 100, fill=1, stroke=0)
        
        # Draw Header Text
        canvas.setFillColor(colors.whitesmoke)
        canvas.setFont("Helvetica-Bold", 18)
        canvas.drawString(40, 755, "PROD POST-MORTEM AI")
        canvas.setFont("Helvetica", 12)
        canvas.drawString(275, 755, "EXECUTIVE REPORT")
        
        # Right aligned
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawRightString(letter[0] - 40, 765, "CONFIDENTIAL")
        canvas.setFont("Helvetica", 10)
        canvas.drawRightString(letter[0] - 40, 750, f"Generated: {datetime.now().strftime('%B %d, %Y')}")
        
        canvas.restoreState()

    def generate_pdf(self, report: IncidentReport) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=85, bottomMargin=40)
        elements = []

        # 1. Main Titles
        elements.append(Paragraph("Incident Report", self.styles['MainTitle']))
        elements.append(Paragraph(report.metrics.incident_title, self.styles['SubTitle']))
        elements.append(Spacer(1, 10))

        # 2. Big Numbers Cards (Retro style borders)
        cards_data = []
        metrics = report.metrics

        def create_card(title, value, sub, color_val=False):
            val_style = self.styles['CardValueGreen'] if color_val else self.styles['CardValue']
            return [
                Paragraph(title, self.styles['CardTitle']),
                Paragraph(value, val_style),
                Paragraph(sub, self.styles['CardSub'])
            ]

        card1 = create_card("Affected Users", f"{metrics.affected_users:,}", "Users impacted during incident")
        card2 = create_card("Downtime / MTTR", f"{metrics.total_downtime}", "Total service disruption time")
        card3 = create_card("Service Status", f"{metrics.service_status}", "Current status", color_val=(metrics.service_status.lower()=="resolved"))
        row1 = [card1, card2, card3]
        
        # Customers block if provided
        if self.request.customers:
            card4 = create_card("Affected Customers", self.request.customers, "Identified client blast radius")
            row1.append(card4)

        card_width = (letter[0] - 80) / len(row1)
        cards_table = Table([row1], colWidths=[card_width]*len(row1))
        
        card_style = [
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (0, 0), 0.5, colors.HexColor("#D1D5DB")),
            ('BOX', (1, 0), (1, 0), 0.5, colors.HexColor("#D1D5DB")),
            ('BOX', (2, 0), (2, 0), 0.5, colors.HexColor("#D1D5DB")),
            ('PADDING', (0, 0), (-1, -1), 12),
        ]
        if len(row1) == 4:
            card_style.append(('BOX', (3, 0), (3, 0), 0.5, colors.HexColor("#D1D5DB")))
            
        # Add gaps between cards using frame inner spacing via Table nesting, or just draw basic grid.
        # Spacing is best achieved by empty columns, but for simplicity we draw inner grids light
        cards_table.setStyle(TableStyle(card_style))
        elements.append(cards_table)
        elements.append(Spacer(1, 15))

        # 3. Two columns: Left (Execution Summary Impact) | Right (SLA)
        # Calculate SLA:
        sla_hours = self.request.sla_hours
        sla_max_minutes = sla_hours * 60
        actual_minutes = metrics.downtime_minutes
        
        sla_percent = min(100, round((actual_minutes / sla_max_minutes) * 100)) if sla_max_minutes > 0 else 0
        sla_color = "#10B981" if sla_percent < 50 else ("#F59E0B" if sla_percent < 80 else "#EF4444")
        
        left_col = [
            Paragraph("Executive Summary", self.styles['SectionTitle']),
            Paragraph(f"<b>Impact:</b> {report.executive_summary.impact}", self.styles['ExecText'])
        ]
        
        sla_circle_val = Paragraph(f"<font color='{sla_color}'>{sla_percent}%</font>", self.styles['SlaPercent'])
        right_col = [
            Spacer(1, 5),
            sla_circle_val,
            Paragraph("SLA BUDGET USED", self.styles['SlaLabel'])
        ]
        
        col_width1 = 360
        col_width2 = 160
        summary_table = Table([[left_col, right_col]], colWidths=[col_width1, col_width2])
        summary_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('BOX', (0, 0), (0, 0), 0.5, colors.HexColor("#E5E7EB")),
            ('BOX', (1, 0), (1, 0), 0.5, colors.HexColor("#E5E7EB")),
            ('PADDING', (0, 0), (-1, -1), 15)
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 15))
        
        # Rest of Executive Summary (extracted to avoid page-break jumps on long texts)
        elements.append(Paragraph(f"<b>Root Cause:</b> {report.executive_summary.root_cause}", self.styles['ExecText']))
        elements.append(Paragraph(f"<b>Resolution:</b> {report.executive_summary.resolution}", self.styles['ExecText']))
        elements.append(Spacer(1, 15))

        elements.append(Paragraph("Suggested Next Steps", self.styles['SectionTitle']))
        for step in report.next_steps:
            elements.append(Paragraph(f"• {step}", self.styles['NextStepBullet']))
        
        elements.append(Spacer(1, 20))

        # 4. Timeline
        elements.append(Paragraph("Team Response Timeline", self.styles['SectionTitle']))
        timeline_data = [["Timestamp", "Decision / Event"]]
        for event in report.timeline:
            timeline_data.append([event.timestamp, event.event])

        timeline_table = Table(timeline_data, colWidths=[120, 400])
        timeline_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#374151")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(timeline_table)

        # Build PDF
        doc.build(elements, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
