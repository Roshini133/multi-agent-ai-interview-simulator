"""PDF report generation (ReportLab)."""
from __future__ import annotations

import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BLUE, DARK, LIGHT, TEXT = colors.HexColor("#1565C0"), colors.HexColor("#0D47A1"), colors.HexColor("#E3F2FD"), colors.HexColor("#172B4D")
AGENT_TITLES = {"hr": "HR", "technical": "Technical", "manager": "Manager"}


def _styles():
    ss = getSampleStyleSheet()
    base = ParagraphStyle("base", parent=ss["Normal"], fontName="Helvetica", fontSize=9.5, leading=13.5, textColor=TEXT)
    return {
        "base": base,
        "title": ParagraphStyle("title", parent=base, fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=DARK),
        "sub": ParagraphStyle("sub", parent=base, fontSize=10.5, textColor=colors.HexColor("#5E6C84")),
        "h1": ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=BLUE, spaceBefore=14, spaceAfter=6, keepWithNext=1),
        "h2": ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=10.5, textColor=DARK, spaceBefore=6, spaceAfter=2, keepWithNext=1),
        "small": ParagraphStyle("small", parent=base, fontSize=8, leading=11, textColor=colors.HexColor("#5E6C84")),
        "bullet": ParagraphStyle("bullet", parent=base, leftIndent=10, bulletIndent=0),
    }


def _p(text, style):
    return Paragraph(escape(str(text if text is not None else "-")), style)


def _bullets(items, st):
    return [Paragraph(escape(str(i)), st["bullet"], bulletText="\u2022") for i in items] or [_p("None recorded.", st["base"])]


def _fmt_duration(sec: int) -> str:
    return f"{sec // 60} min {sec % 60} s"


def _table(rows, widths, header=True):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 9), ("TEXTCOLOR", (0, 0), (-1, -1), TEXT),
             ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DFE1E6")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), BLUE), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    t.setStyle(TableStyle(style))
    return t


