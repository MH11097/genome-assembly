"""
Section components cho Streamlit app - Single Page Layout.

3 sections:
1. Phân mảnh - genome + reads + Coverage Map (View 5)
2. Assembly - 3-cột layout: Code Trace (V2) | Graph (V1) | Distribution (V4)
   + bottom Action View (V3) + narration
3. Kết quả - metrics + Phase Timeline (V6) + Diff View (V7)
"""

from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

from src.visualization.graph_viz import GraphVisualizer
from src.visualization.sequence_viz import SequenceVisualizer
from src.visualization.network_plot import render_olc_graph, render_dbg_graph, legend_html
from src.visualization.action_view import (
    render_overlap_alignment, render_consensus_stack, render_sliding_window,
    render_hierholzer_stack, render_reconstruct_progress, render_layout_breadcrumb,
)
from src.visualization.pseudocode import render_code_trace, render_var_inspector
from src.visualization.coverage_map import render_coverage_map
from src.visualization.timeline import render_phase_timeline
from src.assembly.metrics import alignment_accuracy


# Đồng bộ với SequenceVisualizer.BASE_COLORS / action_view.BASE_COLORS
_READ_BAR_COLORS = {
    'A': '#e63946', 'T': '#f4a261', 'G': '#2a9d8f', 'C': '#264653',
    '-': '#BDBDBD', 'N': '#9E9E9E',
}


def _render_reads_bars(reads: list, max_display: int = 20) -> str:
    """Render reads thành thanh màu — mỗi base = 1 cell màu theo bảng base color."""
    if not reads:
        return ""
    cell_w = 8  # px/base — đủ nhỏ để read 80bp fit ngang, đủ to để phân biệt màu
    rows = []
    for i, read in enumerate(reads[:max_display]):
        cells = "".join(
            f'<span style="display:inline-block;width:{cell_w}px;height:14px;'
            f'background:{_READ_BAR_COLORS.get(b.upper(), "#EEE")};"></span>'
            for b in read
        )
        rows.append(
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;">'
            f'<span style="display:inline-block;width:36px;font-family:ui-monospace,monospace;'
            f'font-size:12px;color:#666;text-align:right;">R{i}</span>'
            f'<span style="white-space:nowrap;">{cells}</span>'
            f'<span style="font-family:ui-monospace,monospace;font-size:11px;color:#999;">'
            f'{len(read)} bp</span>'
            f'</div>'
        )
    return f'<div style="overflow-x:auto;padding:4px 0;">{"".join(rows)}</div>'


# ===========================================================================
# Section 1 — Phân mảnh
# ===========================================================================

def render_fragmentation_section():
    """Section 1: Quá trình phân mảnh genome thành reads + Coverage Map."""
    st.header("📋 Phân mảnh Genome")

    if not st.session_state.genome:
        st.info("👈 Vui lòng tạo hoặc nhập genome ở sidebar")
        return

    genome = st.session_state.genome

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Độ dài genome", f"{len(genome)} bp")
    with col2:
        gc = (genome.count('G') + genome.count('C')) / len(genome) * 100
        st.metric("GC content", f"{gc:.1f}%")
    with col3:
        st.metric("Số reads", len(st.session_state.reads) if st.session_state.reads else 0)

    seq_viz = SequenceVisualizer()
    fig = seq_viz.render_sequence(genome, max_display=80, title="Genome gốc")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(SequenceVisualizer.get_base_legend_html(), unsafe_allow_html=True)

    # Coverage Map (View 5)
    if st.session_state.get('read_positions'):
        st.subheader("🛰️ Coverage Map")
        st.caption("Mỗi read là một thanh ngang tại vị trí gốc. Vùng đỏ = coverage < 1×.")
        fig_cov = render_coverage_map(len(genome), st.session_state.read_positions)
        st.plotly_chart(fig_cov, use_container_width=True)

    if st.session_state.reads:
        with st.expander(f"📖 Danh sách reads ({len(st.session_state.reads)} đoạn)", expanded=False):
            st.markdown(_render_reads_bars(st.session_state.reads, max_display=20),
                        unsafe_allow_html=True)
            if len(st.session_state.reads) > 20:
                st.caption(f"... và {len(st.session_state.reads) - 20} reads khác")


