"""PDFs financeiros com identidade visual e tabelas paginadas."""

from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle
from utilitarios.currency_formatter import CurrencyFormatter
from utilitarios.date_formatter import DateFormatter

NAVY = colors.HexColor("#07304F")
TEAL = colors.HexColor("#16BFC8")
PALE = colors.HexColor("#EAF7F8")
MUTED = colors.HexColor("#60758A")


class FinancialPDF:
    @staticmethod
    def _page(canvas, doc):
        width, height = A4
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, height - 25*mm, width, 25*mm, fill=1, stroke=0)
        canvas.roundRect(16*mm, height-19*mm, 12*mm, 12*mm, 3*mm, fill=0, stroke=0)
        canvas.setStrokeColor(TEAL)
        canvas.setLineWidth(2)
        canvas.line(19*mm, height-16*mm, 21*mm, height-13*mm)
        canvas.line(21*mm, height-13*mm, 23*mm, height-15*mm)
        canvas.line(23*mm, height-15*mm, 26*mm, height-10*mm)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(32*mm, height-13*mm, "FINANCE ASSIST")
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(32*mm, height-17*mm, "Organização financeira")
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(16*mm, 10*mm, datetime.now().strftime("Gerado em %d/%m/%Y às %H:%M"))
        canvas.drawRightString(width-16*mm, 10*mm, f"Página {doc.page}")
        canvas.restoreState()

    @classmethod
    def _doc(cls, path):
        doc = BaseDocTemplate(path, pagesize=A4, leftMargin=16*mm, rightMargin=16*mm,
                              topMargin=34*mm, bottomMargin=18*mm, title="Finance Assist")
        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")
        doc.addPageTemplates(PageTemplate(id="finance", frames=frame, onPage=cls._page))
        return doc

    @staticmethod
    def _styles():
        base = getSampleStyleSheet()
        return {
            "title": ParagraphStyle("FinanceTitle", parent=base["Title"], fontSize=20,
                                    leading=24, textColor=NAVY, alignment=0),
            "small": ParagraphStyle("FinanceSmall", parent=base["Normal"], fontSize=8,
                                    leading=10, textColor=MUTED),
            "cell": ParagraphStyle("FinanceCell", parent=base["Normal"], fontSize=7.5,
                                   leading=9, textColor=colors.HexColor("#182B3A")),
            "total": ParagraphStyle("FinanceTotal", parent=base["Heading2"], fontSize=14,
                                    textColor=NAVY, alignment=TA_RIGHT),
        }

    @staticmethod
    def _table(rows, widths):
        table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), NAVY), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,0), 8),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, PALE]),
            ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#CAD8E2")),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ]))
        return table

    @classmethod
    def extrato(cls, path, conta, transacoes, inicio, fim):
        st = cls._styles()
        nome = conta.get("Nome_Conta") or conta.get("Nome") or "Conta"
        story = [Paragraph(f"Extrato da {nome}", st["title"]),
                 Paragraph(f"Período: {DateFormatter.iso_to_br(inicio)} a {DateFormatter.iso_to_br(fim)}", st["small"]),
                 Spacer(1, 7*mm)]
        rows = [["Data", "Descrição", "Favorecido", "Categoria", "Valor"]]
        total = 0.0
        for item in transacoes:
            valor = float(item.get("Valor") or 0); total += valor
            rows.append([DateFormatter.iso_to_br(item.get("Data", "")),
                         Paragraph(str(item.get("Descricao") or ""), st["cell"]),
                         Paragraph(str(item.get("Favorecido") or "—"), st["cell"]),
                         Paragraph(str(item.get("Categoria") or "Sem categoria"), st["cell"]),
                         CurrencyFormatter.format(valor)])
        story += [cls._table(rows, [22*mm, 58*mm, 36*mm, 34*mm, 28*mm]), Spacer(1, 6*mm),
                  Paragraph(f"Resultado do período: {CurrencyFormatter.format(total)}", st["total"])]
        cls._doc(path).build(story)
        return True

    @classmethod
    def fatura(cls, path, cartao, lancamentos, mes, ano):
        st = cls._styles(); nome = cartao.get("Nome") or "Cartão"
        total = sum(float(i.get("Valor") or 0) for i in lancamentos)
        abertos = sum(float(i.get("Valor") or 0) for i in lancamentos if not i.get("Paga"))
        story = [Paragraph(f"Fatura do {nome}", st["title"]),
                 Paragraph(f"Competência: {int(mes):02d}/{int(ano)}", st["small"]), Spacer(1, 3*mm),
                 Paragraph(f"Total da fatura: {CurrencyFormatter.format(total)}", st["total"]),
                 Paragraph(f"Em aberto: {CurrencyFormatter.format(abertos)}", st["small"]), Spacer(1, 6*mm)]
        rows = [["Data", "Lançamento", "Categoria", "Parcela", "Status", "Valor"]]
        for i in lancamentos:
            rows.append([DateFormatter.iso_to_br(i.get("Data", "")),
                         Paragraph(str(i.get("Descricao") or ""), st["cell"]),
                         Paragraph(str(i.get("Categoria") or "Sem categoria"), st["cell"]),
                         f"{i.get('Parcela_Atual',1)}/{i.get('Num_Parcelas',1)}",
                         "Pago" if i.get("Paga") else "Aberto",
                         CurrencyFormatter.format(float(i.get("Valor") or 0))])
        story.append(cls._table(rows, [20*mm, 54*mm, 31*mm, 18*mm, 22*mm, 27*mm]))
        cls._doc(path).build(story)
        return True