def _bar_chart(cats: dict, labels: dict) -> Drawing:
    items = [(labels[k], v) for k, v in cats.items() if v is not None]
    d = Drawing(170 * mm, max(40, 18 * len(items) + 20))
    chart = HorizontalBarChart()
    chart.x, chart.y, chart.width, chart.height = 90 * mm - 20, 8, 80 * mm, d.height - 16
    chart.data = [[v for _, v in items][::-1]]
    chart.categoryAxis.categoryNames = [n for n, _ in items][::-1]
    chart.valueAxis.valueMin, chart.valueAxis.valueMax, chart.valueAxis.valueStep = 0, 100, 25
    chart.bars[0].fillColor = BLUE
    chart.categoryAxis.labels.fontSize = chart.valueAxis.labels.fontSize = 8
    chart.categoryAxis.labels.dx = -4
    d.add(chart)
    return d


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#5E6C84"))
    canvas.drawString(18 * mm, 10 * mm, "AI Interview Simulator - practice assessment, not an employment decision")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf(report: dict) -> bytes:
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                            title="Interview Report", author="AI Interview Simulator")
    W = A4[0] - 36 * mm
    s: list = []
    scores = report["scores"]
    s += [_p("AI Interview Simulator", st["sub"]), _p("Interview Performance Report", st["title"]), Spacer(1, 4), HRFlowable(width="100%", color=BLUE, thickness=1.5), Spacer(1, 6)]
    date = datetime.fromisoformat(report["date"]).strftime("%d %b %Y, %H:%M")
    meta = [["Candidate", report["candidate"]["name"], "Role", report["role_label"]],
            ["Interview date", date, "Duration", _fmt_duration(report["duration_seconds"])],
            ["Questions answered", f"{report['questions_answered']} / {report['total_questions']}", "Overall score", f"{scores['overall'] if scores['overall'] is not None else 'n/a'} / 100"]]
    s += [_table(meta, [32 * mm, 52 * mm, 30 * mm, W - 114 * mm], header=False)]

    s += [_p("Executive summary", st["h1"]), _p(report.get("executive_summary", ""), st["base"]),
          _p(f"Readiness level (practice): {report.get('readiness', '-')}", st["h2"])]

    s += [_p("Score breakdown", st["h1"])]
    rows = [["Category", "Score (/100)", "Weight"]] + [[scores["category_labels"][k], "n/a" if v is None else v, f"{int(scores['weights'][k] * 100)}%"] for k, v in scores["categories"].items()]
    s += [_table(rows, [80 * mm, 40 * mm, 30 * mm]), Spacer(1, 6), _bar_chart(scores["categories"], scores["category_labels"]), Spacer(1, 10), _p(scores["method"], st["small"])]

    comp = [["Competency", "Average (/10)"]] + [[k.replace("_", " ").title(), "n/a" if v is None else v] for k, v in scores["competencies"].items()]
    s += [_p("Competency averages", st["h2"]), _table(comp, [80 * mm, 40 * mm])]

    s += [_p("Panel evaluation", st["h1"])]
    for key in ("hr", "technical", "manager"):
        r = report["agent_reviews"][key]
        s += [KeepTogether([_p(f"{r['title']} - {r['name']}  |  score: {r['score'] if r['score'] is not None else 'n/a'}", st["h2"]), _p(r["summary"], st["base"])])]
    s += [_p("Panel discussion", st["h2"])]
    for d in report["panel"]["discussion"]:
        s += [Paragraph(f"<b>{escape(d['speaker'])}:</b> {escape(d['message'])}", st["base"]), Spacer(1, 2)]
    s += [_p("Final panel assessment", st["h2"]), _p(report["panel"]["final_assessment"], st["base"])]
    if report["panel"].get("disagreement"):
        s += [_p("Note: " + report["panel"]["disagreement"], st["small"])]

    s += [_p("Strengths", st["h1"])] + _bullets(scores["strengths"] or ["No metric averaged 7/10 or above."], st)
    s += [_p("Weaknesses and improvement areas", st["h1"])] + _bullets(scores["improvements"] or ["No major weaknesses identified."], st)
    rec = report["recommendations"]
    s += [_p("Recommended preparation", st["h1"]), _p("Technical topics to study", st["h2"])] + _bullets(rec["technical_topics"], st)
    s += [_p("Communication suggestions", st["h2"])] + _bullets(rec["communication"], st) + [_p("Behavioral suggestions", st["h2"])] + _bullets(rec["behavioral"], st)

    sp = report["speech_summary"]
    s += [_p("Delivery metrics", st["h1"]), _p(f"Total words: {sp['total_words']} | Avg words/answer: {sp['avg_words_per_answer']} | Filler words: {sp['total_fillers']} | Avg pace: {sp['avg_words_per_minute'] or 'n/a'} wpm | Voice answers: {sp['voice_answers']}", st["base"]), _p(sp["note"], st["small"])]
    s += [_p("Resume-based observations", st["h1"])] + _bullets(report["resume_observations"], st)

    integ = report["integrity"]
    s += [_p("Behavioral observation & integrity signals", st["h1"])]
    rows = [["Observed signal", "Events"]] + [[x["label"], x["count"]] for x in integ["signals"]]
    ratio = integ["screen_attention_ratio"]
    s += [_table(rows, [110 * mm, 30 * mm]), Spacer(1, 4),
          _p(f"Approximate screen attention ratio: {'n/a' if ratio is None else str(round(ratio * 100)) + '%'} ({integ['samples_analyzed']} samples analysed)", st["base"])]
    s += _bullets(integ["observations"], st) + [Spacer(1, 3), _p("IMPORTANT: " + integ["disclaimer"], st["small"])]

    s += [PageBreak(), _p("Question-by-question analysis", st["h1"])]
    for q in report["questions"]:
        head = f"Q{q['index']} - {AGENT_TITLES[q['agent']]} | {q['difficulty']} | topic: {(q['topic'] or '-').replace('_', ' ')} | score {round(q['overall'] * 10)}/100"
        metrics = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in q["scores"].items() if isinstance(v, (int, float)) and k not in ("word_count", "resume_alignment"))
        s += [KeepTogether([_p(head, st["h2"]), _p("Question: " + q["question"], st["base"]), _p("Answer: " + q["answer"][:900], st["base"]),
                            _p("Metrics: " + metrics, st["small"]), _p("Feedback: " + (q["feedback"] or "-"), st["base"]), _p("Improve: " + (q["improvement"] or "-"), st["base"]), Spacer(1, 6)])]

    s += [_p("Methodology & disclaimers", st["h1"]), _p("AI components used", st["h2"])] + _bullets(
        [f"Pretrained models: {'; '.join(report['ai_components']['pretrained_models'])}", f"Deterministic algorithms: {'; '.join(report['ai_components']['deterministic_algorithms'])}",
         f"Scoring logic: {'; '.join(report['ai_components']['scoring_logic'])}"], st)
    s += [Spacer(1, 4)] + _bullets(report["disclaimers"], st)
    doc.build(s, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
