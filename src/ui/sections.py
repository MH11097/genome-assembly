"""
Section components cho Streamlit app - Single Page Layout.

3 sections:
1. Phân mảnh - hiển thị genome và reads (top)
2. Assembly - thuật toán + đồ thị side by side (middle)
3. Kết quả - metrics và so sánh (bottom, after assembly done)
"""

import streamlit as st
import streamlit.components.v1 as components
from src.visualization.graph_viz import GraphVisualizer
from src.visualization.sequence_viz import SequenceVisualizer
from src.assembly.metrics import alignment_accuracy


def render_fragmentation_section():
    """Section 1: Quá trình phân mảnh genome thành reads."""
    st.header("📋 Phân mảnh Genome")

    if not st.session_state.genome:
        st.info("👈 Vui lòng tạo hoặc nhập genome ở sidebar")
        return

    genome = st.session_state.genome

    # Metrics row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Độ dài genome", f"{len(genome)} bp")
    with col2:
        gc = (genome.count('G') + genome.count('C')) / len(genome) * 100
        st.metric("GC content", f"{gc:.1f}%")
    with col3:
        st.metric("Số reads", len(st.session_state.reads) if st.session_state.reads else 0)

    # Sequence visualization
    seq_viz = SequenceVisualizer()
    fig = seq_viz.render_sequence(genome, max_display=80, title="Genome gốc")
    st.plotly_chart(fig, use_container_width=True)

    # Legend
    st.markdown(SequenceVisualizer.get_base_legend_html(), unsafe_allow_html=True)

    # Reads display
    if st.session_state.reads:
        with st.expander(f"📖 Reads ({len(st.session_state.reads)} đoạn)", expanded=False):
            reads = st.session_state.reads[:20]
            cols = st.columns(5)
            for i, read in enumerate(reads):
                with cols[i % 5]:
                    display = read if len(read) <= 10 else f"{read[:8]}..."
                    st.code(f"R{i}: {display}", language=None)
            if len(st.session_state.reads) > 20:
                st.caption(f"... và {len(st.session_state.reads) - 20} reads khác")


def render_assembly_section():
    """Section 2: Thuật toán + Đồ thị side by side."""
    st.header("🔬 Assembly")

    if not st.session_state.assembly_done:
        st.info("👈 Nhấn 'Chạy lắp ráp' ở sidebar để bắt đầu")
        return

    algo = st.session_state.algorithm

    # 2 columns layout: 40% algorithm, 60% graph
    col_algo, col_graph = st.columns([2, 3])

    with col_algo:
        _render_algorithm_panel()

    with col_graph:
        _render_graph_panel(algo)


def _render_algorithm_panel():
    """Panel thuật toán với animation controls."""
    st.subheader("⚙️ Thuật toán từng bước")

    controller = st.session_state.animation_controller
    if not controller or not controller.has_frames():
        st.warning("Không có dữ liệu animation")
        return

    # Compact navigation buttons
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("⏮️", disabled=controller.is_first, use_container_width=True, help="Về đầu"):
            controller.reset()
            st.rerun()
    with c2:
        if st.button("◀️", disabled=controller.is_first, use_container_width=True, help="Trước"):
            controller.prev_step()
            st.rerun()
    with c3:
        if st.button("▶️", disabled=controller.is_last, use_container_width=True, help="Sau"):
            controller.next_step()
            st.rerun()
    with c4:
        if st.button("⏭️", disabled=controller.is_last, use_container_width=True, help="Về cuối"):
            controller.go_to_end()
            st.rerun()

    # Slider
    step = st.slider(
        "Bước:",
        0, controller.total_frames - 1,
        controller.current_index,
        label_visibility="collapsed"
    )
    if step != controller.current_index:
        controller.go_to_step(step)
        st.rerun()

    # Progress
    st.progress(controller.progress)
    st.caption(f"Bước {controller.current_index + 1} / {controller.total_frames}")

    # Current step message
    frame = controller.current_frame
    if frame:
        phase_names = {
            'overlap': '🔍 Tìm Overlap',
            'path': '🛤️ Tìm đường đi',
            'consensus': '🧬 Ghép chuỗi',
            'kmer': '🔤 Tạo k-mers',
            'graph': '🕸️ Xây đồ thị',
            'euler': '🛤️ Tìm đường Euler',
            'reconstruct': '🧬 Tái tạo genome'
        }
        phase_display = phase_names.get(frame.phase.value, frame.phase.value)
        st.info(f"**{phase_display}**\n\n{frame.message}")

    # Phase summary (collapsed)
    with st.expander("📊 Thống kê"):
        summary = controller.get_phase_summary()
        for phase, count in summary.items():
            st.write(f"• {phase}: {count} bước")