# ===========================================================================
# Section 2 — Assembly (3 cột + Action View)
# ===========================================================================

def render_assembly_section():
    """Section 2: Code | Graph | Distribution + Action View."""
    st.header("🔬 Assembly từng bước")

    if not st.session_state.assembly_done:
        st.info("👈 Nhấn 'Chạy lắp ráp' ở sidebar để bắt đầu")
        return

    algo = st.session_state.algorithm

    if algo == "So sánh cả hai":
        tab_olc, tab_dbg = st.tabs(["🟦 OLC (Hamilton)", "🟩 DBG (Euler)"])
        with tab_olc:
            _render_algo_full("OLC", key_prefix="cmp_olc")
        with tab_dbg:
            _render_algo_full("DBG", key_prefix="cmp_dbg")
    else:
        _render_algo_full(algo, key_prefix=algo.lower())


def _get_controller(algo: str):
    if algo == "OLC":
        return st.session_state.get('olc_animation_controller')
    return st.session_state.get('dbg_animation_controller')


def _render_step_controls(controller, key_prefix: str):
    """Step navigation row — đặt phía trên các panel."""
    if not controller or not controller.has_frames():
        st.warning("Không có dữ liệu animation")
        return

    cols = st.columns([1, 1, 1, 1, 6, 2])
    with cols[0]:
        if st.button("⏮", key=f"{key_prefix}_first", disabled=controller.is_first,
                     use_container_width=True, help="Về đầu"):
            controller.reset(); st.rerun()
    with cols[1]:
        if st.button("◀", key=f"{key_prefix}_prev", disabled=controller.is_first,
                     use_container_width=True, help="Bước trước"):
            controller.prev_step(); st.rerun()
    with cols[2]:
        if st.button("▶", key=f"{key_prefix}_next", disabled=controller.is_last,
                     use_container_width=True, help="Bước sau"):
            controller.next_step(); st.rerun()
    with cols[3]:
        if st.button("⏭", key=f"{key_prefix}_last", disabled=controller.is_last,
                     use_container_width=True, help="Đến cuối"):
            controller.go_to_end(); st.rerun()
    with cols[4]:
        step = st.slider("Bước:", 0, controller.total_frames - 1,
                         controller.current_index,
                         key=f"{key_prefix}_slider", label_visibility="collapsed")
        if step != controller.current_index:
            controller.go_to_step(step); st.rerun()
    with cols[5]:
        st.caption(f"Bước **{controller.current_index + 1}** / {controller.total_frames}")

    st.progress(controller.progress)


def _phase_badge(phase: str) -> str:
    """Badge tiếng Việt cho phase."""
    names = {
        'overlap': '🔍 Overlap',
        'layout': '🛤️ Layout (Hamilton)',
        'consensus': '🧬 Consensus',
        'kmer': '🔤 K-mers',
        'graph': '🕸️ Build graph',
        'euler': '🛤️ Euler (Hierholzer)',
        'reconstruct': '🧬 Reconstruct',
    }
    return names.get(phase, phase)


