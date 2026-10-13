"""Gera PDF, Markdown e diagramas a partir do texto-base e do esquema SQLite.

Execute na raiz: python scripts/build_docs.py. Requer apenas ReportLab além
 das dependências do app. O banco da clínica não é aberto ou modificado.
"""

import re
import sqlite3
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.graphics.shapes import Drawing, Rect, Line, String
from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    Preformatted,
    KeepTogether,
    Image,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
NAVY = colors.HexColor("#12243f")
TEAL = colors.HexColor("#087f8c")
MUTED = colors.HexColor("#53657c")
LINE = colors.HexColor("#dfe7ef")
TABLES = [
    "tutors",
    "pets",
    "veterinarians",
    "services",
    "appointments",
    "medical_records",
    "payments",
]
LABELS = dict(
    tutors="Tutores",
    pets="Animais",
    veterinarians="Veterinários",
    services="Serviços",
    appointments="Consultas",
    medical_records="Prontuários",
    payments="Pagamentos",
)
DESCRIPTIONS = {
    "id": "Identificador único gerado pelo SQLite.",
    "name": "Nome de exibição do cadastro.",
    "phone": "Telefone para contato, armazenado como texto.",
    "email": "E-mail opcional.",
    "address": "Endereço de exibição do tutor.",
    "active": "1: ativo, 0: arquivado.",
    "created_at": "Instante de criação em UTC, com sufixo Z.",
    "tutor_id": "Tutor responsável pelo animal.",
    "species": "Cão, Gato, Ave ou Outro.",
    "breed": "Raça informada, sem catálogo auxiliar.",
    "sex": "Macho, Fêmea ou Não informado.",
    "birth_date": "Nascimento opcional em YYYY-MM-DD.",
    "weight_kg": "Peso em kg, positivo quando informado.",
    "notes": "Observações opcionais do cadastro ou agendamento.",
    "crmv": "Registro profissional com UF, único.",
    "specialty": "Área de atuação informada.",
    "price_cents": "Preço atual do serviço em centavos, não negativo.",
    "duration_minutes": "Duração em minutos, de 10 a 240.",
    "pet_id": "Animal da consulta.",
    "veterinarian_id": "Profissional da consulta.",
    "service_id": "Serviço da consulta.",
    "starts_at": "Início em YYYY-MM-DDTHH:MM, horário de São Paulo.",
    "fee_cents": "Preço acordado em centavos, preservado após alterar o catálogo.",
    "status": "Agendado, Confirmado, Concluído ou Cancelado.",
    "appointment_id": "Consulta vinculada ao registro.",
    "complaint": "Queixa ou motivo do atendimento.",
    "diagnosis": "Avaliação clínica ou diagnóstico registrado.",
    "treatment": "Conduta e orientações registradas.",
    "amount_cents": "Valor recebido em centavos, deve ser positivo.",
    "method": "Pix, Dinheiro ou Cartão.",
    "paid_at": "Dia do pagamento em YYYY-MM-DD.",
}


def schema_connection():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript((ROOT / "database/01_schema.sql").read_text(encoding="utf-8"))
    return db


