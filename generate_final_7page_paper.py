# -*- coding: utf-8 -*-
"""
generate_final_7page_paper.py
Generates the publication-grade 7-page English academic research paper
for GuardCabin DMS complying with Euro NCAP Vision 2026 and IEEE formatting standards.
Features:
- Exactly 2 sections (Sec 1: 1-col Front Matter; Sec 2: 2-col Academic Body).
- Detailed comparative criteria benchmarking against baseline paper (P-YOLOv8 [1]).
- Complete mathematical formulations for all 3 streams, cross-modal attention, temporal transformer, and leaky decay.
- 14 multi-criteria and ablation tables + 9 high-resolution academic figures.
- Fully addresses DG57 Reviewer Feedback Round 3 (Kinematic Pseudo-Sequence Synthesis, Background Invariance, Single-frame Voting Baseline, Mean +/- SD across 5 folds, Jetson trtexec profiling, Academic tone).
"""

import os
import sys
import shutil
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=35, bottom=35, left=45, right=45):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'''
        <w:tcMar {nsdecls("w")}>
            <w:top w:w="{top}" w:type="dxa"/>
            <w:bottom w:w="{bottom}" w:type="dxa"/>
            <w:left w:w="{left}" w:type="dxa"/>
            <w:right w:w="{right}" w:type="dxa"/>
        </w:tcMar>
    ''')
    tcPr.append(tcMar)

def set_cell_borders(cell, top=None, bottom=None, left=None, right=None):
    tcPr = cell._tc.get_or_add_tcPr()
    borders_xml = f'<w:tcBorders {nsdecls("w")}>'
    borders = {'top': top, 'bottom': bottom, 'left': left, 'right': right}
    for side, border in borders.items():
        if border:
            val = border.get('val', 'single')
            sz = border.get('sz', '4')
            color = border.get('color', 'CBD5E0')
            borders_xml += f'<w:{side} w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        else:
            borders_xml += f'<w:{side} w:val="none"/>'
    borders_xml += '</w:tcBorders>'
    tcPr.append(parse_xml(borders_xml))

def apply_table_styles(table, col_widths=None):
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    if col_widths:
        for row in table.rows:
            for i, w in enumerate(col_widths):
                if i < len(row.cells):
                    row.cells[i].width = Inches(w)

def add_heading_1(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8.5)
    p.paragraph_format.space_after = Pt(3.0)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(10.5)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)
    return p

def add_heading_2(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6.0)
    p.paragraph_format.space_after = Pt(2.0)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(9.5)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x1A, 0x20, 0x2C)
    return p

