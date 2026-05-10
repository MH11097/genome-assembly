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

    if algo == "So sánh cả hai":
        tab_olc, tab_dbg = st.tabs(["🟦 OLC (Hamilton)", "🟩 DBG (Euler)"])
        with tab_olc:
            _render_algo_pair("OLC", key_prefix="cmp_olc")
        with tab_dbg:
            _render_algo_pair("DBG", key_prefix="cmp_dbg")
    else:
        _render_algo_pair(algo, key_prefix=algo.lower())


def _render_algo_pair(algo: str, key_prefix: str):
    """Render cặp panel thuật toán + đồ thị cho 1 thuật toán."""
    col_algo, col_graph = st.columns([2, 3])

    if algo == "OLC":
        controller = st.session_state.get('olc_animation_controller')
    else:
        controller = st.session_state.get('dbg_animation_controller')

    with col_algo:
        _render_algorithm_panel(controller, key_prefix=key_prefix)
    with col_graph:
        _render_graph_panel(algo)


def _render_algorithm_panel(controller, key_prefix: str = ""):
    """Panel thuật toán với animation controls (nhận controller từ caller)."""
    st.subheader("⚙️ Thuật toán từng bước")

    if not controller or not controller.has_frames():
        st.warning("Không có dữ liệu animation")
        return

    # Compact navigation buttons (key prefix để tránh xung đột giữa 2 tab compare)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("⏮️", key=f"{key_prefix}_first", disabled=controller.is_first,
                     use_container_width=True, help="Về đầu"):
            controller.reset()
            st.rerun()
    with c2:
        if st.button("◀️", key=f"{key_prefix}_prev", disabled=controller.is_first,
                     use_container_width=True, help="Trước"):
            controller.prev_step()
            st.rerun()
    with c3:
        if st.button("▶️", key=f"{key_prefix}_next", disabled=controller.is_last,
                     use_container_width=True, help="Sau"):
            controller.next_step()
            st.rerun()
    with c4:
        if st.button("⏭️", key=f"{key_prefix}_last", disabled=controller.is_last,
                     use_container_width=True, help="Về cuối"):
            controller.go_to_end()
            st.rerun()

    step = st.slider(
        "Bước:",
        0, controller.total_frames - 1,
        controller.current_index,
        key=f"{key_prefix}_slider",
        label_visibility="collapsed"
    )
    if step != controller.current_index:
        controller.go_to_step(step)
        st.rerun()

    st.progress(controller.progress)
    st.caption(f"Bước {controller.current_index + 1} / {controller.total_frames}")

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

    with st.expander("📊 Thống kê"):
        summary = controller.get_phase_summary()
        for phase, count in summary.items():
            st.write(f"• {phase}: {count} bước")


def _render_graph_panel(algo: str):
    """Panel đồ thị visualization (1 thuật toán)."""
    st.subheader("🕸️ Đồ thị")
    st.markdown(GraphVisualizer.get_legend_html(), unsafe_allow_html=True)

    graph_viz = GraphVisualizer(height="380px")
    if algo == "OLC":
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
    nodes, edges = _graph_stats(name)

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Genome gốc", f"{len(genome)} bp")
    with col2:
        st.metric(f"Kết quả {name}",
                  f"{len(result)} bp",
                  f"{len(result) / len(genome) * 100:.0f}% covered")
    with col3:
        st.metric("Độ chính xác", f"{accuracy}%")
    with col4:
        st.metric("Thời gian", _format_time(time_ms))

    # Complexity + graph stats
    complexity = _complexity_label(name)
    st.caption(f"📐 **{complexity}** · đồ thị: {nodes} đỉnh / {edges} cạnh")

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

    olc_nodes, olc_edges = _graph_stats("OLC")
    dbg_nodes, dbg_edges = _graph_stats("DBG")

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

    # Complexity caption
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
            st.caption(f"⚡ Runtime gần như tương đương ({speedup:.2f}×) — kích thước input chưa đủ tách 2 thuật toán.")

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

    # Parameter context caption
    st.caption(
        "🔧 Tham số: "
        f"genome={len(genome)} bp · "
        f"reads={len(st.session_state.reads)} × {st.session_state.read_length} bp "
        f"(coverage {st.session_state.coverage}× tự động) · "
        f"OLC min_overlap={st.session_state.min_overlap} · "
        f"DBG k={st.session_state.k_value}"
    )

    # Summary table
    st.subheader("Bảng tổng hợp")
    st.table({
        "Thuật toán": ["OLC (Hamilton)", "DBG (Euler)"],
        "Độ dài (bp)": [len(olc_result), len(dbg_result)],
        "% covered": [
            f"{len(olc_result) / len(genome) * 100:.0f}%",
            f"{len(dbg_result) / len(genome) * 100:.0f}%"
        ],
        "Chính xác (%)": [olc_acc, dbg_acc],
        "Thời gian": [_format_time(olc_t), _format_time(dbg_t)],
        "Đỉnh đồ thị": [olc_nodes, dbg_nodes],
        "Cạnh đồ thị": [olc_edges, dbg_edges],
    })

    _render_comparison_insight(
        olc_acc=olc_acc, dbg_acc=dbg_acc,
        olc_t=olc_t, dbg_t=dbg_t,
        olc_edges=olc_edges, dbg_edges=dbg_edges,
    )