def dictionary(db):
    sections = []
    for index, table in enumerate(TABLES, 1):
        fields = db.execute(f"PRAGMA table_info({table})").fetchall()
        fks = {
            r["from"]: f"{r['table']}.{r['to']}"
            for r in db.execute(f"PRAGMA foreign_key_list({table})")
        }
        unique = set()
        for r in db.execute(f"PRAGMA index_list({table})").fetchall():
            if r["unique"]:
                cols = db.execute(f"PRAGMA index_info('{r['name']}')").fetchall()
                if len(cols) == 1:
                    unique.add(cols[0]["name"])
        lines = [
            f"### 9.{index}. {LABELS[table]} ({table})",
            "",
            "| Campo | Tipo | Obrigatório | Chave / padrão | Descrição |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        for row in fields:
            key = []
            if row["pk"]:
                key.append("PK")
            if row["name"] in fks:
                key.append("FK: " + fks[row["name"]])
            if row["name"] in unique:
                key.append("UNIQUE")
            if row["dflt_value"] is not None:
                default = row["dflt_value"]
                if "strftime" in default:
                    default = "UTC automático"
                key.append("Padrão: " + default)
            description = DESCRIPTIONS[row["name"]]
            if table == "medical_records" and row["name"] == "weight_kg":
                description = "Peso aferido neste atendimento, registro histórico."
            if table == "pets" and row["name"] == "weight_kg":
                description = "Peso atual do cadastro, atualizado pelo último registro da interface."
            lines.append(
                f"| {row['name']} | {row['type']} | {'Sim' if row['notnull'] or row['pk'] else 'Não'} | {', '.join(key) or 'Sem padrão'} | {description} |"
            )
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def diagram(db, conceptual=False):
    """Mesma geometria para SVG editável e desenho vetorial no relatório."""
    width, height = 960, 1080
    drawing = Drawing(width, height)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="960" height="1080" fill="white"/>',
    ]

    def rect(x, y, w, h, fill, border="#dfe7ef"):
        drawing.add(
            Rect(
                x,
                height - y - h,
                w,
                h,
                fillColor=colors.HexColor(fill),
                strokeColor=colors.HexColor(border),
                strokeWidth=1.4,
                rx=8,
                ry=8,
            )
        )
        svg.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{border}" stroke-width="1.4"/>'
        )

    def label(x, y, value, size=16, fill="#12243f", bold=False):
        font = "Helvetica-Bold" if bold else "Helvetica"
        drawing.add(
            String(
                x,
                height - y,
                value,
                fontName=font,
                fontSize=size,
                fillColor=colors.HexColor(fill),
            )
        )
        svg.append(
            f'<text x="{x}" y="{y}" fill="{fill}" font-family="Arial, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}">{escape(value)}</text>'
        )

    def line(points):
        for (x, y), (xx, yy) in zip(points, points[1:]):
            drawing.add(
                Line(x, height - y, xx, height - yy, strokeColor=TEAL, strokeWidth=2)
            )
        svg.append(
            '<polyline points="'
            + " ".join(f"{x},{y}" for x, y in points)
            + '" fill="none" stroke="#087f8c" stroke-width="2"/>'
        )

    label(
        30,
        32,
        "Modelo conceitual" if conceptual else "Modelo lógico relacional",
        26,
        bold=True,
    )
    label(
        30,
        58,
        (
            "VetCare | PK: chave primária | FK: chave estrangeira"
            if not conceptual
            else "Entidades e relações do atendimento"
        ),
        16,
        "#53657c",
    )
    pos = {
        "tutors": (30, 90),
        "veterinarians": (350, 90),
        "services": (670, 90),
        "pets": (30, 380),
        "appointments": (350, 380),
        "medical_records": (180, 820),
        "payments": (520, 820),
    }
    heights = {
        t: (
            110
            if conceptual
            else 56 + 24 * len(db.execute(f"PRAGMA table_info({t})").fetchall())
        )
        for t in TABLES
    }
    # Conexões são desenhadas antes das caixas, preservando os campos legíveis.
    line([(170, 90 + heights["tutors"]), (170, 380)])
    label(180, 90 + heights["tutors"] + 23, "1", 15)
    label(180, 367, "0..N", 15)
    line([(310, 480), (350, 480)])
    label(319, 469, "1", 13)
    label(314, 507, "0..N", 13)
    line([(490, 90 + heights["veterinarians"]), (490, 380)])
    label(502, 90 + heights["veterinarians"] + 23, "1", 15)
    label(502, 365, "0..N", 15)
    line(
        [
            (810, 90 + heights["services"]),
            (810, 325),
            (650, 325),
            (650, 440),
            (630, 440),
        ]
    )
    label(822, 90 + heights["services"] + 23, "1", 15)
    label(651, 429, "0..N", 15)
    end = 380 + heights["appointments"]
    line([(430, end), (430, 770), (320, 770), (320, 820)])
    label(437, end + 24, "1", 15)
    label(330, 807, "0..1", 15)
    line([(550, end), (550, 750), (660, 750), (660, 820)])
    label(558, end + 24, "1", 15)
    label(670, 807, "0..N", 15)
    concepts = {
        "tutors": "Responsável pelo animal",
        "pets": "Paciente da clínica",
        "veterinarians": "Profissional do atendimento",
        "services": "Catálogo de procedimentos",
        "appointments": "Compromisso da agenda",
        "medical_records": "Registro do atendimento",
        "payments": "Recebimento vinculado",
    }
    for t in TABLES:
        x, y = pos[t]
        h = heights[t]
        rect(x, y, 280, h, "#ffffff")
        rect(x, y, 280, 44, "#e6f5f7")
        label(x + 14, y + 29, LABELS[t] if conceptual else t, 21, bold=True)
        if conceptual:
            label(x + 14, y + 80, concepts[t], 15, "#53657c")
        else:
            fks = {r["from"] for r in db.execute(f"PRAGMA foreign_key_list({t})")}
            for i, r in enumerate(db.execute(f"PRAGMA table_info({t})")):
                tag = "PK " if r["pk"] else "FK " if r["name"] in fks else "   "
                label(
                    x + 14,
                    y + 68 + i * 24,
                    tag + r["name"],
                    16,
                    "#087f8c" if tag.strip() else "#12243f",
                )
    # Caixa dos prontuários/pagamentos excederia altura com campos? Ajustar canvas abaixo.
    svg.append("</svg>")
    output = DOCS / ("modelo-conceitual.svg" if conceptual else "modelagem.svg")
    output.write_text("\n".join(svg), encoding="utf-8")
    scale = 0.32 if conceptual else 0.43
    drawing.scale(scale, scale)
    drawing.width = width * scale
    drawing.height = height * scale
    return drawing


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="BodyVet",
        allowWidows=0,
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=NAVY,
        spaceAfter=9,
    )
)
styles.add(
    ParagraphStyle(
        name="H1Vet",
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=22,
        textColor=TEAL,
        spaceBefore=17,
        spaceAfter=11,
        keepWithNext=True,
    )
)
styles.add(
    ParagraphStyle(
        name="H2Vet",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=17,
        textColor=NAVY,
        spaceBefore=12,
        spaceAfter=7,
        keepWithNext=True,
    )
)
styles.add(
    ParagraphStyle(
        name="CellVet", fontName="Helvetica", fontSize=8, leading=11, textColor=NAVY
    )
)
styles.add(
    ParagraphStyle(
        name="CellHeadVet",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=TEAL,
    )
)
styles.add(
    ParagraphStyle(
        name="CodeVet",
        fontName="Courier",
        fontSize=6.5,
        leading=9,
        textColor=NAVY,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="ListVet",
        parent=styles["BodyVet"],
        leftIndent=12,
        firstLineIndent=-9,
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="TitleVet",
        fontName="Helvetica-Bold",
        fontSize=42,
        leading=48,
        textColor=NAVY,
    )
)
styles.add(
    ParagraphStyle(
        name="SubVet", fontName="Helvetica", fontSize=20, leading=28, textColor=MUTED
    )
)


