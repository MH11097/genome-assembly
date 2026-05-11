"""
Distribution Panel (View 4):
- OLC: heatmap n×n overlap matrix (cumulative)
- DBG: histogram k-mer multiplicity (cumulative)
"""

from __future__ import annotations

from typing import Dict, List, Optional
from collections import Counter

import plotly.graph_objects as go


def render_overlap_heatmap(matrix: List[List[int]], *,
                            current_pair: Optional[tuple] = None,
                            height: int = 320) -> go.Figure:
    """
    Heatmap n×n cho overlap matrix. Ô hiện tại được khoanh.
    matrix[i][j] = overlap length từ i đến j.
    """
    n = len(matrix)
    labels = [f"R{i}" for i in range(n)]

    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=labels, y=labels,
        colorscale=[
            [0.0, '#FFFFFF'],
            [0.01, '#E3F2FD'],
            [0.5, '#42A5F5'],
            [1.0, '#0D47A1'],
        ],
        showscale=True,
        colorbar=dict(thickness=8, len=0.7, title=dict(text='bp', font=dict(size=10))),
        hovertemplate='R%{y}→R%{x}<br>overlap = %{z} bp<extra></extra>',
        zmin=0,
    ))

    shapes = []
    if current_pair and current_pair[0] is not None and current_pair[1] is not None:
        i, j = current_pair
        if 0 <= i < n and 0 <= j < n:
            shapes.append(dict(
                type='rect', xref='x', yref='y',
                x0=j - 0.5, x1=j + 0.5, y0=i - 0.5, y1=i + 0.5,
                line=dict(color='#FF6F00', width=3),
            ))

    fig.update_layout(
        height=height,
        margin=dict(l=40, r=10, t=10, b=30),
        xaxis=dict(side='top', tickfont=dict(size=10), title=dict(text='đến (suffix→prefix)', font=dict(size=10))),
        yaxis=dict(autorange='reversed', tickfont=dict(size=10), title=dict(text='từ', font=dict(size=10))),
        plot_bgcolor='#FAFAFA', paper_bgcolor='#FAFAFA',
        shapes=shapes,
    )
    return fig


def render_kmer_histogram(kmers_dict: Dict[str, int], *,
                           current_kmer: Optional[str] = None,
                           height: int = 320,
                           top_n: int = 25) -> go.Figure:
    """
    Top-N k-mer theo multiplicity. K-mer hiện tại tô vàng nếu xuất hiện trong top.
    """
    if not kmers_dict:
        fig = go.Figure()
        fig.add_annotation(text="(chưa có k-mer)", showarrow=False,
                            font=dict(size=12, color='#888'),
                            x=0.5, y=0.5, xref='paper', yref='paper')
        fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10),
                          xaxis=dict(visible=False), yaxis=dict(visible=False),
                          plot_bgcolor='#FAFAFA', paper_bgcolor='#FAFAFA')
        return fig

    items = sorted(kmers_dict.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]
    labels = [k for k, _ in items]
    counts = [v for _, v in items]
    colors = [
        '#FFC107' if k == current_kmer else ('#EF5350' if v > 1 else '#42A5F5')
        for k, v in items
    ]

    # also count distribution per multiplicity
    mult_counter = Counter(kmers_dict.values())

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=counts, marker_color=colors,
        hovertemplate='%{x}<br>count = %{y}<extra></extra>',
        showlegend=False,
    ))

    # annotation summary
    repeats = sum(c for v, c in mult_counter.items() if v > 1)
    unique = mult_counter.get(1, 0)
    summary = f"unique={unique} · repeated={repeats}"
    fig.add_annotation(text=summary, showarrow=False,
                        xref='paper', yref='paper', x=1, y=1.06,
                        xanchor='right', font=dict(size=11, color='#555'))

    fig.update_layout(
        height=height,
        margin=dict(l=40, r=10, t=24, b=60),
        xaxis=dict(tickangle=-60, tickfont=dict(size=9, family='monospace'),
                   title=dict(text=f"top {len(items)} k-mer", font=dict(size=10))),
        yaxis=dict(title=dict(text='count', font=dict(size=10)),
                   tickfont=dict(size=9), gridcolor='#EEEEEE'),
        plot_bgcolor='#FAFAFA', paper_bgcolor='#FAFAFA',
    )
    return fig