def _render_comparison_insight(*, olc_acc, dbg_acc, olc_t, dbg_t, olc_edges, dbg_edges):
    """Nhận xét tự động dựa trên metric so sánh."""
    notes = []

    if dbg_t > 0 and olc_t > dbg_t * 3:
        notes.append(
            f"⏱️ DBG nhanh hơn OLC ~{olc_t/dbg_t:.1f}× — "
            "nhất quán với độ phức tạp O(n) thay vì O(n²·m²) khi tính overlap từng cặp."
        )
    elif olc_t > 0 and dbg_t > olc_t * 1.5:
        notes.append(
            f"⏱️ Bất ngờ: DBG chậm hơn OLC ~{dbg_t/olc_t:.1f}× — "
            "thường do k cao tạo ít k-mer hữu ích hoặc số reads quá nhỏ."
        )

    if olc_edges > dbg_edges * 2 and olc_edges > 0:
        notes.append(
            f"🕸️ Đồ thị OLC dày hơn DBG ({olc_edges} vs {dbg_edges} cạnh) — "
            "OLC so từng cặp reads, DBG gom k-mer trùng nên cấu trúc gọn hơn."
        )
    elif dbg_edges > olc_edges * 2 and dbg_edges > 0:
        notes.append(
            f"🕸️ Đồ thị DBG có nhiều cạnh hơn OLC ({dbg_edges} vs {olc_edges}) — "
            "thường xảy ra khi k nhỏ, mỗi read sinh nhiều k-mer."
        )

    if olc_acc - dbg_acc >= 5:
        notes.append(
            f"🎯 OLC khôi phục đầy đủ hơn (+{olc_acc - dbg_acc:.1f}%) — "
            "có thể k đang lớn so với read length, làm DBG mất k-mer hữu ích."
        )
    elif dbg_acc - olc_acc >= 5:
        notes.append(
            f"🎯 DBG khôi phục đầy đủ hơn (+{dbg_acc - olc_acc:.1f}%) — "
            "có thể min_overlap quá khắt khe, làm OLC bỏ qua nhiều cạnh hợp lệ."
        )
    elif abs(olc_acc - dbg_acc) < 3:
        notes.append(
            "🎯 Hai thuật toán khôi phục tương đương — "
            "trong điều kiện 'lý tưởng' khác biệt chủ yếu nằm ở chi phí tính toán."
        )

    if not notes:
        return

    with st.container(border=True):
        st.markdown("**🔎 Nhận xét tự động**")
        for n in notes:
            st.markdown(f"- {n}")


def _complexity_label(name: str) -> str:
    """Nhãn độ phức tạp lý thuyết."""
    if name == "OLC":
        return "O(n²·m²)"
    return "O(n·m + V+E)"


def _graph_stats(name: str):
    """(num_nodes, num_edges) cho thuật toán."""
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


def _format_time(ms: float) -> str:
    """Format thời gian: <1ms hiện μs, <1000ms hiện ms, >=1000ms hiện s."""
    if ms <= 0:
        return "—"
    if ms < 1:
        return f"{ms * 1000:.0f} μs"
    if ms < 1000:
        return f"{ms:.1f} ms"
    return f"{ms / 1000:.2f} s"