class Report(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(
            str(path),
            pagesize=A4,
            leftMargin=54,
            rightMargin=54,
            topMargin=62,
            bottomMargin=52,
            title="VetCare | Documentação técnica",
            author="Projeto VetCare",
        )
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="normal",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates(
            PageTemplate(id="normal", frames=[frame], onPage=self.footer)
        )
        self.heading_id = 0

    def beforeDocument(self):
        self.heading_id = 0

    def footer(self, canvas, doc):
        canvas.saveState()
        if doc.page > 1:
            canvas.setStrokeColor(LINE)
            canvas.line(54, A4[1] - 40, A4[0] - 54, A4[1] - 40)
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(MUTED)
            canvas.drawString(54, A4[1] - 30, "VetCare | Projeto de Banco de Dados")
            canvas.drawString(54, 30, "Documentação técnica | versão 1.0")
            canvas.drawRightString(A4[0] - 54, 30, str(doc.page))
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "H1Vet":
            title = flowable.getPlainText()
            if title == "Sumário":
                return
            key = "heading-" + str(self.heading_id)
            self.heading_id += 1
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, 0, False)
            self.notify("TOCEntry", (0, title, self.page, key))


def inline(value):
    value = escape(value)
    value = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', value)
    return value


def markdown_flow(text, drawings):
    lines = text.splitlines()
    result = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("# "):
            i += 1
            continue
        if line.startswith("## "):
            section = line[3:]
            if re.match(r"^(4|5|6|7|9|16)\.", section):
                result.append(PageBreak())
            result.append(Paragraph(inline(section), styles["H1Vet"]))
            i += 1
            continue
        if line.startswith("### "):
            result.append(Paragraph(inline(line[4:]), styles["H2Vet"]))
            i += 1
            continue
        if line.startswith("!["):
            key = "conceptual" if "conceitual" in line else "logical"
            result.append(drawings[key])
            result.append(Spacer(1, 12))
            i += 1
            continue
        if line.startswith("|"):
            grid = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    grid.append(cells)
                i += 1
            n = len(grid[0])
            width = 487
            if n == 5:
                weights = [0.19, 0.12, 0.13, 0.24, 0.32]
            elif n == 4:
                weights = [0.09, 0.28, 0.32, 0.31]
            elif n == 3:
                weights = (
                    [0.10, 0.50, 0.40] if grid[0][0] == "Código" else [0.25, 0.39, 0.36]
                )
            else:
                weights = [1 / n] * n
            wrapped = [
                [
                    Paragraph(
                        inline(c),
                        styles["CellHeadVet"] if r == 0 else styles["CellVet"],
                    )
                    for c in cells
                ]
                for r, cells in enumerate(grid)
            ]
            table = Table(
                wrapped,
                colWidths=[width * w for w in weights],
                repeatRows=1,
                hAlign="LEFT",
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6f5f7")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.6, LINE),
                        ("LINEBELOW", (0, 1), (-1, -1), 0.3, LINE),
                        ("LEFTPADDING", (0, 0), (-1, -1), 7),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                )
            )
            result.extend([table, Spacer(1, 11)])
            continue
        if line.startswith("- "):
            result.append(Paragraph("- " + inline(line[2:]), styles["ListVet"]))
            i += 1
            continue
        para = [line]
        i += 1
        while (
            i < len(lines)
            and lines[i].strip()
            and not lines[i].startswith(("#", "|", "- ", "!["))
        ):
            para.append(lines[i].strip())
            i += 1
        result.append(Paragraph(inline(" ".join(para)), styles["BodyVet"]))
    return result