def _render_algo_full(algo: str, key_prefix: str):
    """Layout đầy đủ cho 1 thuật toán."""
    controller = _get_controller(algo)
    if not controller or not controller.has_frames():
        st.warning(f"Không có dữ liệu {algo}")
        return

    # Step controls (hàng đầu)
    _render_step_controls(controller, key_prefix)

    frame = controller.current_frame
    raw_state = frame.extra_data.get('raw_state') if frame else None
    # Đọc trực tiếp từ raw_state để giữ đúng tên phase ('layout' thay vì 'path'
    # — AnimationController map 'layout' → AnimationPhase.PATH cho lý do lịch sử).
    phase = getattr(raw_state, 'phase', '') if raw_state else ''

    # Narration message
    if frame:
        st.info(f"**{_phase_badge(phase)}** — {frame.message}")

    # 2-cột top row
    col_code, col_graph = st.columns([1.0, 1.5])

    with col_code:
        st.markdown("**📝 Code trace**")
        backtrack = bool(getattr(raw_state, 'backtrack', False)) if raw_state else False
        st.markdown(render_code_trace(algo, phase=phase,
                                       message=frame.message if frame else '',
                                       backtrack=backtrack),
                    unsafe_allow_html=True)
        st.markdown(_var_inspector_for(algo, raw_state, frame), unsafe_allow_html=True)

    with col_graph:
        st.markdown("**🕸️ Đồ thị (đồng bộ theo bước)**")
        st.markdown(legend_html(), unsafe_allow_html=True)
        _render_stepwise_graph(algo, raw_state, controller.current_index)

    # Bottom: Action View
    st.markdown("**🎬 Cơ chế (Action View)**")
    _render_action_view(algo, raw_state, phase)

    # PyVis detail (fallback / explorer mode)
    with st.expander("🔍 Đồ thị PyVis chi tiết (pan/zoom đầy đủ)"):
        _render_pyvis_graph(algo)


# ---------- Stepwise graph ----------

def _olc_state_dict(raw_state, *, visible_overlaps: int) -> dict:
    if raw_state is None:
        return {}
    return {
        'phase': getattr(raw_state, 'phase', None),
        'current_pair': getattr(raw_state, 'current_pair', (None, None)),
        'path': list(getattr(raw_state, 'path', []) or []),
        'visited': set(getattr(raw_state, 'visited', set()) or set()),
        'visible_overlaps': visible_overlaps,
        'backtrack': bool(getattr(raw_state, 'backtrack', False)),
    }


def _dbg_state_dict(raw_state) -> dict:
    if raw_state is None:
        return {}
    return {
        'phase': getattr(raw_state, 'phase', None),
        'current_node': getattr(raw_state, 'current_node', '') or '',
        'next_node': getattr(raw_state, 'next_node', '') or '',
        'visited_edges': list(getattr(raw_state, 'visited_edges', []) or []),
        'path': list(getattr(raw_state, 'path', []) or []),
    }


def _render_stepwise_graph(algo: str, raw_state, step_idx: int):
    if algo == "OLC":
        assembler = st.session_state.get('olc_assembler')
        if not assembler:
            st.warning("Chưa có dữ liệu OLC"); return
        overlaps_all = [(o.read_a, o.read_b, o.length) for o in assembler.overlaps]
        # During overlap phase, only show overlaps already found
        visible = len(overlaps_all)
        if raw_state and getattr(raw_state, 'phase', '') == 'overlap':
            visible = len(getattr(raw_state, 'overlaps_found', []) or [])
        fig = render_olc_graph(
            reads=assembler.reads,
            overlaps=overlaps_all,
            state=_olc_state_dict(raw_state, visible_overlaps=visible),
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True, key=f"olc_graph_{step_idx}")
        st.caption(f"📊 {len(assembler.reads)} nodes · {len(overlaps_all)} edges (cumulative)")

    else:
        assembler = st.session_state.get('dbg_assembler')
        if not assembler:
            st.warning("Chưa có dữ liệu DBG"); return
        # During kmer phase, graph chưa được xây — hiển thị graph cuối làm nền dim
        fig = render_dbg_graph(
            graph=dict(assembler.graph),
            state=_dbg_state_dict(raw_state),
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True, key=f"dbg_graph_{step_idx}")
        stats = assembler.get_graph_stats()
        st.caption(f"📊 {stats['num_nodes']} nodes · {stats['num_edges']} edges · k={stats['k']}")


