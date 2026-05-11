"""
Plotly-based network graph cho step-by-step visualization.

Khác với PyVis (HTML embed nặng, render lần đầu mới render lại),
module này dùng go.Scatter để vẽ graph nhẹ - mỗi step có thể re-render
nhanh và highlight node/edge theo state hiện tại.

Layout (vị trí node) được cache theo (algo, id-set, k) để các step không
nhảy múa vô tổ chức khi state đổi.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple, Any
import math

import plotly.graph_objects as go


# Bảng màu đồng bộ với GraphVisualizer.COLORS
COLORS = {
    'unvisited': '#B0B0B0',
    'current': '#FFC107',
    'visited': '#4CAF50',
    'path': '#F44336',
    'pair': '#FF7043',          # cặp đang xét (OLC)
    'next': '#FFD54F',           # node sắp tới (DBG euler)
    'edge_default': '#CCCCCC',
    'edge_path': '#F44336',
    'edge_current': '#FF9800',
    'edge_visited': '#66BB6A',
    'edge_dim': '#EEEEEE',
    'background': '#FAFAFA',
}


def _spring_layout(nodes: List[Any], edges: List[Tuple[Any, Any]],
                   seed: int = 42, iterations: int = 60) -> Dict[Any, Tuple[float, float]]:
    """
    Fruchterman-Reingold spring layout đơn giản, không phụ thuộc NetworkX
    (giữ requirements gọn). Đủ tốt cho ≤80 nodes.
    """
    import random
    rng = random.Random(seed)
    n = max(1, len(nodes))
    pos = {node: (rng.uniform(-1, 1), rng.uniform(-1, 1)) for node in nodes}
    if n == 1:
        return {nodes[0]: (0.0, 0.0)}

    area = 1.0
    k = math.sqrt(area / n)
    t = 0.1  # nhiệt độ ban đầu
    cooling = t / (iterations + 1)

    adj: Dict[Any, Set[Any]] = {node: set() for node in nodes}
    for a, b in edges:
        if a in adj and b in adj:
            adj[a].add(b)
            adj[b].add(a)

    for _ in range(iterations):
        disp: Dict[Any, List[float]] = {node: [0.0, 0.0] for node in nodes}

        # repulsive
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                dx = pos[a][0] - pos[b][0]
                dy = pos[a][1] - pos[b][1]
                dist = math.sqrt(dx * dx + dy * dy) + 1e-4
                force = (k * k) / dist
                ux, uy = dx / dist, dy / dist
                disp[a][0] += ux * force
                disp[a][1] += uy * force
                disp[b][0] -= ux * force
                disp[b][1] -= uy * force

        # attractive (iterate each unique unordered pair once)
        seen_pairs: Set[Tuple[Any, Any]] = set()
        for a in nodes:
            for b in adj[a]:
                key = (id(a), id(b)) if id(a) < id(b) else (id(b), id(a))
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                dx = pos[a][0] - pos[b][0]
                dy = pos[a][1] - pos[b][1]
                dist = math.sqrt(dx * dx + dy * dy) + 1e-4
                force = (dist * dist) / k
                ux, uy = dx / dist, dy / dist
                disp[a][0] -= ux * force
                disp[a][1] -= uy * force
                disp[b][0] += ux * force
                disp[b][1] += uy * force

        # apply
        for node in nodes:
            d = disp[node]
            mag = math.sqrt(d[0] ** 2 + d[1] ** 2) + 1e-4
            pos[node] = (
                pos[node][0] + (d[0] / mag) * min(mag, t),
                pos[node][1] + (d[1] / mag) * min(mag, t),
            )
        t = max(0.0, t - cooling)

    # normalize vào [-1, 1]
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    if xs and (max(xs) - min(xs)) > 0:
        mn, mx = min(xs), max(xs)
        for node in pos:
            pos[node] = ((pos[node][0] - mn) / (mx - mn) * 2 - 1, pos[node][1])
    if ys and (max(ys) - min(ys)) > 0:
        mn, mx = min(ys), max(ys)
        for node in pos:
            pos[node] = (pos[node][0], (pos[node][1] - mn) / (mx - mn) * 2 - 1)

    return pos


def _make_arrow_annotation(x0: float, y0: float, x1: float, y1: float,
                            color: str, width: int = 1) -> dict:
    return dict(
        ax=x0, ay=y0, x=x1, y=y1,
        xref='x', yref='y', axref='x', ayref='y',
        showarrow=True, arrowhead=3, arrowsize=1.2, arrowwidth=width,
        arrowcolor=color, opacity=0.95,
    )


def render_olc_graph(
    *,
    reads: List[str],
    overlaps: List[Tuple[int, int, int]],
    state: Optional[Dict[str, Any]] = None,
    height: int = 360,
    layout_seed: int = 42,
) -> go.Figure:
    """
    Render OLC overlap graph dưới dạng Plotly figure.

    state có thể chứa:
      - 'phase': 'overlap'|'layout'|'consensus'
      - 'current_pair': (i, j)
      - 'path': [int]
      - 'visited': set[int]
      - 'visible_overlaps': số overlap đã phát hiện đến step hiện tại
        (None = hiện tất cả).
      - 'backtrack': bool — vẽ mũi tên ngược nếu True
    """
    state = state or {}
    n = len(reads)
    nodes = list(range(n))

    edges_full = list(overlaps)
    if state.get('visible_overlaps') is not None:
        edges_full = edges_full[: state['visible_overlaps']]

    pos = _spring_layout(nodes, [(s, d) for s, d, _ in edges_full] or [(0, 0)],
                         seed=layout_seed)

    path = state.get('path') or []
    visited = state.get('visited') or set()
    current_pair = state.get('current_pair') or (None, None)
    phase = state.get('phase')
    backtrack = state.get('backtrack', False)

    path_edges = {(path[i], path[i + 1]) for i in range(len(path) - 1)} if path else set()

    # ----- edges -----
    annotations: List[dict] = []
    for src, dst, length in edges_full:
        if (src, dst) in path_edges:
            color = COLORS['edge_path']; width = 3
        elif phase == 'layout' and src == current_pair[0] and dst == current_pair[1]:
            color = COLORS['edge_current']; width = 3
        elif phase == 'overlap' and (src, dst) == current_pair:
            color = COLORS['edge_current']; width = 2.5
        else:
            color = COLORS['edge_default']; width = 1
        x0, y0 = pos[src]
        x1, y1 = pos[dst]
        annotations.append(_make_arrow_annotation(x0, y0, x1, y1, color, width))

    if backtrack and current_pair[0] is not None and current_pair[1] is not None:
        x0, y0 = pos.get(current_pair[0], (0, 0))
        x1, y1 = pos.get(current_pair[1], (0, 0))
        annotations.append(_make_arrow_annotation(x0, y0, x1, y1, '#9C27B0', 3))

    # ----- nodes -----
    node_colors = []
    node_line_colors = []
    node_line_widths = []
    node_text = []
    hovers = []
    for i in nodes:
        if i in (current_pair[0], current_pair[1]) and phase in ('overlap', 'layout', 'consensus'):
            node_colors.append(COLORS['pair'])
        elif path and i in path:
            node_colors.append(COLORS['path'])
        elif i in visited:
            node_colors.append(COLORS['visited'])
        else:
            node_colors.append(COLORS['unvisited'])
        is_current_head = path and i == path[-1] if phase == 'layout' else False
        node_line_colors.append('#FFEB3B' if is_current_head else '#37474F')
        node_line_widths.append(4 if is_current_head else 1)
        node_text.append(f"R{i}")
        hovers.append(f"<b>R{i}</b><br>{reads[i][:30]}{'...' if len(reads[i]) > 30 else ''}")

    xs = [pos[i][0] for i in nodes]
    ys = [pos[i][1] for i in nodes]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode='markers+text',
        marker=dict(size=28, color=node_colors,
                    line=dict(color=node_line_colors, width=node_line_widths)),
        text=node_text, textposition='middle center',
        textfont=dict(color='white', size=11, family='monospace'),
        hovertext=hovers, hoverinfo='text', showlegend=False,
    ))

    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['background'],
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-1.2, 1.2]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-1.2, 1.2],
                   scaleanchor='x', scaleratio=1),
        annotations=annotations,
        showlegend=False,
    )
    return fig


def render_dbg_graph(
    *,
    graph: Dict[str, List[str]],
    state: Optional[Dict[str, Any]] = None,
    height: int = 360,
    layout_seed: int = 42,
    max_nodes: int = 80,
) -> go.Figure:
    """
    Render DBG (de Bruijn) graph dưới dạng Plotly figure.

    state có thể chứa:
      - 'phase': 'kmer'|'graph'|'euler'|'reconstruct'
      - 'current_node': str
      - 'next_node': str  (cạnh hiện đang đi)
      - 'visited_edges': List[(src, dst)]
      - 'path': List[str]  (path Eulerian đã hoàn thành đến nay)
    """
    state = state or {}

    all_nodes: List[str] = sorted({n for n in graph.keys()} |
                                   {d for ts in graph.values() for d in ts})
    if len(all_nodes) > max_nodes:
        # giữ deterministic - sort + cắt
        all_nodes = all_nodes[:max_nodes]
    node_set = set(all_nodes)
    edges = [(s, d) for s, ts in graph.items() if s in node_set for d in ts if d in node_set]

    pos = _spring_layout(all_nodes, edges, seed=layout_seed)

    current = state.get('current_node')
    nxt = state.get('next_node')
    visited_edges = set(tuple(e) for e in (state.get('visited_edges') or []))
    path = state.get('path') or []
    path_nodes = set(path)
    phase = state.get('phase')

    annotations = []
    for s, d in edges:
        if (s, d) == (current, nxt):
            color = COLORS['edge_current']; width = 3
        elif (s, d) in visited_edges:
            color = COLORS['edge_visited']; width = 2
        elif phase == 'euler' and visited_edges:
            color = COLORS['edge_dim']; width = 1
        else:
            color = COLORS['edge_default']; width = 1
        x0, y0 = pos[s]
        x1, y1 = pos[d]
        annotations.append(_make_arrow_annotation(x0, y0, x1, y1, color, width))

    node_colors = []
    node_line_widths = []
    hovers = []
    for node in all_nodes:
        if node == current:
            node_colors.append(COLORS['current'])
            node_line_widths.append(3)
        elif node == nxt:
            node_colors.append(COLORS['next'])
            node_line_widths.append(2)
        elif node in path_nodes:
            node_colors.append(COLORS['path'])
            node_line_widths.append(1)
        else:
            node_colors.append(COLORS['unvisited'])
            node_line_widths.append(1)
        hovers.append(f"<b>{node}</b>")

    xs = [pos[n][0] for n in all_nodes]
    ys = [pos[n][1] for n in all_nodes]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode='markers+text',
        marker=dict(size=24, color=node_colors,
                    line=dict(color='#37474F', width=node_line_widths)),
        text=all_nodes, textposition='middle center',
        textfont=dict(color='#212121', size=9, family='monospace'),
        hovertext=hovers, hoverinfo='text', showlegend=False,
    ))

    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['background'],
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-1.2, 1.2]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-1.2, 1.2],
                   scaleanchor='x', scaleratio=1),
        annotations=annotations,
        showlegend=False,
    )
    return fig


def legend_html() -> str:
    """HTML legend cho stepwise graph."""
    items = [
        ('Chưa thăm', COLORS['unvisited']),
        ('Đang xét', COLORS['current']),
        ('Sắp tới', COLORS['next']),
        ('Đã thăm', COLORS['visited']),
        ('Trên path', COLORS['path']),
    ]
    spans = ''.join(
        f'<span style="display:inline-flex;align-items:center;gap:4px;margin-right:12px;">'
        f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{c};"></span>'
        f'<span style="font-size:11px;color:#555;">{label}</span></span>'
        for label, c in items
    )
    return f'<div style="padding:6px 8px;background:#FAFAFA;border-radius:4px;">{spans}</div>'
