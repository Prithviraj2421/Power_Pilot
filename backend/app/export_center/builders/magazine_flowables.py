from reportlab.lib import colors
from reportlab.platypus import Flowable


class HeroKPICard(Flowable):
    """
    ReportLab visual flowable rendering large hero KPI callouts
    ($152.4K Revenue, 95.8% Quality Grade) with colored accent bars,
    trend indicators, and confidence labels.
    """

    def __init__(
        self,
        title: str,
        value: str,
        subtitle: str = "",
        accent_color: str = "#1E3A8A",
        bg_color: str = "#F8FAFC",
        width: float = 170,
        height: float = 80,
    ) -> None:
        super().__init__()
        self.title = title
        self.value = value
        self.subtitle = subtitle
        self.accent_color = colors.HexColor(accent_color)
        self.bg_color = colors.HexColor(bg_color)
        self.card_width = width
        self.card_height = height

    def wrap(self, availWidth, availHeight):
        return self.card_width, self.card_height

    def draw(self):
        c = self.canv
        c.saveState()

        # Background card fill & border
        c.setFillColor(self.bg_color)
        c.setStrokeColor(colors.HexColor("#E5E7EB"))
        c.setLineWidth(1)
        c.roundRect(0, 0, self.card_width, self.card_height, 6, fill=1, stroke=1)

        # Left Accent Bar
        c.setFillColor(self.accent_color)
        c.rect(0, 0, 5, self.card_height, fill=1, stroke=0)

        # Title Label
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.HexColor("#6B7280"))
        c.drawString(14, self.card_height - 18, self.title.upper())

        # Hero Value
        c.setFont("Helvetica-Bold", 18)
        c.setFillColor(colors.HexColor("#1F2937"))
        c.drawString(14, self.card_height - 44, self.value)

        # Subtitle / Trend
        if self.subtitle:
            c.setFont("Helvetica", 8)
            c.setFillColor(colors.HexColor("#10B981"))
            c.drawString(14, 12, self.subtitle)

        c.restoreState()


class McKinsey4PartBox(Flowable):
    """
    Editorial box rendering the 4-part synthesis
    (What happened? Why? Business impact? Recommended action?).
    """

    def __init__(
        self,
        what_txt: str,
        why_txt: str,
        impact_txt: str,
        action_txt: str,
        width: float = 540,
        height: float = 160,
    ) -> None:
        super().__init__()
        self.what_txt = what_txt
        self.why_txt = why_txt
        self.impact_txt = impact_txt
        self.action_txt = action_txt
        self.box_w = width
        self.box_h = height

    def wrap(self, availWidth, availHeight):
        return self.box_w, self.box_h

    def draw(self):
        c = self.canv
        c.saveState()

        # Background fill
        c.setFillColor(colors.HexColor("#F0F9FF"))
        c.setStrokeColor(colors.HexColor("#BAE6FD"))
        c.setLineWidth(1)
        c.roundRect(0, 0, self.box_w, self.box_h, 8, fill=1, stroke=1)

        # Header Title
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.HexColor("#0369A1"))
        c.drawString(16, self.box_h - 22, "EXECUTIVE MANAGEMENT BRIEFING (4-PART SYNTHESIS)")

        # Divider line
        c.setStrokeColor(colors.HexColor("#7DD3FC"))
        c.line(16, self.box_h - 28, self.box_w - 16, self.box_h - 28)

        # 4 Points
        pts = [
            ("WHAT HAPPENED?", self.what_txt, "#0284C7"),
            ("WHY DID IT HAPPEN?", self.why_txt, "#0369A1"),
            ("BUSINESS IMPACT?", self.impact_txt, "#0F766E"),
            ("RECOMMENDED ACTION?", self.action_txt, "#15803D"),
        ]

        y = self.box_h - 48
        for title, desc, color in pts:
            c.setFont("Helvetica-Bold", 8)
            c.setFillColor(colors.HexColor(color))
            c.drawString(16, y, f"• {title}:")

            c.setFont("Helvetica", 8.5)
            c.setFillColor(colors.HexColor("#334155"))
            c.drawString(140, y, desc[:75] + ("..." if len(desc) > 75 else ""))
            y -= 26

        c.restoreState()


class ExecutiveGaugeCard(Flowable):
    """
    Visual progress gauge bar for Completeness, Consistency, Validity, and Quality Grade.
    """

    def __init__(
        self,
        label: str,
        score: float,
        width: float = 540,
        height: float = 30,
    ) -> None:
        super().__init__()
        self.label = label
        self.score = min(max(score, 0.0), 100.0)
        self.w = width
        self.h = height

    def wrap(self, availWidth, availHeight):
        return self.w, self.h

    def draw(self):
        c = self.canv
        c.saveState()

        # Background track
        c.setFillColor(colors.HexColor("#F1F5F9"))
        c.roundRect(0, 0, self.w, self.h, 4, fill=1, stroke=0)

        # Filled gauge bar
        fill_w = (self.score / 100.0) * (self.w - 150)
        bar_color = colors.HexColor("#10B981") if self.score >= 85 else colors.HexColor("#F59E0B")
        c.setFillColor(bar_color)
        c.roundRect(140, 5, fill_w, self.h - 10, 3, fill=1, stroke=0)

        # Label & Score Text
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#1E293B"))
        c.drawString(12, 10, self.label)

        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#0F172A"))
        c.drawString(self.w - 45, 10, f"{self.score:.1f}%")

        c.restoreState()
