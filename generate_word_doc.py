"""
将技术文档.md 转换为 Word 文档
"""
import re
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def set_cell_background(cell, color_hex):
    """设置单元格背景色"""
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), color_hex)
    shading.set(qn('w:val'), 'clear')
    cell._tc.get_or_add_tcPr().append(shading)


def add_code_block(doc, code_text):
    """添加代码块"""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(code_text)
    run.font.name = "Consolas"
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    # 设置中文字体
    r = run._element
    r.rPr.rFonts.set(qn('w:eastAsia'), "微软雅黑")
    # 背景色
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), "F5F5F5")
    shading.set(qn('w:val'), 'clear')
    p._p.get_or_add_pPr().append(shading)


def parse_markdown_table(lines):
    """解析Markdown表格行，返回二维数组"""
    rows = []
    for line in lines:
        line = line.strip()
        if line.startswith("|"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            rows.append(cells)
    # 过滤分隔行（含---）
    rows = [r for r in rows if not all(set(c) <= set('-: ') for c in r)]
    return rows


def md_to_docx(md_file: str, docx_file: str):
    """Markdown 转 Word"""
    content = Path(md_file).read_text(encoding="utf-8")
    lines = content.split("\n")

    doc = Document()

    # 设置默认字体
    style = doc.styles['Normal']
    font = style.font
    font.name = "微软雅黑"
    font.size = Pt(11)
    r = style.element.rPr.rFonts
    r.set(qn('w:eastAsia'), "微软雅黑")

    # 设置页边距
    for section in doc.sections:
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)

    i = 0
    in_code_block = False
    code_buffer = []
    table_buffer = []
    in_table = False

    while i < len(lines):
        line = lines[i]

        # 代码块处理
        if line.strip().startswith("```"):
            if in_code_block:
                add_code_block(doc, "\n".join(code_buffer))
                code_buffer = []
                in_code_block = False
            else:
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_buffer.append(line)
            i += 1
            continue

        # 表格处理
        if line.strip().startswith("|"):
            table_buffer.append(line)
            in_table = True
            i += 1
            continue
        elif in_table:
            # 表格结束
            if table_buffer:
                rows = parse_markdown_table(table_buffer)
                if len(rows) >= 2:
                    # 创建表格
                    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
                    table.style = 'Table Grid'
                    table.alignment = WD_TABLE_ALIGNMENT.CENTER

                    for r_idx, row_data in enumerate(rows):
                        for c_idx, cell_text in enumerate(row_data):
                            if c_idx < len(table.rows[r_idx].cells):
                                cell = table.rows[r_idx].cells[c_idx]
                                cell.text = ""
                                p = cell.paragraphs[0]
                                run = p.add_run(cell_text)
                                run.font.size = Pt(10)
                                run.font.name = "微软雅黑"
                                r = run._element
                                r.rPr.rFonts.set(qn('w:eastAsia'), "微软雅黑")

                                # 表头行加粗 + 背景色
                                if r_idx == 0:
                                    run.font.bold = True
                    # 表格后空行
                    doc.add_paragraph()
                table_buffer = []
                in_table = False
            # 不continue，继续处理当前行

        # 标题处理
        if line.startswith("# "):
            text = line[2:].strip()
            h = doc.add_heading(text, level=0)
            h.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in h.runs:
                run.font.color.rgb = RGBColor(0x1a, 0x23, 0x7e)
                run.font.name = "微软雅黑"
                r = run._element
                r.rPr.rFonts.set(qn('w:eastAsia'), "微软雅黑")
        elif line.startswith("## "):
            text = line[3:].strip()
            h = doc.add_heading(text, level=1)
            for run in h.runs:
                run.font.color.rgb = RGBColor(0x1a, 0x23, 0x7e)
                run.font.name = "微软雅黑"
                r = run._element
                r.rPr.rFonts.set(qn('w:eastAsia'), "微软雅黑")
        elif line.startswith("### "):
            text = line[4:].strip()
            h = doc.add_heading(text, level=2)
            for run in h.runs:
                run.font.color.rgb = RGBColor(0x28, 0x35, 0x9a)
                run.font.name = "微软雅黑"
                r = run._element
                r.rPr.rFonts.set(qn('w:eastAsia'), "微软雅黑")
        elif line.startswith("#### "):
            text = line[5:].strip()
            h = doc.add_heading(text, level=3)
            for run in h.runs:
                run.font.color.rgb = RGBColor(0x40, 0x40, 0x40)
                run.font.name = "微软雅黑"
                r = run._element
                r.rPr.rFonts.set(qn('w:eastAsia'), "微软雅黑")
        # 分隔线
        elif line.strip() == "---":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run("─" * 50)
            run.font.color.rgb = RGBColor(0xBB, 0xBB, 0xBB)
        # 引用
        elif line.startswith("> "):
            text = line[2:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(1)
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(4)
            run = p.add_run(text)
            run.font.italic = True
            run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
            run.font.name = "微软雅黑"
            r = run._element
            r.rPr.rFonts.set(qn('w:eastAsia'), "微软雅黑")
            # 背景色
            shading = OxmlElement('w:shd')
            shading.set(qn('w:fill'), "F0F4FF")
            shading.set(qn('w:val'), 'clear')
            p._p.get_or_add_pPr().append(shading)
        # 列表项
        elif re.match(r"^\s*[-*]\s", line):
            text = re.sub(r"^\s*[-*]\s", "", line).strip()
            p = doc.add_paragraph(style="List Bullet")
            # 处理粗体
            parts = re.split(r"(\*\*[^*]+\*\*)", text)
            for part in parts:
                if part.startswith("**") and part.endswith("**"):
                    run = p.add_run(part[2:-2])
                    run.font.bold = True
                else:
                    run = p.add_run(part)
                run.font.size = Pt(11)
                run.font.name = "微软雅黑"
                r = run._element
                r.rPr.rFonts.set(qn('w:eastAsia'), "微软雅黑")
        # 有序列表
        elif re.match(r"^\s*\d+\.\s", line):
            text = re.sub(r"^\s*\d+\.\s", "", line).strip()
            p = doc.add_paragraph(style="List Number")
            parts = re.split(r"(\*\*[^*]+\*\*)", text)
            for part in parts:
                if part.startswith("**") and part.endswith("**"):
                    run = p.add_run(part[2:-2])
                    run.font.bold = True
                else:
                    run = p.add_run(part)
                run.font.size = Pt(11)
                run.font.name = "微软雅黑"
                r = run._element
                r.rPr.rFonts.set(qn('w:eastAsia'), "微软雅黑")
        # 空行
        elif line.strip() == "":
            doc.add_paragraph()
        # 普通段落
        else:
            text = line.strip()
            if text:
                p = doc.add_paragraph()
                p.paragraph_format.line_spacing = 1.5
                p.paragraph_format.space_after = Pt(4)
                # 处理粗体和代码
                parts = re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text)
                for part in parts:
                    if part.startswith("**") and part.endswith("**"):
                        run = p.add_run(part[2:-2])
                        run.font.bold = True
                    elif part.startswith("`") and part.endswith("`"):
                        run = p.add_run(part[1:-1])
                        run.font.name = "Consolas"
                        run.font.size = Pt(10)
                        run.font.color.rgb = RGBColor(0xC0, 0x39, 0x2B)
                    else:
                        run = p.add_run(part)
                    run.font.size = Pt(11)
                    if not (part.startswith("`") and part.endswith("`")):
                        run.font.name = "微软雅黑"
                        r = run._element
                        r.rPr.rFonts.set(qn('w:eastAsia'), "微软雅黑")

        i += 1

    # 处理最后可能剩余的表格
    if table_buffer:
        rows = parse_markdown_table(table_buffer)
        if len(rows) >= 2:
            table = doc.add_table(rows=len(rows), cols=len(rows[0]))
            table.style = 'Table Grid'
            for r_idx, row_data in enumerate(rows):
                for c_idx, cell_text in enumerate(row_data):
                    if c_idx < len(table.rows[r_idx].cells):
                        cell = table.rows[r_idx].cells[c_idx]
                        cell.text = cell_text
                        if r_idx == 0:
                            for p in cell.paragraphs:
                                for run in p.runs:
                                    run.font.bold = True

    doc.save(docx_file)
    print(f"[OK] Word文档已生成: {docx_file}")


if __name__ == "__main__":
    md_to_docx("技术文档.md", "智慧银行理财顾问智能体_技术文档.docx")
