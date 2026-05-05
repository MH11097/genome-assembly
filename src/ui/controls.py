"""
Sidebar controls cho Streamlit app.

Bao gồm:
- Genome input (thủ công, ngẫu nhiên, virus examples)
- Read parameters (length, coverage)
- Algorithm selection (OLC, DBG, compare)
- Run button
"""

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

    _render_genome_input()

    _render_read_params()

    _render_algorithm_selection()

    _render_run_button()


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
        use_repeats = st.sidebar.checkbox("Có vùng lặp lại (repeat)")

        if st.sidebar.button("🎲 Tạo genome", use_container_width=True):
            gen = GenomeGenerator()
            if use_repeats:
                st.session_state.genome = gen.generate_with_repeats(
                    length, repeat_unit="ATATAT", num_copies=3
                )
            else:
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
        "Độ dài read (bp):", 10, 100, 50, 5
    )

    st.session_state.coverage = st.sidebar.slider(
        "Độ phủ (coverage):", 3, 30, 15
    )

    # Warning for low coverage
    if st.session_state.coverage < 10:
        st.sidebar.warning("⚠️ Coverage thấp (<10x) có thể cho kết quả kém")

    # Estimate reads count
    if st.session_state.genome:
        est_reads = (len(st.session_state.genome) * st.session_state.coverage) // st.session_state.read_length
        st.sidebar.caption(f"~{est_reads} reads sẽ được tạo")


def _render_algorithm_selection():
    """Section chọn thuật toán."""
    st.sidebar.subheader("🔬 Thuật toán")

    st.session_state.algorithm = st.sidebar.radio(
        "Chọn:",
        ["OLC", "DBG", "So sánh cả hai"],
        horizontal=True
    )

    # OLC params
    if st.session_state.algorithm in ["OLC", "So sánh cả hai"]:
        st.session_state.min_overlap = st.sidebar.slider(
            "Min overlap (OLC):", 3, 20, 5
        )
        # Warning for aggressive overlap
        if st.session_state.min_overlap > st.session_state.read_length * 0.25:
            st.sidebar.warning(f"⚠️ Min overlap cao (>{st.session_state.read_length * 0.25:.0f}bp) có thể tạo đồ thị thưa")

    # DBG params
    if st.session_state.algorithm in ["DBG", "So sánh cả hai"]:
        st.session_state.k_value = st.sidebar.slider(
            "Giá trị k (DBG):", 5, 21, 7, 2
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
            fragmenter = ReadFragmenter()
            st.session_state.reads = fragmenter.fragment(
                genome,
                st.session_state.read_length,
                st.session_state.coverage
            )

        algo = st.session_state.algorithm

        # Run OLC
        if algo in ["OLC", "So sánh cả hai"]:
            with st.spinner("Đang chạy OLC..."):
                olc = OLCAssembler(
                    st.session_state.reads,
                    min_overlap=st.session_state.min_overlap
                )
                st.session_state.olc_result = olc.assemble()
                st.session_state.olc_assembler = olc

        # Run DBG
        if algo in ["DBG", "So sánh cả hai"]:
            with st.spinner("Đang chạy DBG..."):
                dbg = DBGAssembler(
                    st.session_state.reads,
                    k=st.session_state.k_value
                )
                st.session_state.dbg_result = dbg.assemble()
                st.session_state.dbg_assembler = dbg

        # Setup animation controller
        if algo == "OLC" and st.session_state.olc_assembler:
            states = st.session_state.olc_assembler.get_step_states()
            st.session_state.animation_controller = AnimationController(states)
        elif algo == "DBG" and st.session_state.dbg_assembler:
            states = st.session_state.dbg_assembler.get_step_states()
            st.session_state.animation_controller = AnimationController(states)
        elif algo == "So sánh cả hai" and st.session_state.olc_assembler:
            states = st.session_state.olc_assembler.get_step_states()
            st.session_state.animation_controller = AnimationController(states)

        st.session_state.assembly_done = True
        st.success("✅ Hoàn thành!")
        st.rerun()