def build():
    DOCS.mkdir(exist_ok=True)
    db = schema_connection()
    source = (
        (DOCS / "documentacao-base.md")
        .read_text(encoding="utf-8")
        .replace("{{DICTIONARY}}", dictionary(db))
    )
    (DOCS / "documentacao.md").write_text(source, encoding="utf-8")
    drawings = {"conceptual": diagram(db, True), "logical": diagram(db)}
    report = Report(DOCS / "relatorio-tecnico.pdf")
    story = [
        Spacer(1, 72),
        Paragraph("VetCare", styles["TitleVet"]),
        Spacer(1, 18),
        Paragraph("Sistema de clínica veterinária", styles["SubVet"]),
        Spacer(1, 36),
        Paragraph(
            "Documentação técnica para projeto de Banco de Dados", styles["BodyVet"]
        ),
        Spacer(1, 20),
        Paragraph(
            "SQLite · Python · Flask<br/>Modelagem, implementação e scripts comentados",
            styles["SubVet"],
        ),
        Spacer(1, 125),
        Paragraph("Versão 1.0<br/>Outubro de 2026", styles["BodyVet"]),
        PageBreak(),
        Paragraph("Sumário", styles["H1Vet"]),
    ]
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            name="TOCVet",
            fontName="Helvetica",
            fontSize=9,
            leading=14,
            textColor=NAVY,
            spaceBefore=2,
        )
    ]
    story.extend([toc, PageBreak()])
    story.extend(markdown_flow(source, drawings))
    screenshot = DOCS / "interface-desktop.png"
    if screenshot.exists():
        from PIL import Image as PILImage

        w, h = PILImage.open(screenshot).size
        story.extend(
            [
                PageBreak(),
                Paragraph("17. Interface da aplicação", styles["H1Vet"]),
                Paragraph(
                    "Visão geral com os dados fictícios do projeto.", styles["BodyVet"]
                ),
                Image(str(screenshot), width=487, height=487 * h / w),
            ]
        )
    for number, filename in enumerate(
        ["01_schema.sql", "02_seed.sql", "03_queries.sql", "04_transactions.sql"], 1
    ):
        story.extend(
            [
                PageBreak(),
                Paragraph(f"Apêndice {number}. {filename}", styles["H1Vet"]),
                Paragraph(
                    "O arquivo no diretório database é a versão executável. Linhas longas têm quebra visual neste apêndice.",
                    styles["BodyVet"],
                ),
            ]
        )
        code = (ROOT / "database" / filename).read_text(encoding="utf-8")
        story.append(
            Preformatted(
                code,
                styles["CodeVet"],
                maxLineLength=119,
                splitChars=" ,)",
                newLineChars="    ",
            )
        )
    report.multiBuild(story)
    print(f'Relatório: {DOCS / "relatorio-tecnico.pdf"}')
    print(
        "Tabelas:",
        len(TABLES),
        "Triggers:",
        db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger'"
        ).fetchone()[0],
    )
    db.close()


if __name__ == "__main__":
    build()
