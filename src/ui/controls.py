"""
Sidebar controls cho Streamlit app.

Bao gồm:
- Genome input (thủ công, ngẫu nhiên, virus examples)
- Read parameters (length, coverage)
- Algorithm selection (OLC, DBG, compare)
- Run button
"""

import time
import streamlit as st
from src.genome.generator import GenomeGenerator
from src.genome.fragmenter import ReadFragmenter
from src.genome.validator import validate_dna, clean_sequence
from src.assembly.olc import OLCAssembler
from src.assembly.dbg import DBGAssembler
from src.visualization.animator import AnimationController


def render_sidebar():
    """Render toàn bộ sidebar controls."""
    # Custom CSS để giảm khoảng cách trong sidebar - phiên bản thu gọn tối đa
    st.markdown("""
        <style>
        /* Giảm padding tổng thể của sidebar */
        [data-testid="stSidebar"] > div:first-child {
            padding-top: 0.5rem;
            padding-bottom: 0.5rem;
        }
        
        /* Giảm mạnh khoảng cách giữa các phần tử trong sidebar */
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] .stRadio,
        [data-testid="stSidebar"] .stSelectbox,
        [data-testid="stSidebar"] .stSlider,
        [data-testid="stSidebar"] .stCheckbox,
        [data-testid="stSidebar"] .stButton,
        [data-testid="stSidebar"] .stTextArea {
            margin-bottom: 0rem !important;
            margin-top: 0rem !important;
        }
        
        /* Giảm khoảng cách của subheader */
        [data-testid="stSidebar"] h3 {
            margin-top: 0.3rem !important;
            margin-bottom: 0.1rem !important;
            font-size: 0.9rem !important;
            padding: 0 !important;
        }
        
        /* Giảm khoảng cách của header chính */
        [data-testid="stSidebar"] h2 {
            margin-bottom: 0.2rem !important;
            margin-top: 0 !important;
            font-size: 1rem !important;
        }
        
        /* Ẩn hoàn toàn divider */
        [data-testid="stSidebar"] hr {
            display: none !important;
        }
        
        /* Thu gọn alert/info box */
        [data-testid="stSidebar"] .stAlert {
            padding: 0.3rem 0.5rem !important;
            margin: 0.1rem 0 !important;
        }
        [data-testid="stSidebar"] .stAlert p {
            font-size: 0.8rem !important;
            margin: 0 !important;
        }
        
        /* Thu gọn radio button layout */
        [data-testid="stSidebar"] .stRadio > div {
            gap: 0.1rem !important;
        }
        [data-testid="stSidebar"] .stRadio label {
            font-size: 0.8rem !important;
            padding: 0.1rem 0.3rem !important;
        }
        
        /* Giảm kích thước label */
        [data-testid="stSidebar"] .stSlider > label,
        [data-testid="stSidebar"] .stSelectbox > label,
        [data-testid="stSidebar"] .stTextArea > label,
        [data-testid="stSidebar"] .stCheckbox > label {
            font-size: 0.8rem !important;
        }
        
        /* Thu gọn slider */
        [data-testid="stSidebar"] .stSlider {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        [data-testid="stSidebar"] .stSlider > div {
            padding-bottom: 0.2rem !important;
        }
        
        /* Thu gọn button */
        [data-testid="stSidebar"] .stButton > button {
            padding: 0.3rem 0.5rem !important;
            font-size: 0.85rem !important;
        }
        
        /* Thu gọn text area */
        [data-testid="stSidebar"] .stTextArea textarea {
            min-height: 60px !important;
        }
        
        /* Thu gọn selectbox */
        [data-testid="stSidebar"] .stSelectbox > div {
            margin-bottom: 0 !important;
        }
        
        /* Thu gọn caption */
        [data-testid="stSidebar"] .stCaption {
            font-size: 0.7rem !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        
        /* Ẩn các element container spacing */
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {
            gap: 0.2rem !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.sidebar.header("⚙️ Điều khiển")

    _render_presets()

    _render_genome_input()

    _render_read_params()

    _render_algorithm_selection()

    _render_run_button()


# Mỗi preset là một dict tham số nhằm minh hoạ một góc nhìn so sánh OLC vs DBG.
_PRESETS = {
    "⚖️ Cân bằng": {
        "read_length": 50, "coverage": 15,
        "min_overlap": 10, "k_value": 9,
        "_hint": "Cả hai cùng tốt → so sánh runtime O(n²) vs O(n)"
    },
    "🔬 Reads ngắn, k thấp": {
        "read_length": 20, "coverage": 20,
        "min_overlap": 5, "k_value": 5,
        "_hint": "DBG gom k-mer mật độ cao; OLC graph dày"
    },
    "📏 Reads dài": {
        "read_length": 120, "coverage": 8,
        "min_overlap": 30, "k_value": 15,
        "_hint": "OLC overlap dài, đồ thị thưa; DBG cần k cao"
    },
    "🌊 Coverage cao": {
        "read_length": 50, "coverage": 30,
        "min_overlap": 10, "k_value": 9,
        "_hint": "OLC bùng nổ overlap; DBG ổn định nhờ dedup"
    },
}


def _render_presets():
    """4 preset 1-click để load nhanh kịch bản so sánh."""
    st.sidebar.subheader("🎯 Preset so sánh")
    cols = st.sidebar.columns(2)
    items = list(_PRESETS.items())
    for i, (name, params) in enumerate(items):
        with cols[i % 2]:
            if st.button(name, key=f"preset_{i}", use_container_width=True,
                         help=params.get("_hint", "")):
                for k, v in params.items():
                    if k.startswith("_"):
                        continue
                    st.session_state[k] = v
                st.session_state.assembly_done = False
                st.rerun()


def _render_genome_input():
    """Section nhập genome."""
    st.sidebar.subheader("🧬 Genome đầu vào")

    input_method = st.sidebar.radio(
        "Phương thức:",
        ["Tạo ngẫu nhiên", "Ví dụ virus", "Nhập thủ công"],
        horizontal=True
    )

    if input_method == "Nhập thủ công":
        genome_input = st.sidebar.text_area(
            "Chuỗi DNA (A, T, G, C):",
            height=80,
            placeholder="VD: ATCGATCGATCG..."
        )
        if genome_input:
            cleaned = clean_sequence(genome_input)
            if validate_dna(cleaned):
                st.session_state.genome = cleaned
                st.sidebar.success(f"✅ {len(cleaned)} bp")
            else:
                st.sidebar.error("⚠️ Chuỗi không hợp lệ!")

    elif input_method == "Tạo ngẫu nhiên":
        length = st.sidebar.slider("Độ dài (bp):", 50, 2000, 300, 50)

        if st.sidebar.button("🎲 Tạo genome", use_container_width=True):
            gen = GenomeGenerator()
            st.session_state.genome = gen.generate_random(length)
            st.session_state.assembly_done = False
            st.rerun()

    else:  # Virus examples
        gen = GenomeGenerator()
        virus_names = gen.get_virus_names()
        selected = st.sidebar.selectbox("Chọn virus:", virus_names)

        if st.sidebar.button("📥 Tải genome", use_container_width=True):
            st.session_state.genome = gen.load_virus_example(selected)
            st.session_state.assembly_done = False
            st.rerun()

    # Display genome info
    if st.session_state.genome:
        st.sidebar.info(f"📏 Genome hiện tại: **{len(st.session_state.genome)} bp**")


def _render_read_params():
    """Section tham số read."""
    st.sidebar.subheader("📖 Tham số đọc")

    st.session_state.read_length = st.sidebar.slider(
        "Độ dài read (bp):", 10, 200,
        value=int(st.session_state.get("read_length", 50)), step=5
    )

    st.session_state.coverage = st.sidebar.slider(
        "Độ phủ (coverage):", 3, 30,
        value=int(st.session_state.get("coverage", 15))
    )

    # Warning for low coverage
    if st.session_state.coverage < 10:
        st.sidebar.warning("⚠️ Coverage thấp (<10x) có thể cho kết quả kém")

    st.session_state.random_seed = st.sidebar.number_input(
        "Random seed (reproducible):",
        min_value=0, max_value=999999,
        value=st.session_state.get('random_seed', 42),
        step=1,
        help="Cùng seed → cùng reads. Đổi seed để thử cấu hình ngẫu nhiên khác."
    )

    # Estimate reads count
    if st.session_state.genome:
        est_reads = (len(st.session_state.genome) * st.session_state.coverage) // st.session_state.read_length
        st.sidebar.caption(f"~{est_reads} reads sẽ được tạo")


def _render_algorithm_selection():
    """Section chọn thuật toán."""
    st.sidebar.subheader("🔬 Thuật toán")

    algo_options = ["OLC", "DBG", "So sánh cả hai"]
    current_algo = st.session_state.get("algorithm", "OLC")
    algo_idx = algo_options.index(current_algo) if current_algo in algo_options else 0
    st.session_state.algorithm = st.sidebar.radio(
        "Chọn:",
        algo_options,
        index=algo_idx,
        horizontal=True
    )

    # OLC params
    if st.session_state.algorithm in ["OLC", "So sánh cả hai"]:
        st.session_state.min_overlap = st.sidebar.slider(
            "Min overlap (OLC):", 3, 80,
            value=int(st.session_state.get("min_overlap", 5))
        )
        # Warning for aggressive overlap
        if st.session_state.min_overlap > st.session_state.read_length * 0.25:
            st.sidebar.warning(f"⚠️ Min overlap cao (>{st.session_state.read_length * 0.25:.0f}bp) có thể tạo đồ thị thưa")

    # DBG params
    if st.session_state.algorithm in ["DBG", "So sánh cả hai"]:
        st.session_state.k_value = st.sidebar.slider(
            "Giá trị k (DBG):", 5, 31,
            value=int(st.session_state.get("k_value", 7)), step=2
        )
        # Warning for k too high
        if st.session_state.k_value > st.session_state.read_length / 3:
            st.sidebar.warning(f"⚠️ k cao (>{st.session_state.read_length // 3}) cần coverage cao hơn")


def _render_run_button():
    """Nút chạy assembly."""
    if st.sidebar.button(
        "▶️ Chạy lắp ráp",
        type="primary",
        use_container_width=True,
        disabled=not st.session_state.genome
    ):
        _run_assembly()


def _run_assembly():
    """Execute assembly pipeline."""
    genome = st.session_state.genome
    if not genome:
        st.sidebar.error("⚠️ Chưa có genome!")
        return

    with st.sidebar:
        with st.spinner("Đang phân mảnh..."):
            # Fragment genome
            fragmenter = ReadFragmenter(seed=st.session_state.random_seed)
            st.session_state.reads = fragmenter.fragment(
                genome,
                st.session_state.read_length,
                st.session_state.coverage
            )

        algo = st.session_state.algorithm

        # Reset times
        st.session_state.olc_time_ms = 0.0
        st.session_state.dbg_time_ms = 0.0

        # Run OLC
        if algo in ["OLC", "So sánh cả hai"]:
            with st.spinner("Đang chạy OLC..."):
                olc = OLCAssembler(
                    st.session_state.reads,
                    min_overlap=st.session_state.min_overlap
                )
                t0 = time.perf_counter()
                st.session_state.olc_result = olc.assemble()
                st.session_state.olc_time_ms = (time.perf_counter() - t0) * 1000
                st.session_state.olc_assembler = olc

        # Run DBG
        if algo in ["DBG", "So sánh cả hai"]:
            with st.spinner("Đang chạy DBG..."):
                dbg = DBGAssembler(
                    st.session_state.reads,
                    k=st.session_state.k_value
                )
                t0 = time.perf_counter()
                st.session_state.dbg_result = dbg.assemble()
                st.session_state.dbg_time_ms = (time.perf_counter() - t0) * 1000
                st.session_state.dbg_assembler = dbg

        # Setup animation controllers (mỗi thuật toán 1 controller riêng để
        # compare mode hiển thị 2 tab độc lập)
        st.session_state.olc_animation_controller = None
        st.session_state.dbg_animation_controller = None
        if st.session_state.olc_assembler:
            st.session_state.olc_animation_controller = AnimationController(
                st.session_state.olc_assembler.get_step_states()
            )
        if st.session_state.dbg_assembler:
            st.session_state.dbg_animation_controller = AnimationController(
                st.session_state.dbg_assembler.get_step_states()
            )

        st.session_state.assembly_done = True
        st.success("✅ Hoàn thành!")
        st.rerun()