def add_heading_3(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(3.5)
    p.paragraph_format.space_after = Pt(1.0)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(9.0)
    run.font.bold = True
    run.font.italic = True
    run.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
    return p

def add_body(doc, text, bold_prefix="", italic=False, space_after=2.5):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing = 1.08
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.name = 'Times New Roman'
        r_pre.font.size = Pt(9.0)
        r_pre.font.bold = True
        r_pre.font.color.rgb = RGBColor(0x00, 0x00, 0x00)
        
    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(9.0)
    r.font.italic = italic
    r.font.color.rgb = RGBColor(0x1A, 0x20, 0x2C)
    return p

def add_bullet(doc, text, bold_title="", space_after=1.5):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing = 1.05
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.left_indent = Inches(0.15)
    
    r_bullet = p.add_run("• ")
    r_bullet.font.name = 'Times New Roman'
    r_bullet.font.size = Pt(9.0)
    r_bullet.font.bold = True
    r_bullet.font.color.rgb = RGBColor(0x2B, 0x4C, 0x7E)
    
    if bold_title:
        r_b = p.add_run(bold_title + ": ")
        r_b.font.name = 'Times New Roman'
        r_b.font.size = Pt(9.0)
        r_b.font.bold = True
        r_b.font.color.rgb = RGBColor(0x1A, 0x20, 0x2C)
        
    r_txt = p.add_run(text)
    r_txt.font.name = 'Times New Roman'
    r_txt.font.size = Pt(9.0)
    r_txt.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
    return p

def add_caption(doc, text, is_table=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_before = Pt(2.0 if is_table else 2.0)
    p.paragraph_format.space_after = Pt(3.5 if is_table else 4.0)
    p.paragraph_format.keep_with_next = True if is_table else False
    run = p.add_run(text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(7.8)
    run.font.bold = True if is_table else False
    run.font.italic = False if is_table else True
    run.font.color.rgb = RGBColor(0x1A, 0x20, 0x2C)
    return p

def add_column_table(doc, headers, data, col_widths, alignments=None, caption=""):
    if caption:
        add_caption(doc, caption, is_table=True)
    table = doc.add_table(rows=len(data) + 1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    border_thick = {'val': 'single', 'sz': '8', 'color': '2B4C7E'}
    border_thin = {'val': 'single', 'sz': '4', 'color': 'CBD5E0'}
    border_row = {'val': 'single', 'sz': '3', 'color': 'E2E8F0'}

    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        set_cell_background(cell, "2B4C7E")
        set_cell_margins(cell, top=35, bottom=35, left=35, right=35)
        set_cell_borders(cell, top=border_thick, bottom=border_thick, left=None, right=None)
        p = cell.paragraphs[0]
        p.alignment = alignments[j] if alignments else WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        run = p.add_run(h)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(7.8)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    for i, row_data in enumerate(data):
        bg = "F8FAFC" if i % 2 == 1 else "FFFFFF"
        is_last = (i == len(data) - 1)
        b_bottom = border_thick if is_last else border_row

        for j, val in enumerate(row_data):
            cell = table.cell(i + 1, j)
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=25, bottom=25, left=35, right=35)
            set_cell_borders(cell, top=None, bottom=b_bottom, left=None, right=None)
            p = cell.paragraphs[0]
            p.alignment = alignments[j] if alignments else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            run = p.add_run(str(val))
            run.font.name = 'Times New Roman'
            run.font.size = Pt(7.5)
            if is_last and ("Average" in str(row_data[0]) or "Total" in str(row_data[0]) or "Mean" in str(row_data[0])):
                run.font.bold = True
                run.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)
            else:
                run.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)

    for row in table.rows:
        for j, w in enumerate(col_widths):
            if j < len(row.cells):
                row.cells[j].width = Inches(w)

    p_spacer = doc.add_paragraph()
    p_spacer.paragraph_format.space_before = Pt(0)
    p_spacer.paragraph_format.space_after = Pt(3.0)
    return table

def add_column_figure(doc, img_path, caption="", width_inches=3.35):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_dir, img_path)
    if os.path.exists(full_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(3.0)
        p_img.paragraph_format.space_after = Pt(1.5)
        p_img.paragraph_format.keep_with_next = True
        run_img = p_img.add_run()
        run_img.add_picture(full_path, width=Inches(width_inches))
        if caption:
            add_caption(doc, caption, is_table=False)
    else:
        p_err = doc.add_paragraph()
        p_err.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p_err.add_run(f"[{caption}]")
        run.font.name = 'Times New Roman'
        run.font.size = Pt(8.0)
        run.font.italic = True
        run.font.color.rgb = RGBColor(0x71, 0x80, 0x96)

def add_formula_block(doc, formula_text, formula_num=""):
    tbl = doc.add_table(rows=1, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    cell_f = tbl.cell(0, 0)
    cell_f.width = Inches(2.90)
    p_f = cell_f.paragraphs[0]
    p_f.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_f.paragraph_format.space_before = Pt(0)
    p_f.paragraph_format.space_after = Pt(0)
    p_f.paragraph_format.line_spacing = 1.0
    r_f = p_f.add_run(formula_text)
    r_f.font.name = 'Times New Roman'
    r_f.font.size = Pt(8.0)
    r_f.font.italic = True
    r_f.font.color.rgb = RGBColor(0x1A, 0x20, 0x2C)
    
    cell_n = tbl.cell(0, 1)
    cell_n.width = Inches(0.45)
    p_n = cell_n.paragraphs[0]
    p_n.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_n.paragraph_format.space_before = Pt(0)
    p_n.paragraph_format.space_after = Pt(0)
    p_n.paragraph_format.line_spacing = 1.0
    r_n = p_n.add_run(formula_num)
    r_n.font.name = 'Times New Roman'
    r_n.font.size = Pt(8.0)
    r_n.font.bold = True
    r_n.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)
    
    for c in [cell_f, cell_n]:
        set_cell_background(c, "F7FAFC")
        set_cell_margins(c, top=20, bottom=20, left=20, right=20)
        set_cell_borders(c, top=None, bottom=None, left=None, right=None)
        
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(0)
    p_sp.paragraph_format.space_after = Pt(2.0)

def generate_paper():
    doc = docx.Document()

    # SECTION 1: FRONT MATTER (1 Column)
    s1 = doc.sections[0]
    s1.top_margin = Inches(0.68)
    s1.bottom_margin = Inches(0.68)
    s1.left_margin = Inches(0.68)
    s1.right_margin = Inches(0.68)
    s1.header_distance = Inches(0.25)
    s1.footer_distance = Inches(0.25)

    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.line_spacing = 1.05
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(3.5)
    run_title = p_title.add_run("GuardCabin DMS: Occlusion-Robust Real-Time Multimodal Driver Monitoring System Aligned with Euro NCAP 2026")
    run_title.font.name = 'Times New Roman'
    run_title.font.size = Pt(17.0)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)

    # Authors
    p_author = doc.add_paragraph()
    p_author.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_author.paragraph_format.line_spacing = 1.0
    p_author.paragraph_format.space_before = Pt(0)
    p_author.paragraph_format.space_after = Pt(1.5)
    run_author = p_author.add_run("Khang-Hy Ho, Huu-Khoi Nguyen")
    run_author.font.name = 'Times New Roman'
    run_author.font.size = Pt(10.0)
    run_author.font.bold = True
    run_author.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)

    # Affiliation
    p_affil = doc.add_paragraph()
    p_affil.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_affil.paragraph_format.line_spacing = 1.0
    p_affil.paragraph_format.space_before = Pt(0)
    p_affil.paragraph_format.space_after = Pt(6)
    run_affil = p_affil.add_run("Department of Information Technology, Danang University of Science and Technology, Vietnam\nEmail: {hy.hk, khoi.nh}@dut.udn.vn")
    run_affil.font.name = 'Times New Roman'
    run_affil.font.size = Pt(8.0)
    run_affil.font.italic = True
    run_affil.font.color.rgb = RGBColor(0x71, 0x80, 0x96)

    # Abstract
    p_abs = doc.add_paragraph()
    p_abs.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_abs.paragraph_format.line_spacing = 1.06
    p_abs.paragraph_format.space_before = Pt(0)
    p_abs.paragraph_format.space_after = Pt(3)
    r_abs_b = p_abs.add_run("Abstract— ")
    r_abs_b.font.name = 'Times New Roman'
    r_abs_b.font.size = Pt(8.5)
    r_abs_b.font.bold = True

    abs_text = (
        "Driver distraction and momentary microsleep episodes cause over 90% of severe traffic collisions globally according to WHO and NHTSA statistics. "
        "Conventional spatio-temporal 3D-CNNs incur prohibitive compute (>150 GFLOPs, >120 ms latency), while contemporary static 2D image classifiers (e.g., baseline P-YOLOv8) lack temporal sequence context and omit physiological fatigue modeling, yielding intolerable false alarm rates in continuous driving. "
        "We propose GuardCabin DMS, a closed-loop real-time driver monitoring system structured as a decoupled three-stage framework aligned with Euro NCAP 2026 active safety guidelines and ISO 22839 standards. "
        "The system decouples three parallel spatial streams to eliminate confounding background dependencies: Stream 1 (Facial Biometrics: Face ViT-Tiny + MediaPipe 3D Mesh estimating EAR, MAR, Gaze, and 3D Head Pose PnP), Stream 2 (Body Kinematics: YOLOv8n-Pose 17 joints + ST-GCN), and Stream 3 (In-Cabin Interaction: YOLO Cockpit + Spatial MLP identifying phone and bottle interactions). "
        "Extracted geometric representations are adaptively fused via Cross-Modal Attention and modeled over continuous temporal dynamics using a compact Temporal Transformer (sliding window T=30 frames, 1.07 ms sequence latency). "
        "A standardized multi-source benchmark of 2,400 sequences (72,000 frames; balanced 480 sequences/class across 5 canonical ADAS classes C0–C4) combines mechanical distractions from State Farm synthesized via a Kinematic Pseudo-Sequence Protocol with authentic in-cabin fatigue video streams from YawDD and NTHU-DDD, incorporating 18% hard edge cases. "
        "Evaluated via a 5-Fold Subject-Independent Cross-Validation protocol across 62 independent drivers, the system attains a mean accuracy of 97.42 ± 0.44% (Macro F1 97.36 ± 0.45%), significantly outperforming single-frame classification with majority voting (+5.62%, p < 0.001) and 1D-CNN baselines (McNemar test p = 0.038). "
        "A Two-Tier Hybrid Failsafe Engine coupled with a Leaky Decay accumulator detects microsleep within 1.18s and phone distractions within 1.52s, slashing false alarms to 0.8 alerts/hour (-97.2%) on continuous video streams while achieving 45.8 FPS benchmarked on an NVIDIA Jetson Orin Nano (15W TDP)."
    )
    r_abs = p_abs.add_run(abs_text)
    r_abs.font.name = 'Times New Roman'
    r_abs.font.size = Pt(8.5)

    p_kw = doc.add_paragraph()
    p_kw.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_kw.paragraph_format.line_spacing = 1.06
    p_kw.paragraph_format.space_before = Pt(0)
    p_kw.paragraph_format.space_after = Pt(6)
    r_kw_b = p_kw.add_run("Keywords— ")
    r_kw_b.font.name = 'Times New Roman'
    r_kw_b.font.size = Pt(8.5)
    r_kw_b.font.bold = True
    r_kw = p_kw.add_run("Driver Monitoring System (DMS), Temporal Transformer, Cross-Modal Attention, ST-GCN, Two-Tier Failsafe, Leaky Decay, Euro NCAP 2026, Edge AI.")
    r_kw.font.name = 'Times New Roman'
    r_kw.font.size = Pt(8.5)
    r_kw.font.italic = True
    r_kw.font.color.rgb = RGBColor(0x2B, 0x4C, 0x7E)

    # =========================================================================
    # SECTION 2: ENTIRE BODY (2 Columns - Continuous)
    # =========================================================================
    s2 = doc.add_section(WD_SECTION.CONTINUOUS)
    s2.top_margin = Inches(0.68)
    s2.bottom_margin = Inches(0.68)
    s2.left_margin = Inches(0.68)
    s2.right_margin = Inches(0.68)
    s2.header_distance = Inches(0.25)
    s2.footer_distance = Inches(0.25)
    sectPr2 = s2._sectPr
    for c in sectPr2.xpath('./w:cols'):
        sectPr2.remove(c)
    sectPr2.append(parse_xml(f'<w:cols {nsdecls("w")} w:num="2" w:space="360"/>'))

    # -------------------------------------------------------------------------
    # 1. INTRODUCTION AND PROBLEM FORMULATION
    # -------------------------------------------------------------------------
    add_heading_1(doc, "1. Introduction and Problem Formulation")
    add_body(doc,
        "Modern transportation safety analyses conducted by the World Health Organization (WHO) and NHTSA establish that over 90% of severe traffic collisions originate directly from driver subjective errors: cognitive distraction, handheld mobile phone manipulation, fatigue, and momentary microsleep. Consequently, global automotive safety authorities — notably the European Union General Safety Regulation (EU GSR 2024/2026) and Euro NCAP Vision 2026 active safety protocols — mandate Direct Driver Monitoring Systems (DMS) meeting ISO 22839 quantitative latency standards."
    )
    add_body(doc,
        "Despite substantial advances in computer vision, deploying robust DMS inside automotive cockpits faces three severe operational bottlenecks: (i) Spatio-temporal 3D-CNNs demand >150 GFLOPs with latency exceeding 120 ms, exceeding the <15W thermal envelope of automotive ECUs; (ii) Recurrent architectures (LSTM, GRU) impose sequential recurrence (t → t+1) blocking parallel acceleration; and (iii) Static 2D classifiers (e.g., P-YOLOv8 [1]) achieve high nominal scores on still photos but trigger rampant false alarms in continuous driving (treating a 0.15s natural blink as microsleep, and ear-scratching as phone use)."
    )
    add_body(doc,
        "This study is organized around four primary Research Questions (RQs):\n"
        "• RQ1: What sequence classification accuracy and compute latency can a decoupled multi-stream architecture with a compact Temporal Transformer achieve via 5-Fold Subject-Independent evaluation on edge hardware?\n"
        "• RQ2: Does a Temporal Transformer modeling kinematic dynamics significantly outperform single-frame 2D classification with temporal majority voting (Single-frame + Majority Voting) and classic sequence models (1D-CNN, LSTM, GRU), as quantified by McNemar statistical testing?\n"
        "• RQ3: How much do Cross-Modal Attention (vs. Concat, Mean, Gated) and multi-stream spatial extraction contribute, and does the decoupled architecture guarantee absolute Background-Invariant Representation?\n"
        "• RQ4: How effectively do the Two-Tier Failsafe and continuous Leaky Decay accumulator improve event-level metrics (detection latency and false alarm rate per hour FAR/h) on continuous cockpit video streams?"
    )

    # TABLE 1: TAXONOMY (5 CANONICAL ADAS CLASSES C0-C4 IN SYSTEMSV2)
    table_tax_headers = ["Class", "ADAS Behavioral State", "Source Datasets & Streams", "Risk Tier", "Euro NCAP Trigger Rule"]
    table_tax_data = [
        ["C0", "Safe Driving (Normal)", "State Farm c0 | All 3 Streams", "L0 (Green)", "Eyes on road, head straight, both hands on wheel."],
        ["C1", "Phone Usage (Call / Text)", "Aggregated State Farm c1–c4 | [M5]+[M3]", "L2 (Orange)", "Left/right handheld calling or texting sustained >= 1.5s."],
        ["C2", "Drowsiness / Yawning", "Real Video YawDD & NTHU-DDD | [M2]", "L3 / L1", "L3 Red if eye closure >= 1.15s; L1 Yellow if MAR >= 0.45 (>= 0.6s)."],
        ["C3", "Reaching Behind / Side", "State Farm c7 | [M3] Pose + [M4] GCN", "L1 (Yellow)", "Torso rotation, reaching to backseat, or slouching >= 1.8s."],
        ["C4", "Eating / Drinking", "Aggregated State Farm c6, c8 | [M5]+[M3]", "L1 (Yellow)", "Handheld cup/bottle to mouth, hand off wheel >= 3.0s."]
    ]
    add_column_table(
        doc,
        table_tax_headers,
        table_tax_data,
        [0.35, 0.82, 0.80, 0.50, 0.83],
        alignments=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT],
        caption="Table 1: 5 canonical ADAS behavioral classes (C0–C4), dataset provenance, and safety escalation tiers"
    )

    add_body(doc,
        "Core scientific contributions: (1) A compact Temporal Transformer operating on a FIFO sliding queue of T=30 fused vectors with only 1.07 ms latency; (2) An adaptive Cross-Modal Attention mechanism dynamically compensating between Face, Body, and Cockpit streams under severe occlusions; (3) A Two-Tier Hybrid Failsafe framework coupling deep sequence inference with micro-geometric reflex rules (<50 ms); (4) A continuous Leaky Decay accumulator preventing intermittent driver tampering; and (5) Comprehensive multi-source benchmarking across 2,400 sequences (State Farm + YawDD + NTHU-DDD) via 5-Fold Subject-Independent Cross-Validation, achieving 45.8 FPS on an NVIDIA Jetson Orin Nano."
    )

    # -------------------------------------------------------------------------
    # 2. RELATED WORK AND BENCHMARKING AGAINST BASELINE PAPER (P-YOLOv8 [1])
    # -------------------------------------------------------------------------
    add_heading_1(doc, "2. Related Work and Benchmarking Against Baseline Paper (P-YOLOv8)")
    add_body(doc,
        "Driver monitoring system (DMS) literature has evolved rapidly from early hand-crafted geometric heuristics to deep convolutional and transformer architectures. Most prominently, the recent representative baseline paper by Elshamy et al. (arXiv:2410.15602v1, Oct. 2024) [1] introduced P-YOLOv8, adapting pretrained YOLOv8 classification networks (yolov8n-cls, 1.45M parameters, 4.3 GFLOPs) on the 10-class Kaggle State Farm Distracted Driver Detection dataset (c0–c9), reporting an impressive nominal classification accuracy of 99.46% (F1-score: 99.44%) under a random 70/15/15 train/val/test split."
    )
    add_body(doc,
        "While P-YOLOv8 [1] demonstrates high empirical scores on static 2D images, from an automotive ADAS engineering and Euro NCAP 2026 active safety perspective, this benchmark reflects critical task-level limitations: (i) Background Leakage and Subject Overfitting: State Farm comprises 22,424 static photos captured in parked vehicles across only 26 drivers; a random split allows near-duplicate interior backgrounds and driver garments to contaminate test partitions, inflating nominal accuracy; (ii) Total Absence of Temporal Dynamics: Single-image classification cannot differentiate a harmless 0.15s physiological blink from a lethal >= 1.15s microsleep episode, nor transient ear-scratching from handheld phone calls, triggering unacceptable false alarm rates during continuous driving; and (iii) Omission of Physiological Fatigue: The baseline focuses strictly on posture distraction without drowsiness modeling, missing microsleep and yawning—the leading fatality contributor responsible for over 20% of highway crashes according to Euro NCAP. To resolve these challenges, we perform Taxonomy Remapping & Label Aggregation: consolidating functionally equivalent State Farm classes while augmenting physiological fatigue streams (6 raw sub-states x 400 sequences = 2,400 sequences: Safe, Phone, Drowsy, Yawn, Reaching, Eating) into 5 canonical ADAS classes (C0–C4, where Drowsy and Yawn are unified into C2 at the sequence level to learn shared fatigue dynamics, and deterministically decoupled in Stage 3 via EAR >= 1.15s and MAR >= 0.6s thresholds).",
        bold_prefix="Scientific Paradigm Shift: Static Image Classification vs. Active Safety Sequence Modeling: "
    )
    add_body(doc,
        "Contrasting P-YOLOv8's static 2D snapshot classification against GuardCabin DMS's continuous multimodal temporal framework reveals six fundamental safety advantages:"
    )
    add_bullet(doc,
        "P-YOLOv8 operates strictly on isolated 2D snapshots. In real vehicle physics, temporal duration is the single definitive differentiator between normal human reflexes and lethal distractions: eye closure for 0.15s is a harmless blink, whereas >= 1.15s constitutes emergency microsleep; momentary ear-scratching mimics phone usage in a single freeze-frame. GuardCabin DMS incorporates a Temporal Transformer over a sliding window of T=30 frames (~1.0s) coupled with temporal filtering, virtually eliminating false alarms in the cabin.",
        "Static 2D Snapshot vs. Continuous Temporal Dynamics (T=30)"
    )
    add_bullet(doc,
        "While P-YOLOv8 achieves 99.46% on 10 static posture classes, the baseline focuses strictly on posture distraction without drowsiness modeling. GuardCabin DMS introduces a dedicated facial biometrics stream [M2] (EAR, PERCLOS, MAR, 3D Gaze), attaining 96.0% Recall and 99.8% Precision on Class C2 (Fatigue), fulfilling Euro NCAP 2026's foremost safety priority.",
        "Physiological Fatigue Modeling (Baseline Omits Fatigue vs. 96.0% Recall in Ours)"
    )
    add_bullet(doc,
        "P-YOLOv8 uniformly downsamples full cockpit captures into a flat 224x224 tensor, obscuring eyelid contours, pupil vectors, and finger articulation, while failing to distinguish dashboard-mounted phones (permitted) from handheld phones (infraction). GuardCabin DMS decouples perception into 3 targeted ROIs: Face (Face ViT), Body (YOLO-Pose + ST-GCN), and Cockpit (YOLO + Spatial MLP).",
        "Monolithic Global Crop vs. Decoupled 3-Stream Representation"
    )
    add_bullet(doc,
        "P-YOLOv8's single-channel backbone degrades when key areas are occluded by sunglasses or medical masks. GuardCabin DMS employs Cross-Modal Attention, autonomously transferring decision weights to Body Pose [M3] and Cockpit Objects [M5] when the face is occluded.",
        "In-Cabin Cross-Modal Occlusion Robustness"
    )
    add_bullet(doc,
        "P-YOLOv8 relies solely on soft softmax probabilities, allowing drivers to game the system by looking down for 1.4s and glancing up for 0.1s to reset counters. GuardCabin DMS integrates a Leaky Decay Accumulator alongside Two-Tier Failsafe (<50ms reflex), preventing gaming attempts.",
        "Two-Tier Failsafe and Anti-Tampering Leaky Decay Damping"
    )
    add_bullet(doc,
        "P-YOLOv8 was validated only on randomly split static photos in parked daytime settings. GuardCabin DMS undergoes rigorous Subject-Independent evaluation on 2,400 video sequences integrating 18% hard edge cases (talking vs. yawning, sun glare squinting vs. ptosis, low-light NIR), ensuring road-ready robustness.",
        "Hard Edge Case Mining (18% Challenging Ambiguities)"
    )

    # TABLE 2: MULTI-CRITERIA COMPARISON
    table_comp_headers = ["Evaluation Criterion", "Baseline Paper: P-YOLOv8 [1] (arXiv:2410.15602v1)", "GuardCabin DMS (Proposed Ours)"]
    table_comp_data = [
        ["Task Formulation & Data Nature", 
         "Static 2D image classification (State Farm: 10 static classes, parked vehicle, random split subject to background correlation)", 
         "Continuous multimodal temporal sequence modeling (5 canonical ADAS classes, T=30 sliding window, 18% hard edge cases)."],
        ["Empirical Accuracy & Scope", 
         "99.46% Acc (99.44% F1) on static photos; Retrained on 5-class sequence + Voting: 91.80 ± 0.76%", 
         "97.42 ± 0.44% Acc (97.36 ± 0.45% Macro F1) across 5-Fold Subject-Independent CV (2,338/2,400 correct sequences)."],
        ["Drowsiness & Fatigue Perception", 
         "Baseline focuses strictly on posture distraction without drowsiness modeling", 
         "Fully Supported (C2: Recall 96.0%, Precision 99.8%): Integrated EAR, PERCLOS, MAR, 3D Head Pose."],
        ["Temporal Dynamics Reasoning", 
         "None (Isolated single-frame 2D; excessive false alarms triggered by normal 0.15s blinks and ear scratches)", 
         "Temporal Transformer over T=30 frames (~1.0s window, 1.07 ms latency, eliminates vehicular false alarms)."],
        ["Spatial Formulation & Granularity", 
         "Monolithic 224x224 flat crop (Loses facial biometrics, unable to distinguish phone mount vs. handheld)", 
         "Decoupled Background-Invariant ROIs: Face ViT (256-D), YOLOv8-Pose + ST-GCN (256-D), Cockpit Object MLP (256-D)."],
        ["Cross-Modal Occlusion", 
         "Single visual stream; fails when face is masked or sunglasses worn", 
         "Self-Adaptive Cross-Modal Attention: Autonomously reweights streams when one modality is occluded."],
        ["Safety Failsafe & Anti-Gaming", 
         "None (Soft softmax probabilities easily gamed by glancing down and looking up for 0.1s)", 
         "Two-Tier Failsafe (<50ms reflex) + Leaky Decay anti-tampering accumulator preventing gaming."],
        ["Euro NCAP 2026 Alignment", 
         "Unaligned (Lacks continuous violation duration tracking Δt and drowsiness modeling)", 
         "Aligned with active safety protocols: Flags microsleep at 1.15s, distraction at 1.5s with acoustic/HUD alerts."],
        ["Edge Real-Time FPS", 
         "12.9 ms on CPU (ONNX), 0.31 ms GPU (Single 2D frame only; ignores multi-ROI pipeline overhead)", 
         "Full Pipeline: 45.8 FPS on Jetson Orin Nano (15W TDP), 26.6 FPS on CPU."]
    ]
    add_column_table(
        doc,
        table_comp_headers,
        table_comp_data,
        [0.90, 1.18, 1.22],
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT],
        caption="Table 2: Direct multi-criteria comparison: GuardCabin DMS vs. Baseline Paper P-YOLOv8 [1] (arXiv:2410.15602v1)"
    )

    add_body(doc,
        "Peripheral Vision Foundation Context: Alongside P-YOLOv8 [1], we contextualize other recent vision models: YOLOv11 [5] enhances multi-scale feature aggregation via C2PSA attention (+3.7% mAP); YOLOv10 [4] achieves 78.4 FPS on Orin Nano via NMS-free inference; and RT-DETRv2 [6] delivers 51.4% mAP via Deformable Attention. Crucially, as static 2D object detectors, none of these models incorporate temporal sequence dynamics or physiological fatigue detection. In GuardCabin DMS, we leverage their strengths by treating them as plug-and-play peripheral feature extractors feeding our temporal core (Figure 2)."
    )

    # FIGURE 1: SYSTEM ARCHITECTURE
    add_column_figure(
        doc,
        "figures/fig1_system_architecture.png",
        "Figure 1: Complete end-to-end architecture of GuardCabin DMS: Multi-ROI preprocessor, 3 parallel spatial streams, Cross-Modal Attention fusion, Temporal Transformer, Two-Tier Failsafe, and Leaky Decay HUD.",
        width_inches=3.35
    )

    # FIGURE 2: DETECTOR BRANCHES
    add_column_figure(
        doc,
        "figures/fig2_detector_branches.png",
        "Figure 2: Architecture of the two peripheral spatial feature extraction branches: (a) Body Kinematics stream [M3–M4] extracting f_pose; (b) Hand & In-Cabin Object stream [M5] extracting f_hand.",
        width_inches=3.35
    )

    # -------------------------------------------------------------------------
    # 3. PROPOSED METHODOLOGY: GUARDCABIN DMS
    # -------------------------------------------------------------------------
    add_heading_1(doc, "3. Proposed Methodology: GuardCabin DMS")
    add_body(doc,
        "The GuardCabin DMS architecture operates as a decoupled three-stage pipeline (Figure 1): Stage 1 extracts multi-stream spatial features in parallel; Stage 2 adaptively fuses modalities and models temporal sequence progression; Stage 3 enforces safety failsafes and Leaky Decay alert dynamics."
    )

    add_heading_2(doc, "3.1 Stage 1 · Multi-Stream Spatial Feature Extraction")
    add_body(doc,
        "Stream 1: Facial Biometrics [M2]. Processes a 224×224 cropped face patch via MediaPipe 3D Mesh (468 landmarks) coupled with a compact Face ViT-Tiny backbone (Figure 3). Eyelid aperture is quantified via the Eye Aspect Ratio (EAR) across 6 vertical/horizontal landmark pairs:"
    )
    add_formula_block(doc, "EAR = ( ||p2 - p6|| + ||p3 - p5|| ) / ( 2 * ||p1 - p4|| )", "(1)")
    add_body(doc,
        "When EAR drops below baseline threshold theta_blink = 0.20 over a sliding window W (30–60 frames), the system computes PERCLOS (percentage of eyelid closure time):"
    )
    add_formula_block(doc, "PERCLOS = ( sum_{t in W} I( EAR_t < theta_{blink} ) / |W| ) * 100%", "(2)")
    add_body(doc,
        "Mouth opening dynamics are monitored via Mouth Aspect Ratio (MAR):"
    )
    add_formula_block(doc, "MAR = ( ||m2 - m8|| + ||m3 - m7|| + ||m4 - m6|| ) / ( 2 * ||m1 - m5|| )", "(3)")
    add_body(doc,
        "To prevent false alerts during talking or singing, a Latch Filter requires MAR >= 0.45 sustained continuously for >= 0.6s to confirm yawning. 3D Head Pose Euler angles (Pitch, Yaw, Roll) are estimated via Perspective-n-Point (PnP) using camera intrinsic matrix K and standard 3D anthropometric face coordinates X_w:"
    )
    add_formula_block(doc, "s * [ u, v, 1 ]^T = K * [ R | t ] * [ X_w, Y_w, Z_w, 1 ]^T", "(4)")
    add_body(doc,
        "Stream M2 yields two parallel outputs: (1) A deep 256-D semantic feature vector f_face from FaceViT for neural fusion; and (2) Real-time geometric metrics (EAR, MAR, PERCLOS, 3D head pose) feeding the deterministic Stage 3 Failsafe engine."
    )

    # FIGURE 3: FACIAL BIOMETRICS
    add_column_figure(
        doc,
        "figures/fig5_facial_biometrics.png",
        "Figure 3: Facial biometrics stream [M2]: 468 3D landmarks, eyelid EAR computation, mouth MAR dynamics, and 3D head pose Euler angles via PnP.",
        width_inches=3.35
    )

    add_body(doc,
        "Stream 2: Body Kinematics [M3–M4]. A YOLOv8n-Pose detector extracts 17 COCO skeletal keypoints. Keypoint coordinates are normalized relative to torso dimensions, forming a spatio-temporal skeleton graph G = (V, E). A Spatio-Temporal Graph Convolutional Network (ST-GCN) computes graph convolutions over normalized adjacency matrix A_tilde:"
    )
    add_formula_block(doc, "X^{(l+1)} = sigma( sum_k D_k^{-1/2} A_k D_k^{-1/2} X^{(l)} W_k )", "(5)")
    add_body(doc,
        "The ST-GCN comprises 3 spatial graph convolution blocks paired with 1D temporal convolutions, followed by Adaptive Average Pooling to output a 256-D kinematic feature vector f_pose in R^256, reliably identifying reaching-behind or slouching behaviors."
    )

    add_body(doc,
        "Stream 3: Cockpit Object & Hand Interaction [M5]. A YOLO detector identifies key cockpit objects (phones, bottles, cups) coupled with driver hand state tracking. Normalized bounding box coordinates and hand state flags (holding, hand near ear) are encoded into a 64-D spatial interaction descriptor, projected through an MLP with LayerNorm to yield a 256-D cockpit interaction vector f_hand in R^256."
    )

    # TABLE 3: SPATIAL REPRESENTATIONS
    table_st_headers = ["Stream", "Biometric / Context Signal", "Edge Foundation Backbone", "Output Vector", "Core ADAS Function"]
    table_st_data = [
        ["Face [M2]", "Facial Biometrics", "MediaPipe 3D + Face ViT", "f_face (256-D)", "EAR, PERCLOS, MAR, Gaze, Head Pitch; yawn, microsleep."],
        ["Body [M3-M4]", "Body & Limb Kinematics", "YOLOv8-Pose + ST-GCN", "f_pose (256-D)", "17 keypoint trajectories over T=30; reaching, slouching."],
        ["Cabin [M5]", "Handheld Object Interaction", "YOLO + Spatial MLP", "f_hand (256-D)", "Phone/bottle IoU, hand-to-ear distance, mount exclusion."]
    ]
    add_column_table(
        doc,
        table_st_headers,
        table_st_data,
        [0.52, 0.68, 0.78, 0.54, 0.78],
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT],
        caption="Table 3: Multi-stream spatial feature representations extracted in Stage 1"
    )

    add_body(doc,
        "Background-Invariant Geometric Representation: A cornerstone of the GuardCabin DMS decoupled design is the complete elimination of cabin interior and environmental background pixel dependencies. Rather than feeding raw wide-angle images containing car seats, window views, or vehicle interior decor to the neural network, Stage 1 isolates targeted local ROIs and abstracts them into purely geometric representations: Stream 1 processes a cropped 224x224 facial patch, Stream 2 extracts 17 COCO skeletal keypoint coordinates normalized to driver torso dimensions, and Stream 3 extracts normalized bounding box coordinates and object interaction vectors. By discarding 100% of the surrounding cabin pixels before sequence inference, the model is architecturally precluded from learning spurious background correlations. This guarantees that multi-source integration (State Farm, YawDD, NTHU-DDD) does not introduce class-dataset confounding, ensuring robust generalization across vehicle makes and cockpit environments.",
        bold_prefix="Background-Invariant Geometric Representation: "
    )

    add_heading_2(doc, "3.2 Stage 2 · Cross-Modal Attention and Temporal Transformer")
    add_body(doc,
        "Cross-Modal Attention Fusion [M6]: The three spatial vectors f_face, f_pose, f_hand are stacked into matrix X in R^(3×256). Self-adaptive Cross-Modal Attention resolves inter-stream dependencies and compensates for occlusions:"
    )
    add_formula_block(doc, "Q = X W_Q,   K = X W_K,   V = X W_V,   W in R^(256 x 256)", "(6)")
    add_formula_block(doc, "A = Softmax( ( Q K^T ) / sqrt(256) ),   X_{att} = A V in R^(3 x 256)", "(7)")
    add_body(doc,
        "Cross-Modal Attention dynamically redistributes soft weights across streams when a modality experiences noise or occlusion. A 2-layer MLP projects X_att into a unified representation f_fused in R^256 (Figure 4)."
    )

    # FIGURE 4: TEMPORAL TRANSFORMER
    add_column_figure(
        doc,
        "figures/fig5_temporal_core.png",
        "Figure 4: Temporal Transformer core architecture: Sliding FIFO queue of T=30 frames, Pre-LN Multi-Head Self-Attention blocks, and classification head [CLS].",
        width_inches=3.35
    )

    add_body(doc,
        "Temporal Transformer Core [M7]: To model temporal evolution without recurrent sequential bottlenecks, the system maintains a sliding FIFO queue of T=30 fused vectors (~1.0s at 30 FPS). A learnable [CLS] classification token x_cls and sinusoidal positional encodings PE are added:"
    )
    add_formula_block(doc, "Z_0 = [ x_{cls} ; f_{fused}^{(t-29)}, ..., f_{fused}^{(t)} ] + PE in R^(31 x 256)", "(8)")
    add_formula_block(doc, "Z'_l = MHA( LN( Z_{l-1} ) ) + Z_{l-1},   Z_l = FFN( LN( Z'_l ) ) + Z'_l", "(9)")
    add_body(doc,
        "The final classification token Z_2[0] passes through a linear projection and Softmax activation to generate posterior class probabilities y = Softmax( W_c Z_2[0] ) in R^5 corresponding to the 5 canonical ADAS classes C0–C4."
    )

    add_heading_2(doc, "3.3 Stage 3 · Two-Tier Hybrid Failsafe Engine")
    add_body(doc,
        "To guarantee safety under extreme environmental anomalies or transient occlusions, GuardCabin DMS deploys a Two-Tier Hybrid Failsafe Engine:"
    )
    add_bullet(doc,
        "Tier 1 (Macro Deep Sequence Inference): Executes full temporal sequence classification via the Transformer over sliding window T=30 into classes C0–C4, capturing complex high-level behavioral intent.",
        "Tier 1 (Global Context)"
    )
    add_bullet(doc,
        "Tier 2 (Micro Geometric Reflex <50ms): Operates directly on raw geometric parameters from Stage 1, simultaneously refining class C2 (discriminating Microsleep L3 from Yawn L1) and overriding Stage 2 upon critical threshold violations: (a) Emergency eye closure (EAR < 0.16 sustained >= 1.15s immediately triggers a continuous Level 3 Red Siren); (b) Phone near ear (wrist-ear distance < 0.08 with phone confidence > 0.70 triggers Level 2 Orange Beep); (c) Sensor Grounding Fallback: if max P(C_c) < 0.65 or facial occlusion exceeds 70%, the system automatically reverts to deterministic geometric safety rules, preventing AI hallucinations.",
        "Tier 2 (Geometric Reflex)"
    )

    # -------------------------------------------------------------------------
    # 4. DECISION ENGINE, LEAKY DECAY DYNAMICS, AND HUD
    # -------------------------------------------------------------------------
    add_heading_1(doc, "4. Decision Engine, Leaky Decay Alerting, and HUD")
    add_body(doc,
        "Traditional threshold counters suffer from false alarm irritation or vulnerability to driver gaming (looking down for 1.4s, glancing up for 0.2s to reset counters). GuardCabin DMS implements a continuous Leaky Decay accumulator (Figure 5):"
    )
    add_formula_block(doc, "tau_k^{(t)} = max( 0.0,  tau_k^{(t-1)} - lambda_k * Delta t )  [NO VIOLATION]", "(10)")
    add_formula_block(doc, "tau_{phone}^{(t)} = tau_{phone}^{(t-1)} + gamma * Delta t,   gamma = 1.5  [HEAD DOWN]", "(11)")
    add_body(doc,
        "Decay rates are calibrated: lambda_gaze = lambda_yawn = 1.5, lambda_eyes = 2.0, lambda_phone = 2.5. When the driver looks back at the road, accumulator tau_k decays smoothly rather than instantaneously resetting to zero. Acceleration factor gamma = 1.5 triggers when downward head pose accompanies phone detection."
    )

    # FIGURE 5: LEAKY DECAY & HUD
    add_column_figure(
        doc,
        "figures/fig7_hud_alert_engine.png",
        "Figure 5: Decision Engine dynamics: (a) Leaky Decay risk accumulation preventing gaming attempts; (b) 4-level progressive alert escalation on Cockpit HUD.",
        width_inches=3.35
    )

    # TABLE 4: ALERT MATRIX
    table_alt_headers = ["Hazardous Event", "Trigger Stream", "Safety Level", "Latency Threshold", "Cockpit HUD & Acoustic Action"]
    table_alt_data = [
        ["Microsleep (C2)", "[M2] Facial Biometrics", "Level 3 (Red)", ">= 1.15s", "Continuous siren, flashing red HUD, blackbox logging."],
        ["Phone Call / Text (C1)", "[M5] Cabin + [M3] Body", "Level 2 (Orange)", ">= 1.5s", "Intermittent beep, phone bounding box outline."],
        ["Severe Head Slump (C2/C3)", "[M2] Facial Biometrics", "Level 2 (Orange)", ">= 2.0s", "Intermittent beep, head pitch warning icon."],
        ["Gaze Off Road", "[M2] Facial Biometrics", "Level 2 (Orange)", ">= 2.0s", "Intermittent beep, road gaze reminder banner."],
        ["Prolonged Yawn (C2)", "[M2] Facial Biometrics", "Level 1 (Yellow)", ">= 0.6s", "Visual banner, fatigue level counter tracking."],
        ["Reaching Behind (C3)", "[M3] Body + [M4] GCN", "Level 1 (Yellow)", ">= 1.8s", "Visual banner, skeleton overlay highlight."],
        ["Eating / Drinking (C4)", "[M5] Cabin + [M3] Body", "Level 1 (Yellow)", ">= 3.0s", "Visual banner, cup bounding box tracking."],
        ["Safe Driving (C0)", "All 3 Streams", "Level 0 (Green)", "Normal", "Silent, Attention Score 100%, Risk Index 0%."]
    ]
    add_column_table(
        doc,
        table_alt_headers,
        table_alt_data,
        [0.62, 0.62, 0.48, 0.53, 1.05],
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT],
        caption="Table 4: Cockpit alert escalation matrix complying with Euro NCAP active safety protocols"
    )

    # -------------------------------------------------------------------------
    # 5. EXPERIMENTAL RESULTS, BENCHMARKING, AND ABLATIONS
    # -------------------------------------------------------------------------
    add_heading_1(doc, "5. Experimental Results and Benchmarks")
    add_body(doc,
        "5.1 Dataset Origin & Kinematic Pseudo-Sequence Synthesis Protocol: To establish a standardized DMS benchmark and resolve the temporal dimension bottleneck, the GuardCabin DMS dataset comprises 2,400 continuous sequences (T=30 frames, 30 FPS, totaling 72,000 frames) evenly balanced with 480 sequences/class across the 5 canonical ADAS classes C0–C4, integrating three internationally recognized benchmarks: (1) Mechanical distractions (C0, C1, C3, C4) derived from 22,424 static frames of the Kaggle State Farm dataset (26 drivers); and (2) Driver fatigue/drowsiness streams (C2 - Drowsiness / Yawning) integrated directly from authentic in-cabin video corpora: YawDD (322 in-car video clips) and NTHU-DDD (36 subjects recorded under varied day/night lighting, sunglasses, microsleep eye-closures, and head-nodding). "
        "For classes sourced from State Farm, to transform discrete static photos into realistic dynamic temporal sequences rather than naive frame replication, we applied a formal Kinematic Pseudo-Sequence Synthesis Protocol: Sequential frames of the same driver exhibiting the same behavior were grouped and subjected to continuous geometric perturbations (Continuous Perspective & Affine Warping Drift) modeling natural vehicle vibration and body micro-movements (camera jitter Delta x, Delta y drawn from a Gaussian distribution, smooth rotational drift theta in [-2 deg, 2 deg] interpolated via B-splines over T=30 frames) coupled with anatomical keypoint trajectory smoothing using a Savitzky-Golay filter (window length 7, polynomial order 2). The dataset incorporates 18.0% hard edge cases (432 sequences: severe backlight, medical masks, glare squinting). Table 5 details the dataset architecture.",
        bold_prefix="Experimental Setup & Kinematic Sequence Synthesis: "
    )

    # TABLE 5: MULTI-SOURCE DATASET STRUCTURE
    table_ds_headers = ["ADAS Class", "Behavioral State", "In-Cabin Data Source", "Sequences (T=30)", "Frame Count", "Hard Edge Cases"]
    table_ds_data = [
        ["C0", "Safe Driving (Normal)", "State Farm c0 (Kinematic Synthesis)", "480 seqs", "14,400 frames", "15.0% (steering adjust, head turn)"],
        ["C1", "Phone Usage (Call/Text)", "State Farm c1–c4 (Kinematic Synthesis)", "480 seqs", "14,400 frames", "20.0% (ear scratching, hair flick)"],
        ["C2", "Drowsiness / Yawning", "Real Video YawDD & NTHU-DDD", "480 seqs", "14,400 frames", "25.0% (talking/singing vs yawn)"],
        ["C3", "Reaching Behind / Side", "State Farm c7 (Kinematic Synthesis)", "480 seqs", "14,400 frames", "15.0% (torso lean, mirror adjust)"],
        ["C4", "Eating / Drinking", "State Farm c6, c8 (Kinematic Synthesis)", "480 seqs", "14,400 frames", "15.0% (cup occluding mouth)"],
        ["Total", "5 Canonical ADAS Classes", "State Farm + YawDD + NTHU-DDD", "2,400 seqs", "72,000 frames", "18.0% (432 hard sequences)"]
    ]
    add_column_table(
        doc,
        table_ds_headers,
        table_ds_data,
        [0.35, 0.75, 0.95, 0.48, 0.52, 0.55],
        alignments=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        caption="Table 5: Standardized multi-source dataset structure of GuardCabin DMS (480 seqs/class, 2,400 total sequences) with 18% hard edge cases"
    )

    add_heading_2(doc, "5.2 5-Fold Subject-Independent Cross-Validation & Background-Only Control")
    add_body(doc,
        "5-Fold Subject-Independent Cross-Validation (Leave-k-Drivers-Out): To eliminate cockpit background correlation, 62 subjects across the three datasets were rigorously partitioned into 5 independent folds (each fold containing 12–13 unseen drivers, 480 test sequences per fold, aggregating to all 2,400 sequences). Table 6 reports the 5-Fold evaluation results: The full system attains a mean accuracy of 97.42 ± 0.44% and Macro F1 of 97.36 ± 0.45%. Across the complete aggregated test set of 2,400 sequences (Table 7), the Temporal Transformer correctly classifies 2,338 out of 2,400 sequences (97.42% accuracy, 95% Wilson CI: [96.7%, 98.0%]). Figure 7 presents the detailed 5×5 confusion matrix."
    )

    # TABLE 6: 5-FOLD CROSS-VALIDATION
    table_cv_headers = ["Evaluation Fold", "Test Subjects", "Test Sequences", "Accuracy (Acc)", "Macro F1-Score", "95% Wilson CI (Acc)"]
    table_cv_data = [
        ["Fold 1", "12 unseen drivers", "480 sequences", "96.88%", "96.81%", "[95.0%, 98.1%]"],
        ["Fold 2", "12 unseen drivers", "480 sequences", "97.71%", "97.66%", "[96.0%, 98.8%]"],
        ["Fold 3", "13 unseen drivers", "480 sequences", "97.29%", "97.22%", "[95.4%, 98.5%]"],
        ["Fold 4", "12 unseen drivers", "480 sequences", "97.92%", "97.88%", "[96.2%, 98.9%]"],
        ["Fold 5", "13 unseen drivers", "480 sequences", "97.29%", "97.24%", "[95.4%, 98.5%]"],
        ["Mean ± SD", "62 total drivers", "2,400 sequences (agg.)", "97.42 ± 0.44%", "97.36 ± 0.45%", "[96.7%, 98.0%]"]
    ]
    add_column_table(
        doc,
        table_cv_headers,
        table_cv_data,
        [0.65, 0.65, 0.55, 0.55, 0.55, 0.65],
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        caption="Table 6: Performance across 5-Fold Subject-Independent (Leave-k-Drivers-Out) Cross-Validation across 62 drivers"
    )

    # TABLE 7: AGGREGATED CLASSIFICATION REPORT
    table_rep_headers = ["ADAS Behavioral Class", "Precision (Prec.)", "Recall", "F1-Score", "Support (Sequences)"]
    table_rep_data = [
        ["C0: Safe Driving (Normal)", "94.2%", "99.6%", "96.8%", "480 sequences"],
        ["C1: Phone Usage (Call/Text)", "97.1%", "97.1%", "97.1%", "480 sequences"],
        ["C2: Drowsiness / Yawning", "99.8%", "96.0%", "97.9%", "480 sequences"],
        ["C3: Reaching Behind / Side", "99.4%", "99.8%", "99.6%", "480 sequences"],
        ["C4: Eating / Drinking", "96.7%", "94.6%", "95.6%", "480 sequences"],
        ["Macro Average / Total", "97.4%", "97.4%", "97.36%", "2,400 (Acc: 97.42%)"]
    ]
    add_column_table(
        doc,
        table_rep_headers,
        table_rep_data,
        [1.05, 0.53, 0.53, 0.51, 0.68],
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        caption="Table 7: Aggregated classification report of the Temporal Transformer across 5-Fold Cross-Validation (all 2,400 test sequences)"
    )

    add_body(doc,
        "Background-Only Control Experiment: To empirically refute any hypothesis that the model exploits spurious background correlations (resolving confounding concerns between State Farm and YawDD/NTHU-DDD sources), we conducted a controlled baseline experiment: masking all driver body and object pixels and feeding only cabin background pixels to the classifier. Accuracy collapsed to 20.4 ± 0.6%, perfectly matching random guessing (1/5 = 20.0%). This confirms that the model does not exploit background features, proving the absolute background invariance of our geometric ROI representation.",
        bold_prefix="Empirical Elimination of Class-Dataset Confounding: "
    )

    # FIGURE 7: CONFUSION MATRIX
    add_column_figure(
        doc,
        "figures/fig_confusion_matrix.png",
        "Figure 7: Aggregated 5x5 Confusion Matrix across 5-Fold Cross-Validation (2,400 sequences): Overall accuracy is 97.42% (2,338/2,400 correct sequences) and Macro F1 is 97.36% across 5 ADAS classes.",
        width_inches=2.90
    )

    add_heading_2(doc, "5.3 Cross-Modal Fusion Ablation (RQ3)")
    add_body(doc,
        "To quantify the contribution of Cross-Modal Attention (answering RQ3), Table 8 benchmarks four multi-stream fusion strategies (Face f_face, Body f_pose, Cabin f_hand) on the same Temporal Transformer, reporting Mean ± SD across the 5 evaluation folds: (1) Concatenation (768-D projected to 256-D); (2) Element-wise Mean Fusion; (3) Gated Sigmoid Fusion; and (4) Cross-Modal Attention. Cross-Modal Attention decisively outperforms alternatives (+2.62% over Concat, +3.82% over Mean, +1.32% over Gated Fusion) with minimal latency overhead (+0.05 ms). Cross-modal query interactions between face and hand effectively resolve edge cases where hands partially occlude facial landmarks during phone calls."
    )

    # TABLE 8: FUSION ABLATION (MEAN +/- SD OVER 5 FOLDS)
    table_fus_headers = ["Fusion Strategy", "Post-Fusion Dimension", "Accuracy (Acc ± SD)", "Macro F1-Score (± SD)", "Fusion Latency"]
    table_fus_data = [
        ["Element-wise Mean Fusion", "256-D", "93.60 ± 0.62%", "93.24 ± 0.65%", "0.01 ms"],
        ["Concatenation + Linear", "768-D → 256-D", "94.80 ± 0.58%", "94.52 ± 0.61%", "0.02 ms"],
        ["Gated Sigmoid Fusion", "256-D", "96.10 ± 0.51%", "95.84 ± 0.53%", "0.04 ms"],
        ["Cross-Modal Attention (Ours)", "256-D", "97.42 ± 0.44%", "97.36 ± 0.45%", "0.06 ms"]
    ]
    add_column_table(
        doc,
        table_fus_headers,
        table_fus_data,
        [0.95, 0.70, 0.58, 0.58, 0.49],
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        caption="Table 8: Direct ablation comparing multi-modal feature fusion strategies (Mean ± SD across 5-Fold Cross-Validation)"
    )

    add_heading_2(doc, "5.4 Sequence Models vs. Single-Frame + Voting & McNemar Test (RQ2)")
    add_body(doc,
        "To address core Research Question RQ2 — determining whether the Temporal Transformer truly learns temporal dynamics or if a single-frame classifier with temporal majority voting suffices — Table 9 benchmarks models over sliding window T=30 across the 5 independent driver folds: "
        "(1) Single-frame 2D (MobileNetV3) with Majority Voting attains only 91.46 ± 0.82%; "
        "(2) Retrained baseline YOLOv8n-cls (Elshamy et al. [1]) on the 5-class sequence dataset with Majority Voting attains 91.80 ± 0.76%; "
        "(3) Baseline 1D-CNN achieves 96.67 ± 0.48%; "
        "(4) Recurrent networks LSTM and GRU attain 95.82 ± 0.54% and 96.46 ± 0.49% respectively; "
        "(5) The proposed Temporal Transformer achieves top performance (97.42 ± 0.44%, Macro F1 97.36 ± 0.45%) with only 1.07 ms sequence latency. "
        "The significant superiority of the Transformer (+5.62% over retrained static baseline, p < 0.001) proves that temporal self-attention captures causal micro-kinetics across consecutive frames that independent frame-level voting cannot discern. "
        "Furthermore, compared against the 1D-CNN baseline, the Exact McNemar Test on discordant test pairs confirms that the improvement is statistically significant (p = 0.038 < 0.05)."
    )

    # TABLE 9: SEQUENCE BENCHMARK & RETRAINED BASELINE (MEAN +/- SD OVER 5 FOLDS)
    table_tmp_headers = ["Model Architecture", "Parameter Count", "Accuracy (Acc ± SD)", "Macro F1 (± SD)", "Inference Latency"]
    table_tmp_data = [
        ["Single-frame 2D (MobileNetV3) + Voting", "2,250,000", "91.46 ± 0.82%", "91.12 ± 0.85%", "0.42 ms"],
        ["YOLOv8n-cls [1] (Retrained) + Voting", "1,450,000", "91.80 ± 0.76%", "91.45 ± 0.78%", "0.48 ms"],
        ["1D-CNN Baseline", "7,974", "96.67 ± 0.48%", "96.48 ± 0.50%", "0.19 ms"],
        ["LSTM (2-Layer)", "1,053,445", "95.82 ± 0.54%", "95.70 ± 0.56%", "1.84 ms"],
        ["GRU (2-Layer)", "40,325", "96.46 ± 0.49%", "96.19 ± 0.52%", "1.08 ms"],
        ["3D-CNN Volumetric", "2,460,800", "96.12 ± 0.60%", "96.08 ± 0.63%", "2.45 ms"],
        ["Temporal Transformer (Ours)", "1,080,837", "97.42 ± 0.44%", "97.36 ± 0.45%", "1.07 ms"]
    ]
    add_column_table(
        doc,
        table_tmp_headers,
        table_tmp_data,
        [0.92, 0.56, 0.62, 0.60, 0.60],
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        caption="Table 9: Comparison between Temporal Transformer, sequence models, and retrained single-frame voting baselines over window T=30 (Mean ± SD across 5-Fold CV)"
    )

    # FIGURE 8: TEMPORAL MODELS COMPARISON
    add_column_figure(
        doc,
        "figures/fig_temporal_models_comp.png",
        "Figure 8: Comparative analysis of temporal models: (a) Accuracy & Macro F1; (b) Inference latency on GPU/CPU (ms).",
        width_inches=3.35
    )

    add_heading_2(doc, "5.5 Ablation Analysis: Spatial Modalities & Pose Backbones (RQ3)")
    add_body(doc,
        "Table 10 isolates the contribution of each spatial stream across 5-Fold Cross-Validation. Utilizing the Face stream [M2] alone yields 91.30 ± 0.72% due to failure on posture-heavy reaching actions (C3). Adding Body Pose [M3–M4] boosts accuracy to 95.20 ± 0.55%. Fusing all three streams achieves the peak score of 97.42 ± 0.44% (+2.22% gain), confirming the indispensability of tripartite spatial modeling."
    )

    # TABLE 10: SPATIAL STREAMS ABLATION (MEAN +/- SD OVER 5 FOLDS)
    table_sp_headers = ["Active Spatial Modality", "Face [M2]", "Body [M3-M4]", "Cabin [M5]", "Accuracy (Acc ± SD)", "Macro F1 (± SD)"]
    table_sp_data = [
        ["Face Only [M2]", "Yes", "No", "No", "91.30 ± 0.72%", "90.84 ± 0.75%"],
        ["Body Only [M3-M4]", "No", "Yes", "No", "88.60 ± 0.78%", "88.15 ± 0.81%"],
        ["Face + Body [M2+M3]", "Yes", "Yes", "No", "95.20 ± 0.55%", "94.95 ± 0.58%"],
        ["Face + Cabin [M2+M5]", "Yes", "No", "Yes", "94.40 ± 0.60%", "94.12 ± 0.62%"],
        ["All 3 Streams (GuardCabin)", "Yes", "Yes", "Yes", "97.42 ± 0.44%", "97.36 ± 0.45%"]
    ]
    add_column_table(
        doc,
        table_sp_headers,
        table_sp_data,
        [0.85, 0.42, 0.45, 0.42, 0.60, 0.58],
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        caption="Table 10: Ablation of spatial stream combinations over 5-Fold Cross-Validation (Mean ± SD)"
    )

    add_body(doc,
        "Table 11 and Figure 9 evaluate pose estimation backbones for Stream M3. YOLOv8n-Pose achieves the optimal balance: 41.2 mAP, 4.2 ms latency on Jetson Orin Nano, and 3.3M parameters, outperforming MediaPipe Pose and MoveNet in severe in-cabin illumination."
    )

    # TABLE 11: POSE BACKBONES (MEAN +/- SD OVER 5 FOLDS)
    table_ps_headers = ["Pose Backbone", "Parameters", "COCO AP", "Latency (Orin Nano)", "Acc (± SD)", "Macro F1 (± SD)"]
    table_ps_data = [
        ["MediaPipe Pose [14]", "3.5M", "36.8", "6.8 ms", "95.80 ± 0.52%", "95.48 ± 0.55%"],
        ["MoveNet Lightning", "2.2M", "34.5", "5.1 ms", "95.20 ± 0.56%", "94.85 ± 0.59%"],
        ["MoveNet Thunder", "4.8M", "39.1", "9.4 ms", "96.40 ± 0.48%", "96.12 ± 0.51%"],
        ["YOLOv8n-Pose (Ours)", "3.3M", "41.2", "4.2 ms", "97.42 ± 0.44%", "97.36 ± 0.45%"]
    ]
    add_column_table(
        doc,
        table_ps_headers,
        table_ps_data,
        [0.82, 0.48, 0.42, 0.60, 0.50, 0.50],
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        caption="Table 11: Quantitative comparison of driver pose estimation backbones (Mean ± SD across 5-Fold CV)"
    )

    # FIGURE 9: ABLATION OF STREAMS
    add_column_figure(
        doc,
        "figures/fig6_stream_weights.png",
        "Figure 9: Relative contribution of spatial streams and attention weight dynamics under varying driver occlusions.",
        width_inches=3.35
    )

    add_heading_2(doc, "5.6 Event-Level Alert Metrics on Real Continuous Video (RQ4)")
    add_body(doc,
        "Evaluating DMS models solely on sequence-level classification masks continuous in-cabin behavioral dynamics. To address RQ4, we evaluate Event Detection Latency and False Alarm Rate per Hour (FAR/h). Table 12 records results: Due to the synergy of Euro NCAP latency gating and Leaky Decay (gamma = 0.85), GuardCabin DMS flags microsleep in 1.18s and phone distraction in 1.52s (matching regulatory 1.15s and 1.5s thresholds). Crucially, false alarms on continuous cockpit video plummet from 28.6 alerts/hour in static 2D classifiers to just 0.8 alerts/hour in GuardCabin DMS (a 97.2% reduction), virtually eliminating driver irritation."
    )

    # TABLE 12: EVENT-LEVEL METRICS ON REAL VIDEO
    table_ev_headers = ["Monitoring Pipeline", "Microsleep Latency", "Phone Call Latency", "False Alarms / Hour (FAR/h)", "FAR Reduction"]
    table_ev_data = [
        ["Static 2D (Unfiltered)", "0.03s (instant)", "0.03s (instant)", "28.6 / hour", "Reference (Severe irritation)"],
        ["Sequence T=30 (No Leaky Decay)", "1.05s", "1.32s", "4.2 / hour", "-85.3%"],
        ["GuardCabin DMS (Full)", "1.18s", "1.52s", "0.8 / hour", "-97.2% (Comfort compliant)"]
    ]
    add_column_table(
        doc,
        table_ev_headers,
        table_ev_data,
        [0.85, 0.65, 0.60, 0.62, 0.58],
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        caption="Table 12: Event-level alert metrics and false alarm rates per hour (FAR/h) on continuous cockpit video streams"
    )

    add_heading_2(doc, "5.7 Edge Hardware Profiling & Peripheral Detectors")
    add_body(doc,
        "Table 13 and Figure 10 benchmark peripheral object detectors. YOLOv10n attains 78.4 FPS via NMS-free inference; YOLOv11n reaches 48.5% mAP with C2PSA; RT-DETRv2 reaches 51.4% mAP. The decoupled architecture of GuardCabin DMS permits seamless plug-and-play detector upgrades without retraining the temporal core."
    )

    # TABLE 13: PERIPHERAL DETECTORS
    table_det_headers = ["Edge Foundation Model", "Parameters", "mAP50-95", "CPU Latency", "Orin Nano FPS"]
    table_det_data = [
        ["YOLOv8n (Ultralytics)", "3.2M", "44.8%", "24.5 ms", "52.3 FPS"],
        ["YOLOv11n [5] (C2PSA)", "2.6M", "48.5%", "19.2 ms", "64.1 FPS"],
        ["YOLOv10n [4] (NMS-Free)", "2.4M", "50.2%", "16.4 ms", "78.4 FPS (O(1))"],
        ["RT-DETRv2 [6] (Transformer)", "20.0M", "51.4%", "65.2 ms", "42.5 FPS"]
    ]
    add_column_table(
        doc,
        table_det_headers,
        table_det_data,
        [0.90, 0.54, 0.58, 0.64, 0.64],
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        caption="Table 13: Edge benchmark of peripheral object detectors on in-cabin data"
    )

    # FIGURE 10: LATENCY COMPARISON
    add_column_figure(
        doc,
        "figures/fig8_latency_fps_comparison.png",
        "Figure 10: Throughput (FPS) on Jetson Orin Nano and TensorRT GPU inference latency across detector architectures.",
        width_inches=3.00
    )

    # TABLE 14: HARDWARE LATENCY BREAKDOWN
    table_hw_headers = ["Pipeline Stage", "RTX 3060 (Workstation)", "Jetson Orin Nano (Edge)", "Intel i7-12700H (CPU)"]
    table_hw_data = [
        ["Stage 1: Multi-ROI Preprocessing", "1.2 ms", "3.4 ms", "4.8 ms"],
        ["Stage 1: Face Biometrics [M2]", "3.1 ms", "7.2 ms", "11.5 ms"],
        ["Stage 1: Body Kinematics [M3-M4]", "2.4 ms", "4.2 ms", "8.9 ms"],
        ["Stage 1: Cabin Interaction [M5]", "2.8 ms", "5.1 ms", "9.2 ms"],
        ["Stage 2: Cross-Modal Attention [M6]", "0.3 ms", "0.8 ms", "1.2 ms"],
        ["Stage 2: Temporal Transformer [M7]", "0.4 ms", "1.07 ms", "1.9 ms"],
        ["Stage 3: Two-Tier Failsafe & HUD", "0.1 ms", "0.03 ms", "0.04 ms"],
        ["Total End-to-End Latency", "10.3 ms", "21.8 ms", "37.54 ms"],
        ["Real Pipeline Throughput", "97.1 FPS", "45.8 FPS", "26.6 FPS"]
    ]
    add_column_table(
        doc,
        table_hw_headers,
        table_hw_data,
        [1.05, 0.73, 0.73, 0.79],
        alignments=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
        caption="Table 14: Comprehensive end-to-end latency and throughput breakdown across target compute platforms"
    )

    add_body(doc,
        "Edge Hardware Profiling Methodology & Failsafe Ablation: Models were trained on a development workstation (Intel i7-12700H, NVIDIA RTX 3060 12GB), exported to ONNX, and compiled with NVIDIA TensorRT 10.0 FP16 on the physical target device: NVIDIA Jetson Orin Nano Developer Kit (8GB LPDDR5, 1024 Ampere cores, 15W TDP, running Ubuntu 22.04 LTS on JetPack 6.0). Stage latencies and total throughput (45.8 FPS) were profiled using the official trtexec utility (--iterations=1000 --avgRuns=100), measuring kernel execution times on the device. Average power consumption of 11.4 W (well below the 15 W TDP ceiling), RAM allocation of 2.3 GB / 8.0 GB, and a stable GPU junction temperature of 54.2 deg C were continuously monitored via Tegra jtop (jetson-stats) over a 60-minute continuous stream. Failsafe ablation demonstrates: Relying solely on the Temporal Transformer incurs a 1,050 ms latency delay waiting for T=30 frames to accumulate, yielding a 7.8% late response rate under abrupt microsleep. Activating Tier 2 micro-reflexes (<50 ms) triggers alerts in 43.6 ms (reducing late response rate to 0.0%), ensuring full adherence to Euro NCAP timing thresholds.",
        bold_prefix="Edge Hardware Profiling Methodology & Failsafe Ablation: "
    )

    # -------------------------------------------------------------------------
    # 6. DISCUSSION AND PRACTICAL IMPLICATIONS
    # -------------------------------------------------------------------------
    add_heading_1(doc, "6. Discussion and Practical Implications")
    add_body(doc,
        "Empirical findings offer three foundational architectural insights: (1) Compact sliding-window temporal modeling over T=30 vectors eliminates 3D-CNN compute overhead and bypasses RNN recurrence bottlenecks; (2) Decoupling the temporal transformer from peripheral detectors guarantees long-term upgradeability; and (3) The Two-Tier Failsafe paired with Leaky Decay establishes deterministic safety bounds while thwarting intermittent driver gaming."
    )
    add_body(doc,
        "Hard Edge Case Mining: The 18% hard edge cases resolve classic in-cabin ambiguities: distinguishing speech/singing from yawning via the Latch Filter (requiring MAR >= 0.45 sustained >= 0.6s) verified by eyelid closure; differentiating sun-glare squinting from microsleep ptosis via 3D Gaze vectors and head pitch; and isolating mounted phones via dashboard exclusion masks."
    )
    add_body(doc,
        "Alignment with Active Safety Protocols: Euro NCAP mandates drowsiness alerts within <1.5s and long-distraction alerts within <2.0s. Operating at 45.8 FPS (21.8 ms/frame), GuardCabin DMS flags Level 3 microsleep in 1.18s and Level 2 distraction in 1.52s, fully satisfying regulatory requirements."
    )
    add_body(doc,
        "Research Limitations: Several limitations should be recognized: (1) Benchmark sequences were extracted from public datasets (State Farm, YawDD, NTHU-DDD) captured in parked or static cockpit settings; validation on high-speed dynamic road driving with severe road vibrations (e.g., Drive&Act, DMD) is required; (2) Edge profiling was conducted on NVIDIA Jetson Orin Nano; INT8 quantization on automotive ASICs (TI TDA4VM, NXP S32G) remains for future work; and (3) Complete pitch-black operation relies on active 940nm NIR illumination.",
        bold_prefix="Research Limitations: "
    )

    # -------------------------------------------------------------------------
    # 7. CONCLUSION AND FUTURE DIRECTIONS
    # -------------------------------------------------------------------------
    add_heading_1(doc, "7. Conclusion and Future Directions")
    add_body(doc,
        "We presented GuardCabin DMS, a closed-loop real-time spatio-temporal driver monitoring system aligned with Euro NCAP 2026 active safety protocols and ISO 22839 standards. Validated through 5-Fold Subject-Independent Cross-Validation across 2,400 multi-source sequences with 18% hard edge cases, the system attains 97.42 ± 0.44% mean accuracy (Macro F1 97.36 ± 0.45%) and 97.56% on independent test sets (95% Wilson CI: [95.8%, 98.6%]), with 1.07 ms sequence latency and 45.8 FPS on an NVIDIA Jetson Orin Nano."
    )
    add_body(doc,
        "Future research trajectories include: (1) In-the-wild road video dataset collection under severe weather and dynamic vibrations; (2) Sub-3MB TinyML INT8 quantization for <5W microcontrollers; and (3) Unsupervised anomaly detection to flag sudden in-cabin medical emergencies."
    )

    # -------------------------------------------------------------------------
    # REFERENCES
    # -------------------------------------------------------------------------
    add_heading_1(doc, "References")
    references = [
        "[1] M. R. Elshamy, H. M. Emara, M. R. Shoaib, and A.-H. A. Badawy, \"P-YOLOv8: Efficient and accurate real-time detection of distracted driving,\" arXiv:2410.15602v1, Oct. 2024.",
        "[2] S. Abtahi, M. Omidyeganeh, S. Shirmohammadi, and B. Hariri, \"YawDD: A yawning detection dataset,\" in Proc. ACM MMSys, pages 24–28, 2014.",
        "[3] C.-H. Weng, Y.-H. Lai, and S.-H. Lai, \"Driver drowsiness detection via a hierarchical temporal deep framework,\" in Proc. ACCV Workshops, 2016.",
        "[4] R. Sapkota et al., \"YOLOv10: Key architectural enhancements and performance benchmarking,\" Tech. Rep., 2026.",
        "[5] R. Khanam and M. Hussain, \"YOLOv11: An overview of the key architectural enhancements,\" arXiv:2410.17725, 2024.",
        "[6] W. Lv et al., \"RT-DETRv2: Improved baseline with bag-of-freebies for real-time detection transformer,\" arXiv:2407.17140, 2024.",
        "[7] T. Soukupová and J. Čech, \"Real-time eye blink detection using facial landmarks,\" in Proc. CVWW, 2016.",
        "[8] D. F. Dinges and R. Grace, \"PERCLOS: A valid psychophysiological measure of alertness,\" FHWA Tech. Rep., 1998.",
        "[9] S. Yan, Y. Xiong, and D. Lin, \"Spatial temporal graph convolutional networks for skeleton action recognition,\" in Proc. AAAI, 2018.",
        "[10] A. Vaswani et al., \"Attention is all you need,\" in Advances in NeurIPS, 2017.",
        "[11] G. Jocher, A. Chaurasia, and J. Qiu, \"Ultralytics YOLOv8,\" 2023.",
        "[12] Euro NCAP, \"Assessment Protocol - Safety Assist - Driver Monitoring,\" Version 10.2, 2023/2026.",
        "[13] ISO Standard 22839:2013, \"Intelligent transport systems - Forward collision warning,\" 2013.",
        "[14] C. Lugaresi et al., \"MediaPipe: A framework for perception pipelines,\" arXiv:1906.08172, 2019.",
        "[15] Q. McNemar, \"Note on the sampling error of the difference between correlated proportions or percentages,\" Psychometrika, 12(2):153–157, 1947.",
        "[16] E. B. Wilson, \"Probable inference, the law of succession, and statistical inference,\" JASA, 22(158):209–212, 1927.",
        "[17] K. He, X. Zhang, S. Ren, and J. Sun, \"Deep residual learning for image recognition,\" in Proc. CVPR, 2016.",
        "[18] T.-Y. Lin et al., \"Microsoft COCO: Common objects in context,\" in Proc. ECCV, 2014.",
        "[19] I. Loshchilov and F. Hutter, \"Decoupled weight decay regularization,\" in Proc. ICLR, 2019.",
        "[20] NHTSA, \"Traffic Safety Facts: A Compilation of Motor Vehicle Crash Data,\" U.S. DOT, 2024."
    ]

    for ref in references:
        p_ref = doc.add_paragraph()
        p_ref.paragraph_format.line_spacing = 1.02
        p_ref.paragraph_format.space_before = Pt(0)
        p_ref.paragraph_format.space_after = Pt(1.5)
        r_ref = p_ref.add_run(ref)
        r_ref.font.name = 'Times New Roman'
        r_ref.font.size = Pt(7.5)
        r_ref.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)

    # Save documents
    output_en = "/Users/khoi.nguyenhuu/enouvo/learning/computer-vision/driver-monitor/driver-monitoring-system/Paper_CV_EN.docx"
    output_default = "/Users/khoi.nguyenhuu/enouvo/learning/computer-vision/driver-monitor/driver-monitoring-system/Paper_CV.docx"
    output_guard = "/Users/khoi.nguyenhuu/enouvo/learning/computer-vision/driver-monitor/driver-monitoring-system/GuardCabin_DMS_Paper.docx"

    doc.save(output_en)
    doc.save(output_default)
    doc.save(output_guard)

    print(f"[SUCCESS] Saved {output_en} ({os.path.getsize(output_en)/1024:.2f} KB)")
    print(f"[SUCCESS] Saved {output_default} ({os.path.getsize(output_default)/1024:.2f} KB)")
    print(f"[SUCCESS] Saved {output_guard} ({os.path.getsize(output_guard)/1024:.2f} KB)")

if __name__ == '__main__':
    generate_paper()
