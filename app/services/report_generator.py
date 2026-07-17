import logging
from typing import Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import (
    HexColor, white, black
)
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO

logger = logging.getLogger(__name__)

# ─── Color Palette ────────────────────────────────────────
PRIMARY = HexColor('#2563EB')      # Blue
SECONDARY = HexColor('#1E40AF')    # Dark Blue
SUCCESS = HexColor('#16A34A')      # Green
WARNING = HexColor('#D97706')      # Orange
DANGER = HexColor('#DC2626')       # Red
LIGHT_BG = HexColor('#F1F5F9')    # Light Gray
DARK_TEXT = HexColor('#1E293B')    # Dark Text
MUTED_TEXT = HexColor('#64748B')   # Muted Text


class ReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            fontSize=24,
            fontName='Helvetica-Bold',
            textColor=white,
            alignment=TA_CENTER,
            spaceAfter=6,
        ))

        # Section heading style
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            fontSize=13,
            fontName='Helvetica-Bold',
            textColor=PRIMARY,
            spaceBefore=12,
            spaceAfter=6,
        ))

        # Body text style
        self.styles.add(ParagraphStyle(
            name='BodyText2',
            fontSize=10,
            fontName='Helvetica',
            textColor=DARK_TEXT,
            spaceAfter=4,
            leading=14,
        ))

        # Muted text style
        self.styles.add(ParagraphStyle(
            name='MutedText',
            fontSize=9,
            fontName='Helvetica',
            textColor=MUTED_TEXT,
            spaceAfter=4,
        ))

        # Score style
        self.styles.add(ParagraphStyle(
            name='ScoreText',
            fontSize=36,
            fontName='Helvetica-Bold',
            textColor=white,
            alignment=TA_CENTER,
        ))

        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='SubTitle',
            fontSize=11,
            fontName='Helvetica',
            textColor=white,
            alignment=TA_CENTER,
        ))

    def _get_score_color(self, score: float) -> HexColor:
        """Return color based on score value"""
        if score >= 80:
            return SUCCESS
        elif score >= 60:
            return WARNING
        else:
            return DANGER

    def _build_header(self, analysis: Dict) -> list:
        """Build report header section"""
        elements = []

        ats_score = analysis.get('ats_score')
        ai_powered = analysis.get('ai_powered', False)

        # Header background table
        score_display = f"{int(ats_score)}%" if ats_score is not None else "N/A"
        score_color = self._get_score_color(float(ats_score)) if ats_score is not None else MUTED_TEXT

        header_data = [[
            Paragraph("AI Resume Analyzer", self.styles['ReportTitle']),
        ]]

        header_table = Table(header_data, colWidths=[7 * inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), PRIMARY),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 20),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('ROUNDEDCORNERS', [8, 8, 8, 8]),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.2 * inch))

        # ATS Score card
        score_data = [[
            Paragraph(score_display, self.styles['ScoreText']),
        ], [
            Paragraph("ATS Score", self.styles['SubTitle']),
        ]]

        score_table = Table(score_data, colWidths=[7 * inch])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), score_color),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ]))
        elements.append(score_table)
        elements.append(Spacer(1, 0.1 * inch))

        # AI powered badge
        badge_text = "✓ AI Powered Analysis" if ai_powered else "⚠ Basic Analysis (AI Unavailable)"
        badge_color = SUCCESS if ai_powered else WARNING

        badge_data = [[Paragraph(badge_text, ParagraphStyle(
            name='Badge',
            fontSize=9,
            fontName='Helvetica-Bold',
            textColor=white,
            alignment=TA_CENTER,
        ))]]

        badge_table = Table(badge_data, colWidths=[2.5 * inch])
        badge_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), badge_color),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        # Center the badge
        wrapper = Table([[badge_table]], colWidths=[7 * inch])
        wrapper.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(wrapper)
        elements.append(Spacer(1, 0.3 * inch))

        return elements

    def _build_section_scores(self, analysis: Dict) -> list:
        """Build section scores table"""
        elements = []

        section_scores = analysis.get('section_scores', {})
        if not section_scores:
            return elements

        elements.append(
            Paragraph("Section Scores", self.styles['SectionHeading'])
        )
        elements.append(
            HRFlowable(width="100%", thickness=1, color=PRIMARY)
        )
        elements.append(Spacer(1, 0.1 * inch))

        # Build table data
        table_data = [['Section', 'Score', 'Rating']]

        for section, score in section_scores.items():
            try:
                score_val = float(score)
            except (ValueError, TypeError):
                score_val = 0.0

            if score_val >= 80:
                rating = "Excellent"
                color = SUCCESS
            elif score_val >= 60:
                rating = "Good"
                color = WARNING
            else:
                rating = "Needs Work"
                color = DANGER

            table_data.append([
                section.capitalize(),
                f"{int(score_val)}%",
                rating
            ])

        score_table = Table(
            table_data,
            colWidths=[3 * inch, 1.5 * inch, 2.5 * inch]
        )
        score_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), SECONDARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_BG]),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, MUTED_TEXT),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(score_table)
        elements.append(Spacer(1, 0.2 * inch))

        return elements

    def _build_list_section(
        self,
        title: str,
        items: list,
        bullet: str = "•",
        color: HexColor = PRIMARY
    ) -> list:
        """Build a bullet list section"""
        elements = []

        if not items:
            return elements

        elements.append(
            Paragraph(title, self.styles['SectionHeading'])
        )
        elements.append(
            HRFlowable(width="100%", thickness=1, color=color)
        )
        elements.append(Spacer(1, 0.05 * inch))

        for item in items:
            if item:
                elements.append(
                    Paragraph(
                        f"{bullet} {item}",
                        self.styles['BodyText2']
                    )
                )

        elements.append(Spacer(1, 0.15 * inch))
        return elements

    def _build_feedback_section(self, analysis: Dict) -> list:
        """Build detailed feedback section"""
        elements = []

        detailed_feedback = analysis.get('detailed_feedback', {})
        if not detailed_feedback:
            return elements

        elements.append(
            Paragraph("Detailed Feedback", self.styles['SectionHeading'])
        )
        elements.append(
            HRFlowable(width="100%", thickness=1, color=PRIMARY)
        )
        elements.append(Spacer(1, 0.05 * inch))

        for key, value in detailed_feedback.items():
            if value:
                elements.append(
                    Paragraph(
                        f"<b>{key.capitalize()}:</b>",
                        self.styles['BodyText2']
                    )
                )
                elements.append(
                    Paragraph(str(value), self.styles['BodyText2'])
                )
                elements.append(Spacer(1, 0.05 * inch))

        elements.append(Spacer(1, 0.15 * inch))
        return elements

    def _build_summary_section(self, analysis: Dict) -> list:
        """Build rewritten summary section"""
        elements = []

        summary = analysis.get('rewritten_summary', '')
        if not summary:
            return elements

        elements.append(
            Paragraph("AI Suggested Summary", self.styles['SectionHeading'])
        )
        elements.append(
            HRFlowable(width="100%", thickness=1, color=PRIMARY)
        )
        elements.append(Spacer(1, 0.05 * inch))

        # Summary box
        summary_data = [[Paragraph(summary, self.styles['BodyText2'])]]
        summary_table = Table(summary_data, colWidths=[6.8 * inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('BOX', (0, 0), (-1, -1), 1, PRIMARY),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.2 * inch))

        return elements

    def _build_footer(self) -> list:
        """Build report footer"""
        elements = []

        elements.append(HRFlowable(width="100%", thickness=1, color=MUTED_TEXT))
        elements.append(Spacer(1, 0.05 * inch))
        elements.append(
            Paragraph(
                "Generated by AI Resume Analyzer | Powered by Google Gemini",
                self.styles['MutedText']
            )
        )
        return elements

    def generate_pdf_report(self, analysis: Dict) -> bytes:
        """
        Generate a complete PDF report from analysis data
        Returns PDF as bytes
        """
        if not analysis:
            logger.warning("⚠️ Empty analysis data provided to report generator")
            analysis = {}

        try:
            buffer = BytesIO()

            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=0.75 * inch,
                leftMargin=0.75 * inch,
                topMargin=0.75 * inch,
                bottomMargin=0.75 * inch,
            )

            # Build all sections
            elements = []

            # 1. Header with ATS Score
            elements.extend(self._build_header(analysis))

            # 2. Section Scores Table
            elements.extend(self._build_section_scores(analysis))

            # 3. Strengths
            elements.extend(self._build_list_section(
                title="✅ Strengths",
                items=analysis.get('strengths', []),
                color=SUCCESS
            ))

            # 4. Areas for Improvement
            elements.extend(self._build_list_section(
                title="🔧 Areas for Improvement",
                items=analysis.get('improvements', []),
                color=WARNING
            ))

            # 5. Missing Keywords
            elements.extend(self._build_list_section(
                title="🔍 Missing Keywords",
                items=analysis.get('missing_keywords', []),
                color=DANGER
            ))

            # 6. Suggested Roles
            elements.extend(self._build_list_section(
                title="💼 Suggested Roles",
                items=analysis.get('suggested_roles', []),
                color=PRIMARY
            ))

            # 7. AI Suggested Summary
            elements.extend(self._build_summary_section(analysis))

            # 8. Detailed Feedback
            elements.extend(self._build_feedback_section(analysis))

            # 9. Footer
            elements.extend(self._build_footer())

            # Build PDF
            doc.build(elements)

            pdf_bytes = buffer.getvalue()
            buffer.close()

            logger.info("✅ PDF report generated successfully")
            return pdf_bytes

        except Exception as e:
            logger.error(f"❌ PDF generation failed: {e}")
            raise ValueError(f"Could not generate PDF report: {e}")