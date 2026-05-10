#!/usr/bin/env python3
"""
Demo Lắp Ráp Genome - Main Streamlit Application

Ứng dụng giáo dục minh họa 2 thuật toán genome assembly:
- OLC (Overlap-Layout-Consensus) - đường đi Hamilton
- DBG (de Bruijn Graph) - đường đi Euler
"""

import streamlit as st
from src.ui.controls import render_sidebar
from src.ui.sections import (
    render_fragmentation_section,
    render_assembly_section,
    render_results_section
)

# Page config
st.set_page_config(
    page_title="Demo Lắp Ráp Genome",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """Khởi tạo session state variables."""
    defaults = {
        'genome': '',
        'reads': [],
        'algorithm': 'OLC',
        'read_length': 50,
        'coverage': 0,  # dẫn xuất tại runtime, chỉ giữ để hiển thị
        'min_overlap': 10,
        'k_value': 11,
        'olc_assembler': None,
        'dbg_assembler': None,
        'olc_result': '',
        'dbg_result': '',
        'olc_time_ms': 0.0,
        'dbg_time_ms': 0.0,
        'olc_animation_controller': None,
        'dbg_animation_controller': None,
        'step_index': 0,
        'assembly_done': False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def main():
    """Main application entry point."""
    init_session_state()

    # Header
    st.title("🧬 Demo Lắp Ráp Genome")
    st.markdown("*Minh họa thuật toán OLC (Hamilton) và de Bruijn Graph (Euler)*")

    # Sidebar controls
    render_sidebar()

    # === SECTION 1: Phân mảnh ===
    render_fragmentation_section()

    # === SECTION 2: Assembly (Thuật toán + Đồ thị) ===
    st.divider()
    render_assembly_section()

    # === SECTION 3: Kết quả (chỉ hiển thị khi assembly xong) ===
    if st.session_state.assembly_done:
        st.divider()
        render_results_section()

    # Footer
    st.divider()
    st.caption("🎓 Ứng dụng giáo dục - Demo genome assembly algorithms")


if __name__ == "__main__":
    main()
