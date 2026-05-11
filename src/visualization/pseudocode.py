"""
Pseudocode panel cho OLC và DBG — render code với dòng hiện tại được highlight.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any


OLC_PSEUDOCODE: List[str] = [
    "# OLC: Overlap-Layout-Consensus",
    "",
    "# === Phase 1: Overlap ===",
    "for i in range(n):",
    "    for j in range(n):",
    "        ov = suffix_prefix(reads[i], reads[j])",
    "        if ov >= min_overlap:",
    "            overlaps.append((i, j, ov))",
    "",
    "# === Phase 2: Layout (Hamilton heuristic) ===",
    "start = pick_source(overlaps)",
    "path, visited = [start], {start}",
    "while len(visited) < n:",
    "    nbrs = sorted(graph[path[-1]], by=overlap, desc)",
    "    if any unvisited:",
    "        path.append(best_unvisited)",
    "    else:           # dead-end",
    "        backtrack(path, visited)",
    "",
    "# === Phase 3: Consensus ===",
    "consensus = reads[path[0]]",
    "for prev, cur in pairs(path):",
    "    ov = overlap_map[(prev, cur)]",
    "    consensus += reads[cur][ov:]",
    "return consensus",
]


DBG_PSEUDOCODE: List[str] = [
    "# DBG: De Bruijn Graph",
    "",
    "# === Phase 1: K-mers ===",
    "for read in reads:",
    "    for i in range(len(read) - k + 1):",
    "        kmers[read[i:i+k]] += 1",
    "",
    "# === Phase 2: Build graph ===",
    "for kmer in kmers:",
    "    u, v = kmer[:-1], kmer[1:]",
    "    graph[u].append(v)",
    "",
    "# === Phase 3: Euler path (Hierholzer) ===",
    "stack, path = [start], []",
    "while stack:",
    "    cur = stack[-1]",
    "    if graph[cur]:",
    "        stack.append(graph[cur].pop())",
    "    else:",
    "        path.append(stack.pop())",
    "path.reverse()",
    "",
    "# === Phase 4: Reconstruct ===",
    "genome = path[0]",
    "for node in path[1:]:",
    "    genome += node[-1]",
    "return genome",
]


# Phase -> list of 0-indexed lines to highlight
OLC_LINE_MAP: Dict[str, List[int]] = {
    'overlap': [2, 3, 4, 5, 6, 7],
    'layout': [9, 10, 11, 12, 13, 14, 15, 16, 17],
    'consensus': [19, 20, 21, 22, 23, 24],
}

DBG_LINE_MAP: Dict[str, List[int]] = {
    'kmer': [2, 3, 4, 5],
    'graph': [7, 8, 9, 10],
    'euler': [12, 13, 14, 15, 16, 17, 18, 19, 20],
    'reconstruct': [22, 23, 24, 25, 26],
}


# Mapping chi tiết hơn: dựa vào (phase, sub-event) trả về 1 dòng "primary"
def _olc_active_line(phase: str, message: str, backtrack: bool) -> Optional[int]:
    if phase == 'overlap':
        return 7 if 'overlap' in message.lower() else 5
    if phase == 'layout':
        if backtrack:
            return 17
        return 15
    if phase == 'consensus':
        return 23
    return None


def _dbg_active_line(phase: str, message: str) -> Optional[int]:
    if phase == 'kmer':
        return 4
    if phase == 'graph':
        return 8
    if phase == 'euler':
        if 'đẩy vào path' in message.lower() or 'pop' in message.lower():
            return 17
        return 15
    if phase == 'reconstruct':
        return 25
    return None


def render_code_trace(algo: str, *, phase: str, message: str = "",
                       backtrack: bool = False) -> str:
    """
    Trả về HTML hiển thị pseudocode với:
      - Highlight nền vàng nhạt cho cả khối thuộc phase hiện tại
      - Mũi tên ► + nền vàng đậm cho dòng "primary" tương ứng với step
    """
    code = OLC_PSEUDOCODE if algo == 'OLC' else DBG_PSEUDOCODE
    block = (OLC_LINE_MAP if algo == 'OLC' else DBG_LINE_MAP).get(phase, [])
    active = (_olc_active_line(phase, message, backtrack)
              if algo == 'OLC' else _dbg_active_line(phase, message))

    rows = []
    for i, line in enumerate(code):
        is_active = (i == active)
        is_block = i in block
        if is_active:
            bg = '#FFE082'; weight = 700; marker = '▶'
        elif is_block:
            bg = '#FFF8E1'; weight = 500; marker = ' '
        else:
            bg = 'transparent'; weight = 400; marker = ' '

        # comment color
        is_comment = line.strip().startswith('#')
        fg = '#37474F'
        if is_comment:
            fg = '#558B2F' if not is_block else '#33691E'

        rows.append(
            f'<div style="display:flex;background:{bg};padding:1px 4px;">'
            f'<span style="width:14px;color:#E65100;font-weight:700;">{marker}</span>'
            f'<span style="width:24px;color:#BBB;text-align:right;margin-right:8px;">{i + 1}</span>'
            f'<span style="color:{fg};font-weight:{weight};white-space:pre;">{line or "&nbsp;"}</span>'
            f'</div>'
        )

    return (
        '<div style="font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;'
        'line-height:18px;background:#FAFAFA;border:1px solid #E0E0E0;border-radius:4px;'
        'padding:6px;max-height:420px;overflow-y:auto;">'
        + ''.join(rows) +
        '</div>'
    )


def render_var_inspector(vars_dict: Dict[str, Any]) -> str:
    """Bảng key=value cho variable inspector."""
    if not vars_dict:
        return '<div style="padding:6px;color:#888;font-size:11px;">(no variables)</div>'
    rows = []
    for k, v in vars_dict.items():
        s = str(v)
        if len(s) > 60:
            s = s[:57] + '…'
        rows.append(
            f'<div style="display:flex;border-bottom:1px solid #F0F0F0;padding:2px 4px;">'
            f'<span style="width:120px;color:#0277BD;font-family:ui-monospace,Menlo,monospace;font-size:11px;">{k}</span>'
            f'<span style="flex:1;color:#37474F;font-family:ui-monospace,Menlo,monospace;font-size:11px;">{s}</span>'
            f'</div>'
        )
    return (
        '<div style="background:#FAFAFA;border:1px solid #E0E0E0;border-radius:4px;'
        'margin-top:6px;font-size:11px;">'
        '<div style="padding:4px 6px;background:#ECEFF1;color:#555;font-weight:600;'
        'font-size:11px;">Variables</div>'
        + ''.join(rows) +
        '</div>'
    )