def _render_pyvis_graph(algo: str):
    graph_viz = GraphVisualizer(height="380px")
    if algo == "OLC":
        a = st.session_state.get('olc_assembler')
        if not a:
            st.warning("Chưa có dữ liệu OLC"); return
        ov = [(o.read_a, o.read_b, o.length) for o in a.overlaps]
        html = graph_viz.render_overlap_graph(reads=a.reads, overlaps=ov, path=a.path)
        components.html(html, height=400, scrolling=True)
    else:
        a = st.session_state.get('dbg_assembler')
        if not a:
            st.warning("Chưa có dữ liệu DBG"); return
        html = graph_viz.render_debruijn_graph(graph=dict(a.graph), path=a.path)
        components.html(html, height=400, scrolling=True)


# ---------- Action View ----------

def _render_action_view(algo: str, raw_state, phase: str):
    if raw_state is None:
        st.markdown('<div style="padding:8px;color:#888;">(không có state)</div>',
                    unsafe_allow_html=True)
        return

    if algo == "OLC":
        a = st.session_state.get('olc_assembler')
        if not a:
            return

        if phase == 'overlap':
            i, j = getattr(raw_state, 'current_pair', (0, 0))
            ov_len = getattr(raw_state, 'overlap_length', 0)
            if 0 <= i < len(a.reads) and 0 <= j < len(a.reads):
                html = render_overlap_alignment(
                    a.reads[i], a.reads[j], ov_len, label_a=f"R{i}", label_b=f"R{j}")
                st.markdown(html, unsafe_allow_html=True)

        elif phase == 'layout':
            path = list(getattr(raw_state, 'path', []) or [])
            visited = set(getattr(raw_state, 'visited', set()) or set())
            backtrack = bool(getattr(raw_state, 'backtrack', False))
            cp = getattr(raw_state, 'current_pair', None)
            html = render_layout_breadcrumb(
                path, visited, len(a.reads), backtrack=backtrack, current_pair=cp)
            st.markdown(html, unsafe_allow_html=True)

        elif phase == 'consensus':
            # Find current step index in path (số read đã ghép)
            path = list(a.path)
            consensus = getattr(raw_state, 'consensus_so_far', '') or ''
            overlaps_map = {(o.read_a, o.read_b): o.length for o in a.overlaps}
            # Determine current step: count consensus phase states up to this state
            # Simpler heuristic: current head = read whose merge_offset matches state
            cur_step = 0
            cp = getattr(raw_state, 'current_pair', None)
            if cp and cp[1] in path:
                cur_step = path.index(cp[1])
            html = render_consensus_stack(
                a.reads, path, overlaps_map, current_step=cur_step, consensus=consensus)
            st.markdown(html, unsafe_allow_html=True)

    else:  # DBG
        a = st.session_state.get('dbg_assembler')
        if not a:
            return

        if phase == 'kmer':
            read_idx = getattr(raw_state, 'read_index', -1)
            pos = getattr(raw_state, 'window_pos', -1)
            if 0 <= read_idx < len(a.reads):
                tray = list(a.kmers.keys())[:60]  # approx tray
                html = render_sliding_window(
                    a.reads[read_idx], a.k, pos, read_index=read_idx, kmer_tray=tray)
                st.markdown(html, unsafe_allow_html=True)

        elif phase == 'graph':
            st.markdown(
                f'<div style="padding:8px;background:#FAFAFA;border-radius:6px;">'
                f'Mỗi k-mer trở thành <b>cạnh</b>: prefix (k-1)-mer → suffix (k-1)-mer. '
                f'Đồ thị hoàn thành với <b>{len(a.graph)}</b> đỉnh nguồn, '
                f'<b>{sum(len(v) for v in a.graph.values())}</b> cạnh.'
                f'</div>',
                unsafe_allow_html=True,
            )

        elif phase == 'euler':
            stack = list(getattr(raw_state, 'stack_snapshot', []) or [])
            cur = getattr(raw_state, 'current_node', '') or ''
            nxt = getattr(raw_state, 'next_node', '') or ''
            er = getattr(raw_state, 'edges_remaining', 0) or 0
            et = getattr(raw_state, 'edges_total', 0) or 0
            html = render_hierholzer_stack(stack, cur, nxt, er, et)
            st.markdown(html, unsafe_allow_html=True)

        elif phase == 'reconstruct':
            genome = getattr(raw_state, 'genome_so_far', '') or ''
            cur = getattr(raw_state, 'current_node', '') or ''
            html = render_reconstruct_progress(genome, cur, a.k)
            st.markdown(html, unsafe_allow_html=True)


