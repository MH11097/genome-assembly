"""
Module hiển thị chuỗi DNA với Plotly.

Chức năng:
- Hiển thị sequence với màu cho từng base
- So sánh alignment giữa genome gốc và assembled
- Hiển thị vị trí reads trên genome
"""

from typing import List, Tuple, Optional
import plotly.graph_objects as go


class SequenceVisualizer:
    """
    Hiển thị chuỗi DNA với màu sắc.

    Color scheme cho bases:
    - A: Red (#e63946)
    - T: Orange (#f4a261)
    - G: Teal (#2a9d8f)
    - C: Dark slate (#264653)
    """

    BASE_COLORS = {
        'A': '#e63946',
        'T': '#f4a261',
        'G': '#2a9d8f',
        'C': '#264653',
    }

    def render_sequence(
        self,
        sequence: str,
        max_display: int = 100,
        title: str = ""
    ) -> go.Figure:
        """
        Render chuỗi DNA dạng bar chart với màu cho từng base.

        Args:
            sequence: Chuỗi DNA
            max_display: Số base tối đa hiển thị
            title: Tiêu đề

        Returns:
            Plotly Figure
        """
        display_seq = sequence[:max_display]
        colors = [self.BASE_COLORS.get(b, '#9E9E9E') for b in display_seq]

        fig = go.Figure(data=[
            go.Bar(
                x=list(range(len(display_seq))),
                y=[1] * len(display_seq),
                marker_color=colors,
                text=list(display_seq),
                textposition='inside',
                hovertemplate='Vị trí %{x}: %{text}<extra></extra>',
                showlegend=False
            )
        ])

        fig.update_layout(
            title=title,
            height=100,
            margin=dict(l=10, r=10, t=30 if title else 10, b=10),
            xaxis=dict(showticklabels=False, showgrid=False),
            yaxis=dict(showticklabels=False, showgrid=False, range=[0, 1.3]),
            bargap=0.05
        )

        if len(sequence) > max_display:
            fig.add_annotation(
                x=max_display - 1, y=0.5,
                text=f"...+{len(sequence) - max_display} bp",
                showarrow=False, font=dict(size=10)
            )

        return fig

    def _find_best_offset(self, original: str, assembled: str, max_shift: int = 30) -> int:
        """
        Tìm offset tốt nhất để căn chỉnh assembled với original.

        Returns:
            Offset dương = assembled thiếu đầu, cần thêm gaps ở đầu assembled
            Offset âm = original thiếu đầu, cần thêm gaps ở đầu original
        """
        best_offset = 0
        best_matches = 0

        for offset in range(-max_shift, max_shift + 1):
            matches = 0
            # So sánh: original[i] với assembled[i - offset]
            for i in range(len(original)):
                j = i - offset  # Index trong assembled
                if 0 <= j < len(assembled):
                    if original[i] == assembled[j]:
                        matches += 1

            if matches > best_matches:
                best_matches = matches
                best_offset = offset

        return best_offset

    def render_alignment(
        self,
        original: str,
        assembled: str,
        max_display: int = 80
    ) -> go.Figure:
        """
        So sánh genome gốc với genome lắp ráp.

        Tự động căn chỉnh (align) nếu có phase shift.
        Mismatches được highlight bằng màu xám.

        Args:
            original: Genome gốc
            assembled: Genome đã lắp ráp
            max_display: Số base tối đa

        Returns:
            Plotly Figure với 2 rows
        """
        # Tìm best alignment offset
        offset = self._find_best_offset(original, assembled)

        # Căn chỉnh sequences
        if offset > 0:
            # Assembled bắt đầu sau original -> thêm gaps vào đầu assembled
            aligned_asmb = '-' * offset + assembled
            aligned_orig = original
        elif offset < 0:
            # Original bắt đầu sau assembled -> thêm gaps vào đầu original
            aligned_orig = '-' * (-offset) + original
            aligned_asmb = assembled
        else:
            aligned_orig = original
            aligned_asmb = assembled

        # Cắt về max_display
        orig = aligned_orig[:max_display]
        asmb = aligned_asmb[:max_display]
        max_len = max(len(orig), len(asmb))

        # Original sequence colors
        orig_colors = [self.BASE_COLORS.get(b, '#9E9E9E') for b in orig]

        # Assembled colors - gray for mismatches, handle gaps
        asmb_colors = []
        for i, b in enumerate(asmb):
            if b == '-':
                asmb_colors.append('#EEEEEE')  # Light gray for gap
            elif i < len(orig) and orig[i] != '-' and b == orig[i]:
                asmb_colors.append(self.BASE_COLORS.get(b, '#9E9E9E'))
            else:
                asmb_colors.append('#BDBDBD')  # Gray for mismatch

        fig = go.Figure()

        # Original (top row)
        fig.add_trace(go.Bar(
            x=list(range(len(orig))), y=[1] * len(orig),
            marker_color=orig_colors, text=list(orig),
            textposition='inside', name='Gốc',
            base=[1.2] * len(orig), showlegend=True,
            hovertemplate='Gốc[%{x}]: %{text}<extra></extra>'
        ))

        # Assembled (bottom row)
        fig.add_trace(go.Bar(
            x=list(range(len(asmb))), y=[1] * len(asmb),
            marker_color=asmb_colors, text=list(asmb),
            textposition='inside', name='Lắp ráp',
            base=[0] * len(asmb), showlegend=True,
            hovertemplate='Lắp ráp[%{x}]: %{text}<extra></extra>'
        ))

        # Title với thông tin offset
        title = "So sánh Genome"
        if offset != 0:
            title += f" (căn chỉnh: {'+' if offset > 0 else ''}{offset}bp)"

        fig.update_layout(
            title=title,
            height=180,
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis=dict(showticklabels=False, showgrid=False, range=[-1, max_len]),
            yaxis=dict(showticklabels=False, showgrid=False, range=[-0.2, 2.5]),
            barmode='overlay', bargap=0.05,
            legend=dict(orientation='h', y=1.15)
        )

        return fig

    def render_reads_coverage(
        self,
        genome_length: int,
        reads_positions: List[Tuple[int, int]],
        max_display: int = 100
    ) -> go.Figure:
        """
        Hiển thị coverage của reads trên genome.

        Args:
            genome_length: Độ dài genome
            reads_positions: List of (start, end) positions
            max_display: Số position tối đa

        Returns:
            Plotly Figure showing coverage depth
        """
        # Calculate coverage at each position
        coverage = [0] * min(genome_length, max_display)
        for start, end in reads_positions:
            for i in range(max(0, start), min(end, len(coverage))):
                coverage[i] += 1

        fig = go.Figure(data=[
            go.Bar(
                x=list(range(len(coverage))),
                y=coverage,
                marker_color='#2196F3',
                hovertemplate='Vị trí %{x}: %{y}x coverage<extra></extra>'
            )
        ])

        fig.update_layout(
            title="Coverage theo vị trí",
            height=150,
            margin=dict(l=40, r=10, t=40, b=30),
            xaxis=dict(title="Vị trí (bp)"),
            yaxis=dict(title="Coverage"),
        )

        return fig

    @staticmethod
    def get_base_legend_html() -> str:
        """HTML legend cho màu các base."""
        return """
        <div style="display: flex; gap: 15px; padding: 8px; background: #f5f5f5;
                    border-radius: 5px; font-size: 12px; font-family: monospace; color: #333;">
            <span><span style="color: #e63946; font-weight: bold;">■</span> A (Adenine)</span>
            <span><span style="color: #f4a261; font-weight: bold;">■</span> T (Thymine)</span>
            <span><span style="color: #2a9d8f; font-weight: bold;">■</span> G (Guanine)</span>
            <span><span style="color: #264653; font-weight: bold;">■</span> C (Cytosine)</span>
        </div>
        """