def _render_graph_panel(algo: str):
    """Panel đồ thị visualization."""
    st.subheader("🕸️ Đồ thị")

    # Legend
    st.markdown(GraphVisualizer.get_legend_html(), unsafe_allow_html=True)

    graph_viz = GraphVisualizer(height="380px")

    if algo == "So sánh cả hai":
        # Sub-tabs for comparison
        graph_tab1, graph_tab2 = st.tabs(["OLC", "DBG"])
        with graph_tab1:
            _render_olc_graph(graph_viz, height=350)
        with graph_tab2:
            _render_dbg_graph(graph_viz, height=350)
    elif algo == "OLC":
        _render_olc_graph(graph_viz, height=400)
    else:
        _render_dbg_graph(graph_viz, height=400)


def _render_olc_graph(graph_viz, height=400):
    """Render OLC overlap graph."""
    assembler = st.session_state.olc_assembler
    if not assembler:
        st.warning("Chưa có dữ liệu OLC")
        return

    overlaps = [(o.read_a, o.read_b, o.length) for o in assembler.overlaps]
    html = graph_viz.render_overlap_graph(
        reads=assembler.reads,
        overlaps=overlaps,
        path=assembler.path
    )
    components.html(html, height=height, scrolling=True)
    st.caption(f"📊 {len(assembler.reads)} nodes, {len(overlaps)} edges")


def _render_dbg_graph(graph_viz, height=400):
    """Render DBG de Bruijn graph."""
    assembler = st.session_state.dbg_assembler
    if not assembler:
        st.warning("Chưa có dữ liệu DBG")
        return

    stats = assembler.get_graph_stats()
    html = graph_viz.render_debruijn_graph(
        graph=dict(assembler.graph),
        path=assembler.path
    )
    components.html(html, height=height, scrolling=True)
    st.caption(f"📊 {stats['num_nodes']} nodes, {stats['num_edges']} edges, k={stats['k']}")


def render_results_section():
    """Section 3: Kết quả lắp ráp."""
    st.header("📊 Kết quả lắp ráp")

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
    """Render result for single algorithm."""
    if not result:
        st.warning(f"Không có kết quả {name}")
        return

    accuracy = alignment_accuracy(result, genome)
    time_ms = (st.session_state.olc_time_ms if name == "OLC"
               else st.session_state.dbg_time_ms)

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Genome gốc", f"{len(genome)} bp")
    with col2:
        st.metric(f"Kết quả {name}", f"{len(result)} bp")
    with col3:
        st.metric("Độ chính xác", f"{accuracy}%")
    with col4:
        st.metric("Thời gian", _format_time(time_ms))

    # Alignment view
    fig = seq_viz.render_alignment(genome, result, max_display=60)
    st.plotly_chart(fig, use_container_width=True)

    # Raw sequences
    with st.expander("🔤 Xem chuỗi thô"):
        st.text_area("Genome gốc:", genome[:500], height=60, disabled=True)
        st.text_area(f"Kết quả {name}:", result[:500], height=60, disabled=True)


def _render_comparison_results(genome: str, seq_viz):
    """Render comparison between OLC and DBG."""
    olc_result = st.session_state.olc_result
    dbg_result = st.session_state.dbg_result

    olc_acc = alignment_accuracy(olc_result, genome) if olc_result else 0
    dbg_acc = alignment_accuracy(dbg_result, genome) if dbg_result else 0
    olc_t = st.session_state.olc_time_ms
    dbg_t = st.session_state.dbg_time_ms
    speedup = (olc_t / dbg_t) if dbg_t > 0 else 0

    # Metrics row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Genome gốc", f"{len(genome)} bp")
    with col2:
        st.metric("OLC", f"{len(olc_result)} bp",
                  f"{olc_acc}% • {_format_time(olc_t)}")
    with col3:
        st.metric("DBG", f"{len(dbg_result)} bp",
                  f"{dbg_acc}% • {_format_time(dbg_t)}")

    if speedup > 0:
        st.caption(f"⚡ DBG nhanh hơn OLC **{speedup:.1f}×**")

    # Side by side alignment
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("OLC vs Gốc")
        if olc_result:
            fig = seq_viz.render_alignment(genome, olc_result, max_display=35)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("DBG vs Gốc")
        if dbg_result:
            fig = seq_viz.render_alignment(genome, dbg_result, max_display=35)
            st.plotly_chart(fig, use_container_width=True)

    # Summary table
    st.subheader("Bảng tổng hợp")
    st.table({
        "Thuật toán": ["OLC (Hamilton)", "DBG (Euler)"],
        "Độ dài": [len(olc_result), len(dbg_result)],
        "Chính xác (%)": [olc_acc, dbg_acc],
        "Thời gian": [_format_time(olc_t), _format_time(dbg_t)],
        "Số bước": [
            len(st.session_state.olc_assembler.get_step_states()) if st.session_state.olc_assembler else 0,
            len(st.session_state.dbg_assembler.get_step_states()) if st.session_state.dbg_assembler else 0
        ]
    })


def _format_time(ms: float) -> str:
    """Format thời gian: <1ms hiện μs, <1000ms hiện ms, >=1000ms hiện s."""
    if ms <= 0:
        return "—"
    if ms < 1:
        return f"{ms * 1000:.0f} μs"
    if ms < 1000:
        return f"{ms:.1f} ms"
    return f"{ms / 1000:.2f} s"