# ---------- Variable inspector ----------

def _var_inspector_for(algo: str, raw_state, frame) -> str:
    if raw_state is None:
        return render_var_inspector({})
    vars_dict = {}
    if algo == "OLC":
        cp = getattr(raw_state, 'current_pair', None)
        vars_dict['phase'] = getattr(raw_state, 'phase', '')
        vars_dict['current_pair'] = f"R{cp[0]} → R{cp[1]}" if cp and cp[0] is not None else "—"
        vars_dict['overlap_length'] = getattr(raw_state, 'overlap_length', 0)
        path = list(getattr(raw_state, 'path', []) or [])
        vars_dict['len(path)'] = len(path)
        vars_dict['path[-3:]'] = ' → '.join(f"R{p}" for p in path[-3:]) if path else '—'
        vars_dict['len(visited)'] = len(getattr(raw_state, 'visited', set()) or set())
        vars_dict['backtrack'] = getattr(raw_state, 'backtrack', False)
    else:
        vars_dict['phase'] = getattr(raw_state, 'phase', '')
        vars_dict['current_node'] = getattr(raw_state, 'current_node', '') or '—'
        vars_dict['next_node'] = getattr(raw_state, 'next_node', '') or '—'
        vars_dict['current_kmer'] = getattr(raw_state, 'current_kmer', '') or '—'
        vars_dict['window_pos'] = getattr(raw_state, 'window_pos', -1)
        et = getattr(raw_state, 'edges_total', 0)
        er = getattr(raw_state, 'edges_remaining', 0)
        if et > 0:
            vars_dict['edges_visited'] = f"{et - er}/{et}"
        vars_dict['len(stack)'] = len(getattr(raw_state, 'stack_snapshot', []) or [])
        vars_dict['|genome_so_far|'] = len(getattr(raw_state, 'genome_so_far', '') or '')
    return render_var_inspector(vars_dict)


# ===========================================================================
# Section 3 — Kết quả
# ===========================================================================

def render_results_section():
    """Section 3: Kết quả lắp ráp."""
    st.header("📊 Kết quả")

    genome = st.session_state.genome
    algo = st.session_state.algorithm
    seq_viz = SequenceVisualizer()

    if algo == "So sánh cả hai":
        _render_comparison_results(genome, seq_viz)
    elif algo == "OLC":
        _render_single_result("OLC", st.session_state.olc_result, genome, seq_viz)
    else:
        _render_single_result("DBG", st.session_state.dbg_result, genome, seq_viz)


def _render_single_result(name: str, result: str, genome: str, seq_viz):
    if not result:
        st.warning(f"Không có kết quả {name}")
        return

    accuracy = alignment_accuracy(result, genome)
    time_ms = (st.session_state.olc_time_ms if name == "OLC"
               else st.session_state.dbg_time_ms)
    nodes, edges = _graph_stats(name)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Genome gốc", f"{len(genome)} bp")
    with col2:
        st.metric(f"Kết quả {name}", f"{len(result)} bp",
                  f"{len(result) / len(genome) * 100:.0f}% covered")
    with col3:
        st.metric("Độ chính xác", f"{accuracy}%")
    with col4:
        st.metric("Thời gian", _format_time(time_ms))

    complexity = _complexity_label(name)
    st.caption(f"📐 **{complexity}** · đồ thị: {nodes} đỉnh / {edges} cạnh")

    with st.expander("📊 Alignment bar (kiểu cũ)"):
        fig = seq_viz.render_alignment(genome, result, max_display=60)
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("🔤 Xem chuỗi thô"):
        st.text_area("Genome gốc:", genome[:500], height=60, disabled=True)
        st.text_area(f"Kết quả {name}:", result[:500], height=60, disabled=True)


