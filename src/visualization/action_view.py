"""
Action View — render *cơ chế* của từng phase thuật toán dưới dạng HTML.

Mỗi hàm trả về HTML string để embed bằng st.markdown(..., unsafe_allow_html=True).
Lý do dùng HTML thay vì Plotly: các action ở đây là sequence text với highlight
ký tự — HTML inline span là cách hiển thị tự nhiên nhất, không cần plot axes.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


# Bảng màu base DNA — đồng bộ SequenceVisualizer.BASE_COLORS
BASE_COLORS = {
    'A': '#e63946',  # red
    'T': '#f4a261',  # orange
    'G': '#2a9d8f',  # teal
    'C': '#264653',  # dark slate
    '-': '#BDBDBD',
    'N': '#9E9E9E',
}

_FONT_MONO = "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"


def _char_span(ch: str, *, bg: Optional[str] = None, fg: Optional[str] = None,
               border: Optional[str] = None, bold: bool = False, dim: bool = False) -> str:
    """Render 1 ký tự thành <span> với style."""
    styles = [
        "display:inline-block",
        "width:14px",
        "text-align:center",
        "font-family:" + _FONT_MONO,
        "font-size:13px",
        "line-height:18px",
    ]
    if bg:
        styles.append(f"background:{bg}")
    if fg:
        styles.append(f"color:{fg}")
    if border:
        styles.append(f"border:1px solid {border}")
    if bold:
        styles.append("font-weight:700")
    if dim:
        styles.append("opacity:0.35")
    return f'<span style="{";".join(styles)}">{ch}</span>'


def _seq_html(seq: str, *, highlight_range: Optional[Tuple[int, int]] = None,
              dim_outside: bool = False) -> str:
    """Render một sequence DNA thành chuỗi span màu base."""
    out = []
    for i, ch in enumerate(seq):
        bg = BASE_COLORS.get(ch.upper(), '#EEEEEE')
        in_range = highlight_range and highlight_range[0] <= i < highlight_range[1]
        dim = dim_outside and not in_range
        out.append(_char_span(ch, bg=bg, fg='white', bold=bool(in_range), dim=dim))
    return f'<div style="white-space:nowrap;overflow-x:auto;">{"".join(out)}</div>'


# --------------------------------------------------------------------------
# OLC — Overlap alignment (phase 'overlap')
# --------------------------------------------------------------------------

def render_overlap_alignment(read_a: str, read_b: str, overlap_len: int,
                              *, label_a: str = "A", label_b: str = "B") -> str:
    """
    Hiển thị 2 read xếp dọc với offset = len(A) - overlap_len.
    Cột overlap: tô viền vàng, mismatch tô đỏ (dùng cho cả trường hợp
    overlap_len = 0 -> chỉ hiện 2 read).
    """
    if overlap_len < 0:
        overlap_len = 0
    offset = max(0, len(read_a) - overlap_len)

    width = max(len(read_a), offset + len(read_b))
    row_a_chars = []
    row_b_chars = []
    row_match = []

    for i in range(width):
        ch_a = read_a[i] if i < len(read_a) else ' '
        b_idx = i - offset
        ch_b = read_b[b_idx] if 0 <= b_idx < len(read_b) else ' '

        in_overlap = (i >= offset) and (b_idx < overlap_len)
        if in_overlap and ch_a != ' ' and ch_b != ' ':
            match = ch_a.upper() == ch_b.upper()
            mark_bg = '#C8E6C9' if match else '#FFCDD2'
            row_a_chars.append(_char_span(ch_a, bg=BASE_COLORS.get(ch_a.upper(), '#EEE'),
                                          fg='white', border='#FFC107', bold=True))
            row_b_chars.append(_char_span(ch_b, bg=BASE_COLORS.get(ch_b.upper(), '#EEE'),
                                          fg='white', border='#FFC107', bold=True))
            row_match.append(_char_span('|' if match else '×', bg=mark_bg, fg='#37474F'))
        else:
            if ch_a == ' ':
                row_a_chars.append(_char_span(' '))
            else:
                row_a_chars.append(_char_span(ch_a, bg=BASE_COLORS.get(ch_a.upper(), '#EEE'),
                                              fg='white'))
            if ch_b == ' ':
                row_b_chars.append(_char_span(' '))
            else:
                row_b_chars.append(_char_span(ch_b, bg=BASE_COLORS.get(ch_b.upper(), '#EEE'),
                                              fg='white'))
            row_match.append(_char_span(' '))

    return f"""
    <div style="font-family:{_FONT_MONO};padding:8px;background:#FAFAFA;border-radius:6px;">
      <div style="display:flex;align-items:center;gap:8px;">
        <span style="width:30px;color:#666;font-weight:600;">{label_a}</span>
        <div>{"".join(row_a_chars)}</div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        <span style="width:30px;color:#888;"></span>
        <div>{"".join(row_match)}</div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        <span style="width:30px;color:#666;font-weight:600;">{label_b}</span>
        <div>{"".join(row_b_chars)}</div>
      </div>
      <div style="margin-top:6px;font-size:12px;color:#555;">
        Overlap = <b>{overlap_len}</b> bp · offset = {offset}
      </div>
    </div>
    """


# --------------------------------------------------------------------------
# OLC — Consensus stack (phase 'consensus')
# --------------------------------------------------------------------------

def render_consensus_stack(reads: List[str], path: List[int], overlaps_map: Dict[Tuple[int, int], int],
                            *, current_step: int, consensus: str) -> str:
    """
    Hiện reads xếp ở offset của chúng theo Hamiltonian path; read vừa được
    ghép (index = current_step trong path) được highlight viền vàng.
    Bên dưới là consensus đang xây.
    """
    if not path:
        return '<div style="padding:8px;color:#666;">Chưa có path.</div>'

    offsets: List[int] = [0]
    for i in range(1, len(path)):
        prev = path[i - 1]
        cur = path[i]
        ov = overlaps_map.get((prev, cur), 0)
        offsets.append(offsets[-1] + len(reads[prev]) - ov)

    total_width = max(offsets[-1] + len(reads[path[-1]]), len(consensus))

    rows = []
    for idx, (read_idx, off) in enumerate(zip(path, offsets)):
        spacer = '&nbsp;' * off * 2  # approx — width của 1 char span = 14px, dùng nbsp chỉ cho dòng đầu mô tả
        highlight = idx == current_step
        border = '2px solid #FFC107' if highlight else '1px solid transparent'
        row_html = _seq_html(reads[read_idx])
        rows.append(
            f'<div style="display:flex;align-items:center;gap:8px;margin:1px 0;">'
            f'<span style="width:34px;color:#666;font-weight:{"700" if highlight else "400"};">R{read_idx}</span>'
            f'<div style="margin-left:{off * 14}px;border:{border};border-radius:3px;padding:1px;">'
            f'{row_html}</div></div>'
        )

    consensus_html = _seq_html(consensus)
    return f"""
    <div style="font-family:{_FONT_MONO};padding:8px;background:#FAFAFA;border-radius:6px;overflow-x:auto;">
      <div style="font-size:11px;color:#888;margin-bottom:4px;">Stacked reads theo path:</div>
      {"".join(rows)}
      <div style="margin-top:8px;border-top:1px dashed #BBB;padding-top:6px;">
        <div style="display:flex;align-items:center;gap:8px;">
          <span style="width:34px;color:#0277BD;font-weight:700;">Σ</span>
          <div>{consensus_html}</div>
        </div>
        <div style="font-size:11px;color:#555;margin-top:4px;">Consensus: <b>{len(consensus)}</b> bp</div>
      </div>
    </div>
    """


# --------------------------------------------------------------------------
# DBG — Sliding window (phase 'kmer')
# --------------------------------------------------------------------------

def render_sliding_window(read: str, k: int, window_pos: int, *,
                          read_index: int = -1, kmer_tray: Optional[List[str]] = None) -> str:
    """
    Read được hiển thị; window k ký tự bắt đầu từ window_pos được highlight.
    kmer_tray: 5-10 k-mer đã gom gần nhất, hiển thị bên cạnh như "rổ".
    """
    if window_pos < 0:
        window_pos = 0
    seq_html = _seq_html(read, highlight_range=(window_pos, window_pos + k), dim_outside=True)

    tray = kmer_tray or []
    tray_html = ''.join(
        f'<span style="display:inline-block;margin:2px;padding:2px 6px;background:#FFF8E1;'
        f'border:1px solid #FFC107;border-radius:3px;font-family:{_FONT_MONO};font-size:11px;">'
        f'{km}</span>'
        for km in tray[-8:]
    )

    label = f"R{read_index}" if read_index >= 0 else "Read"
    return f"""
    <div style="font-family:{_FONT_MONO};padding:8px;background:#FAFAFA;border-radius:6px;">
      <div style="display:flex;align-items:center;gap:8px;">
        <span style="width:34px;color:#666;font-weight:600;">{label}</span>
        <div>{seq_html}</div>
      </div>
      <div style="margin-top:6px;font-size:11px;color:#555;">
        Cửa sổ k={k} tại vị trí [{window_pos}:{window_pos + k}] → k-mer
        <b style="color:#E65100;">{read[window_pos:window_pos + k] if window_pos + k <= len(read) else "?"}</b>
      </div>
      <div style="margin-top:6px;font-size:11px;color:#888;">Rổ k-mer gần nhất:</div>
      <div>{tray_html or '<span style="color:#BBB;">(trống)</span>'}</div>
    </div>
    """


# --------------------------------------------------------------------------
# DBG — Hierholzer stack (phase 'euler')
# --------------------------------------------------------------------------

def render_hierholzer_stack(stack: List[str], current: str, next_node: str,
                             edges_remaining: int, edges_total: int) -> str:
    """Vẽ stack LIFO dạng cột."""
    items = []
    for i, node in enumerate(reversed(stack)):
        is_top = (i == 0)
        bg = '#FFC107' if is_top else '#ECEFF1'
        color = '#212121' if is_top else '#37474F'
        items.append(
            f'<div style="background:{bg};color:{color};padding:4px 10px;margin:2px 0;'
            f'border-radius:3px;font-family:{_FONT_MONO};font-size:12px;'
            f'border-left:3px solid {"#E65100" if is_top else "#90A4AE"};">'
            f'{"▶ " if is_top else "  "}{node}</div>'
        )
    progress_pct = 0
    if edges_total > 0:
        progress_pct = int((edges_total - edges_remaining) / edges_total * 100)

    return f"""
    <div style="font-family:{_FONT_MONO};padding:8px;background:#FAFAFA;border-radius:6px;">
      <div style="display:flex;gap:12px;">
        <div style="flex:0 0 160px;">
          <div style="font-size:11px;color:#888;margin-bottom:4px;">Stack (LIFO):</div>
          {"".join(items) or '<i style="color:#BBB;">trống</i>'}
        </div>
        <div style="flex:1;">
          <div style="font-size:11px;color:#888;">Cạnh đang đi:</div>
          <div style="font-size:13px;color:#E65100;font-weight:700;margin:4px 0;">
            {current or '?'} <span style="color:#888;">→</span> {next_node or '?'}
          </div>
          <div style="font-size:11px;color:#888;margin-top:8px;">Tiến độ Euler:</div>
          <div style="height:8px;background:#ECEFF1;border-radius:4px;overflow:hidden;margin-top:4px;">
            <div style="width:{progress_pct}%;height:100%;background:linear-gradient(90deg,#66BB6A,#43A047);"></div>
          </div>
          <div style="font-size:11px;color:#555;margin-top:4px;">
            {edges_total - edges_remaining}/{edges_total} cạnh ({progress_pct}%)
          </div>
        </div>
      </div>
    </div>
    """


# --------------------------------------------------------------------------
# DBG — Reconstruct (phase 'reconstruct')
# --------------------------------------------------------------------------

def render_reconstruct_progress(genome_so_far: str, current_node: str, k: int) -> str:
    """
    Hiện genome đang xây; ký tự cuối được flash (vừa append từ current_node[-1]).
    """
    if not genome_so_far:
        return '<div style="padding:8px;color:#666;">Chưa khởi tạo.</div>'

    body = genome_so_far[:-1]
    last = genome_so_far[-1]
    body_html = _seq_html(body)
    last_html = _char_span(last, bg=BASE_COLORS.get(last.upper(), '#EEE'),
                            fg='white', border='#E65100', bold=True)

    return f"""
    <div style="font-family:{_FONT_MONO};padding:8px;background:#FAFAFA;border-radius:6px;">
      <div style="font-size:11px;color:#888;margin-bottom:4px;">
        Node hiện tại: <b style="color:#E65100;">{current_node}</b> → append ký tự cuối <b>'{last}'</b>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        <span style="width:34px;color:#0277BD;font-weight:700;">Σ</span>
        <div style="display:flex;align-items:center;">{body_html}{last_html}</div>
      </div>
      <div style="font-size:11px;color:#555;margin-top:4px;">Genome: <b>{len(genome_so_far)}</b> bp</div>
    </div>
    """


# --------------------------------------------------------------------------
# OLC — Layout breadcrumb (phase 'layout')
# --------------------------------------------------------------------------

def render_layout_breadcrumb(path: List[int], visited: set, total_reads: int,
                              *, backtrack: bool = False, current_pair: Optional[Tuple[int, int]] = None) -> str:
    """Hiển thị path đã đi dạng breadcrumb R0 → R3 → R7 ..."""
    if not path:
        return '<div style="padding:8px;color:#666;">Chưa có path.</div>'

    crumbs = []
    for i, r in enumerate(path):
        is_head = (i == len(path) - 1)
        bg = '#F44336' if is_head else '#FFCDD2'
        crumbs.append(
            f'<span style="display:inline-block;padding:3px 8px;background:{bg};color:white;'
            f'border-radius:3px;font-family:{_FONT_MONO};font-size:12px;font-weight:{"700" if is_head else "500"};">'
            f'R{r}</span>'
        )
        if i < len(path) - 1:
            crumbs.append('<span style="color:#888;margin:0 4px;">→</span>')

    note = ''
    if backtrack and current_pair:
        note = (
            f'<div style="margin-top:8px;padding:6px;background:#FCE4EC;border-left:3px solid #9C27B0;'
            f'font-size:12px;color:#6A1B9A;">Backtrack: rời R{current_pair[0]} → quay lại R{current_pair[1]}</div>'
        )

    coverage = len(visited)
    return f"""
    <div style="font-family:{_FONT_MONO};padding:8px;background:#FAFAFA;border-radius:6px;">
      <div style="font-size:11px;color:#888;margin-bottom:6px;">Path đã đi (greedy + backtrack):</div>
      <div style="line-height:28px;">{"".join(crumbs)}</div>
      {note}
      <div style="font-size:11px;color:#555;margin-top:8px;">
        Đã thăm: <b>{coverage}/{total_reads}</b> reads
      </div>
    </div>
    """
