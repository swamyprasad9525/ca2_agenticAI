import io
import csv
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether

from backend.app.services.scorecard_service import ScorecardService
from backend.app.schemas.scorecard import SharedScorecardResponse
from backend.app.schemas.award import AwardRecommendationDTO


class ReportService:
    """Generates official procurement audit reports in PDF, CSV, and JSON formats."""

    def __init__(self, scorecard_service: ScorecardService):
        self.scorecard_service = scorecard_service

    async def generate_pdf_report(self, run_id: str) -> bytes:
        """Constructs an enterprise-grade procurement evaluation PDF report."""
        scorecard = await self.scorecard_service.get_shared_scorecard(run_id)
        recommendation = await self.scorecard_service.get_award_recommendation(run_id)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1e3a8a"),  # Navy blue
            spaceAfter=6,
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#4b5563"),
            spaceAfter=15,
        )
        h2_style = ParagraphStyle(
            "Heading2Custom",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#1e3a8a"),
            spaceBefore=12,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "BodyCustom",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#1f2937"),
        )
        winner_box_style = ParagraphStyle(
            "WinnerBox",
            parent=styles["Normal"],
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#065f46"),
            backColor=colors.HexColor("#d1fae5"),
            borderColor=colors.HexColor("#10b981"),
            borderWidth=1,
            borderPadding=8,
            spaceAfter=12,
        )

        elements = []

        # 1. Header
        elements.append(Paragraph("TENDER EVALUATION & AWARD RECOMMENDATION REPORT", title_style))
        elements.append(Paragraph(
            f"<b>Evaluation Run ID:</b> {run_id} &nbsp;|&nbsp; "
            f"<b>Tender ID:</b> {scorecard.tender_id} &nbsp;|&nbsp; "
            f"<b>Date:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            subtitle_style,
        ))
        elements.append(Spacer(1, 8))

        # 2. Executive Recommendation Callout Box
        winner_name = recommendation.recommended_vendor_name if recommendation and recommendation.recommended_vendor_name else "No Eligible Vendor"
        winner_score = f"{recommendation.winning_composite_score:.2f}/100.00" if recommendation and recommendation.winning_composite_score else "N/A"
        winner_status = recommendation.status.value if recommendation else "INCOMPLETE"

        elements.append(Paragraph(
            f"<b>RECOMMENDED CONTRACT AWARD:</b> {winner_name}<br/>"
            f"<b>Composite Evaluation Score:</b> {winner_score} &nbsp;|&nbsp; "
            f"<b>Status:</b> {winner_status}",
            winner_box_style,
        ))

        # 3. Executive Summary
        if recommendation and recommendation.executive_summary:
            elements.append(Paragraph("1. Executive Summary", h2_style))
            elements.append(Paragraph(recommendation.executive_summary, body_style))
            elements.append(Spacer(1, 8))

        # 4. Award Justification
        if recommendation and recommendation.award_justification:
            elements.append(Paragraph("2. Award Justification & Strengths", h2_style))
            elements.append(Paragraph(recommendation.award_justification, body_style))
            elements.append(Spacer(1, 8))

        # 5. Composite Scorecard Table
        elements.append(Paragraph("3. Ranked Vendor Scorecard", h2_style))
        table_data = [
            ["Rank", "Vendor Name", "Compliance", "Tech Score", "Comm Price", "Composite", "Outcome"]
        ]

        for s in scorecard.vendor_summaries:
            rank_str = f"#{s.rank}" if s.rank is not None else "-"
            comp_score_str = f"{s.composite_score:.2f}" if s.composite_score is not None else "0.00"
            price_str = f"{s.commercial_score.raw_points:,.0f}" if s.commercial_score and s.commercial_score.raw_points else "N/A"
            tech_total = sum((t.weighted_score for t in s.technical_scores if t.weighted_score is not None), Decimal("0.0"))
            outcome = "Disqualified" if s.is_disqualified else ("Review" if s.requires_human_review else "Eligible")

            table_data.append([
                rank_str,
                s.vendor_name[:24],
                s.compliance_status,
                f"{tech_total:.1f}",
                price_str,
                comp_score_str,
                outcome,
            ])

        col_widths = [35, 150, 75, 60, 75, 60, 75]
        score_table = Table(table_data, colWidths=col_widths)
        score_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (1, 1), (1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ]))
        elements.append(score_table)
        elements.append(Spacer(1, 10))

        # 6. Risk Assessment
        if recommendation and recommendation.risk_assessment:
            elements.append(Paragraph("4. Procurement Risk Assessment", h2_style))
            for risk in recommendation.risk_assessment:
                elements.append(Paragraph(f"• {risk}", body_style))
            elements.append(Spacer(1, 8))

        # 7. Human Governance Sign-Off Section
        elements.append(KeepTogether([
            Paragraph("5. Formal Human Governance Sign-Off", h2_style),
            Paragraph(
                "In compliance with statutory public procurement regulations and internal corporate governance mandates, "
                "this AI-assisted evaluation constitutes an objective technical and commercial recommendation. "
                "The legal decision to execute a binding contract remains strictly with the designated procurement authority.",
                body_style,
            ),
            Spacer(1, 15),
            Table([
                ["Authorized Procurement Officer:", "_____________________________________"],
                ["Official Title / Role:", "_____________________________________"],
                ["Formal Decision (Approve / Override / Reject):", "_____________________________________"],
                ["Signature & Official Stamp:", "_____________________________________"],
                ["Date of Execution:", "_____________________________________"],
            ], colWidths=[220, 280], style=[
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ])
        ]))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    async def generate_csv_report(self, run_id: str) -> str:
        """Constructs a standard CSV export of the complete scorecard."""
        scorecard = await self.scorecard_service.get_shared_scorecard(run_id)

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Rank",
            "Vendor ID",
            "Vendor Name",
            "Compliance Status",
            "Is Disqualified",
            "Requires Human Review",
            "Technical Score",
            "Commercial Price",
            "Normalized Commercial Score",
            "Composite Score",
            "Disqualification Reasons",
        ])

        for s in scorecard.vendor_summaries:
            tech_total = sum((t.weighted_score for t in s.technical_scores if t.weighted_score is not None), Decimal("0.0"))
            price_val = str(s.commercial_score.raw_points) if s.commercial_score and s.commercial_score.raw_points else ""
            norm_comm = str(s.commercial_score.normalized_score) if s.commercial_score and s.commercial_score.normalized_score else ""
            comp_val = str(s.composite_score) if s.composite_score is not None else ""

            writer.writerow([
                s.rank if s.rank is not None else "",
                s.vendor_id,
                s.vendor_name,
                s.compliance_status,
                s.is_disqualified,
                s.requires_human_review,
                f"{tech_total:.2f}",
                price_val,
                norm_comm,
                comp_val,
                "; ".join(s.disqualification_reasons),
            ])

        return output.getvalue()

    async def generate_json_report(self, run_id: str) -> Dict[str, Any]:
        """Constructs a comprehensive JSON dump of the entire evaluation lifecycle."""
        scorecard = await self.scorecard_service.get_shared_scorecard(run_id)
        recommendation = await self.scorecard_service.get_award_recommendation(run_id)

        return {
            "evaluation_run_id": run_id,
            "tender_id": scorecard.tender_id,
            "status": scorecard.status,
            "current_step": scorecard.current_step,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "award_recommendation": recommendation.model_dump(mode="json") if recommendation else None,
            "scorecard": scorecard.model_dump(mode="json"),
        }

