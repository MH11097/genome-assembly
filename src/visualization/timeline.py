"""
Phase Timeline (View 6): Gantt-style horizontal bar chart so sánh thời gian
mỗi phase của OLC và DBG.
"""

from __future__ import annotations

from typing import Dict, Optional

import plotly.graph_objects as go


_PHASE_COLORS = {
    'overlap': '#42A5F5',
    'layout': '#5E35B2',
    'consensus': '#26A69A',
    'kmer': '#7CB342',
    'graph': '#FFA726',
    'euler': '#EF5350',
    'reconstruct': '#26C6DA',
}

_PHASE_LABELS = {
    'overlap': 'Overlap',
    'layout': 'Layout (Hamilton)',
    'consensus': 'Consensus',
    'kmer': 'K-mers',
    'graph': 'Build graph',
    'euler': 'Euler (Hierholzer)',
    'reconstruct': 'Reconstruct',
}


def render_phase_timeline(
    olc_timing: Optional[Dict[str, float]] = None,
    dbg_timing: Optional[Dict[str, float]] = None,
    *, height: int = 280,
) -> go.Figure:
    """
    Mỗi thuật toán = 1 hàng. Mỗi phase = 1 bar chồng (stacked horizontal).
    Width thật theo ms.
    """
    olc_timing = olc_timing or {}
    dbg_timing = dbg_timing or {}

    fig = go.Figure()

    def _add_row(label: str, timing: Dict[str, float], phases_order: list):
        cum = 0.0
        for phase in phases_order:
            duration = timing.get(phase, 0.0)
            if duration <= 0:
                continue
            fig.add_trace(go.Bar(
                y=[label],
                x=[duration],
                base=[cum],
                orientation='h',
                marker=dict(color=_PHASE_COLORS.get(phase, '#9E9E9E'),
                            line=dict(color='white', width=2)),
                name=_PHASE_LABELS.get(phase, phase),
                text=[f"{_PHASE_LABELS.get(phase, phase)}<br>{duration:.1f} ms"],
                textposition='inside',
                insidetextanchor='middle',
                textfont=dict(color='white', size=11),
                hovertemplate=f'<b>{_PHASE_LABELS.get(phase, phase)}</b><br>'
                              f'{duration:.2f} ms<extra></extra>',
                showlegend=False,
            ))
            cum += duration

    _add_row('OLC', olc_timing, ['overlap', 'layout', 'consensus'])
    _add_row('DBG', dbg_timing, ['kmer', 'graph', 'euler', 'reconstruct'])

    total_olc = sum(olc_timing.values())
    total_dbg = sum(dbg_timing.values())
    max_x = max(total_olc, total_dbg, 1.0) * 1.05

    annotations = []
    if total_olc > 0:
        annotations.append(dict(
            x=total_olc, y='OLC', text=f"<b>{total_olc:.1f} ms</b>",
            showarrow=False, xanchor='left', font=dict(size=11, color='#333'),
            xshift=8,
        ))
    if total_dbg > 0:
        annotations.append(dict(
            x=total_dbg, y='DBG', text=f"<b>{total_dbg:.1f} ms</b>",
            showarrow=False, xanchor='left', font=dict(size=11, color='#333'),
            xshift=8,
        ))

    fig.update_layout(
        height=height,
        barmode='stack',
        margin=dict(l=50, r=80, t=30, b=40),
        xaxis=dict(title=dict(text='thời gian (ms)', font=dict(size=10)),
                   tickfont=dict(size=10), gridcolor='#EEEEEE', range=[0, max_x]),
        yaxis=dict(tickfont=dict(size=12, family='monospace'), categoryorder='array',
                   categoryarray=['DBG', 'OLC']),
        plot_bgcolor='#FAFAFA', paper_bgcolor='#FAFAFA',
        annotations=annotations,
        showlegend=False,
    )
    return fig