def _render_comparison_results(genome: str, seq_viz):
    olc_result = st.session_state.olc_result
    dbg_result = st.session_state.dbg_result

    olc_acc = alignment_accuracy(olc_result, genome) if olc_result else 0
    dbg_acc = alignment_accuracy(dbg_result, genome) if dbg_result else 0
    olc_t = st.session_state.olc_time_ms
    dbg_t = st.session_state.dbg_time_ms
    speedup = (olc_t / dbg_t) if dbg_t > 0 else 0

    olc_nodes, olc_edges = _graph_stats("OLC")
    dbg_nodes, dbg_edges = _graph_stats("DBG")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Genome gốc", f"{len(genome)} bp")
    with col2:
        st.metric("OLC", f"{len(olc_result)} bp",
                  f"{olc_acc}% • {_format_time(olc_t)}")
    with col3:
        st.metric("DBG", f"{len(dbg_result)} bp",
                  f"{dbg_acc}% • {_format_time(dbg_t)}")

    st.caption(
        f"📐 OLC **{_complexity_label('OLC')}** vs DBG **{_complexity_label('DBG')}** · "
        f"`n` = số reads, `m` = read length, `V/E` = đỉnh/cạnh đồ thị"
    )
    if speedup > 0:
        if speedup >= 1.2:
            st.caption(f"⚡ DBG nhanh hơn OLC **{speedup:.1f}×** — phù hợp với khác biệt độ phức tạp O(n²) vs O(n).")
        elif speedup <= 0.8:
            st.caption(f"⚡ Trong run này OLC nhanh hơn DBG **{1/speedup:.1f}×** (graph quá nhỏ để O(n²) lộ).")
        else:
            st.caption(f"⚡ Runtime gần như tương đương ({speedup:.2f}×).")

    # Phase Timeline (View 6)
    olc_timing = _get_timing("OLC")
    dbg_timing = _get_timing("DBG")
    if olc_timing or dbg_timing:
        st.subheader("⏱️ Phase Timeline")
        fig = render_phase_timeline(olc_timing, dbg_timing)
        st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "🔧 Tham số: "
        f"genome={len(genome)} bp · "
        f"reads={len(st.session_state.reads)} × {st.session_state.read_length} bp "
        f"(coverage {st.session_state.coverage}×) · "
        f"OLC min_overlap={st.session_state.min_overlap} · "
        f"DBG k={st.session_state.k_value}"
    )


# ---------- Helpers ----------

def _complexity_label(name: str) -> str:
    if name == "OLC":
        return "O(n²·m²)"
    return "O(n·m + V+E)"


def _graph_stats(name: str):
    if name == "OLC":
        a = st.session_state.get('olc_assembler')
        if not a:
            return 0, 0
        return len(a.reads), len(a.overlaps)
    a = st.session_state.get('dbg_assembler')
    if not a:
        return 0, 0
    s = a.get_graph_stats()
    return s.get('num_nodes', 0), s.get('num_edges', 0)


def _get_timing(name: str) -> Optional[dict]:
    if name == "OLC":
        a = st.session_state.get('olc_assembler')
    else:
        a = st.session_state.get('dbg_assembler')
    return getattr(a, 'timing_ms', None) if a else None


def _format_time(ms: float) -> str:
    if ms <= 0:
        return "—"
    if ms < 1:
        return f"{ms * 1000:.0f} μs"
    if ms < 1000:
        return f"{ms:.1f} ms"
    return f"{ms / 1000:.2f} s"


