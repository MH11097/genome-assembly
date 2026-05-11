"""
Coverage Map (View 5): hiển thị reads xếp tại vị trí gốc trên genome
+ depth-of-coverage line phía trên.
"""

from __future__ import annotations

from typing import List, Optional

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def render_coverage_map(genome_length: int,
                         read_positions: List[tuple],  # list of (start, end, index)
                         *, height: int = 280,
                         min_depth_alert: int = 1) -> go.Figure:
    """
    Hiển thị:
      - Hàng trên: depth-of-coverage line plot (xanh dương)
      - Hàng dưới: reads dưới dạng segment ngang xếp packed (kiểu IGV)
      - Vùng coverage = 0 (gap) được tô đỏ nhạt
    """
    if genome_length <= 0:
        fig = go.Figure()
        fig.add_annotation(text="Genome rỗng", showarrow=False)
        return fig

    # depth array
    depth = [0] * genome_length
    for start, end, _idx in read_positions:
        for p in range(max(0, start), min(genome_length, end)):
            depth[p] += 1

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.35, 0.65], vertical_spacing=0.04,
        subplot_titles=("Depth-of-coverage", f"Reads ({len(read_positions)} reads)"),
    )

    # ===== Row 1: depth =====
    xs = list(range(genome_length))
    fig.add_trace(
        go.Scatter(x=xs, y=depth, mode='lines', line=dict(color='#1976D2', width=2),
                   fill='tozeroy', fillcolor='rgba(25,118,210,0.15)',
                   hovertemplate='pos %{x}<br>depth %{y}<extra></extra>',
                   showlegend=False),
        row=1, col=1,
    )

    # gap shading (depth < min_depth_alert)
    in_gap = False
    gap_start = 0
    shapes = []
    for i, d in enumerate(depth):
        if d < min_depth_alert and not in_gap:
            in_gap = True
            gap_start = i
        elif d >= min_depth_alert and in_gap:
            in_gap = False
            shapes.append(dict(
                type='rect', xref='x', yref='paper',
                x0=gap_start, x1=i, y0=0, y1=1,
                fillcolor='rgba(244,67,54,0.10)', line=dict(width=0), layer='below',
            ))
    if in_gap:
        shapes.append(dict(
            type='rect', xref='x', yref='paper',
            x0=gap_start, x1=genome_length, y0=0, y1=1,
            fillcolor='rgba(244,67,54,0.10)', line=dict(width=0), layer='below',
        ))

    # ===== Row 2: packed reads =====
    # greedy interval packing: assign each read to lowest row where it doesn't overlap
    sorted_reads = sorted(read_positions, key=lambda r: r[0])
    row_ends: List[int] = []  # end position of last read in each row
    assignments: List[int] = []
    for (s, e, _idx) in sorted_reads:
        placed = False
        for r, last_end in enumerate(row_ends):
            if s >= last_end:
                row_ends[r] = e
                assignments.append(r)
                placed = True
                break
        if not placed:
            row_ends.append(e)
            assignments.append(len(row_ends) - 1)

    # cap rows visible at 25 to keep figure compact; remaining rendered as faded
    max_rows = max(1, len(row_ends))
    for (s, e, idx), r in zip(sorted_reads, assignments):
        y = -r  # so row 0 at top
        visible_alpha = 0.85 if r < 25 else 0.25
        fig.add_trace(go.Scatter(
            x=[s, e], y=[y, y], mode='lines',
            line=dict(color=f'rgba(38,166,154,{visible_alpha})', width=6),
            hovertemplate=f'R{idx}<br>[%{{x}}]<extra></extra>',
            showlegend=False,
        ), row=2, col=1)

    fig.update_layout(
        height=height,
        margin=dict(l=40, r=10, t=30, b=30),
        plot_bgcolor='#FFFFFF', paper_bgcolor='#FAFAFA',
        shapes=shapes,
        font=dict(size=10),
    )
    fig.update_xaxes(showgrid=False, title=dict(text='vị trí trên genome (bp)', font=dict(size=10)),
                     row=2, col=1)
    fig.update_yaxes(title=dict(text='depth', font=dict(size=9)),
                     gridcolor='#EEEEEE', row=1, col=1)
    fig.update_yaxes(showticklabels=False, showgrid=False,
                     range=[-(max_rows + 0.5), 0.5], row=2, col=1)

    # summary annotation
    if depth:
        mean_depth = sum(depth) / len(depth)
        gap_bp = sum(1 for d in depth if d < min_depth_alert)
        fig.add_annotation(
            text=f"<b>{mean_depth:.1f}×</b> mean · <b>{gap_bp}</b> bp gap",
            xref='paper', yref='paper', x=1, y=1.04,
            xanchor='right', showarrow=False,
            font=dict(size=11, color='#555'),
        )

    return fig
