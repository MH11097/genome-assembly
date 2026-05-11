"""
Spotlight onboarding overlay — chạy 1 lần khi user mở app lần đầu.

Khác biệt với Guided Tour cũ:
- Không có "mode" cần bật/tắt; tự động hiện ở lần đầu, dismiss = tắt vĩnh viễn (localStorage)
- Dim toàn màn hình + cutout quanh phần đang giới thiệu + tooltip có Next/Prev/Skip
- Toàn bộ logic chạy client-side trong components.html iframe, inject DOM vào parent
- Phục hồi đúng step khi Streamlit rerun (lưu current step trong localStorage)

5 steps mặc định:
1. Welcome (center)
2. Sidebar: Genome đầu vào
3. Sidebar: Tham số đọc + Thuật toán
4. Sidebar: Nút Chạy lắp ráp
5. Main: Vùng Phân mảnh + Assembly + Kết quả
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import streamlit as st
import streamlit.components.v1 as components


SPOTLIGHT_STEPS: List[Dict[str, Any]] = [
    {
        'title': '👋 Chào mừng đến với Demo Lắp Ráp Genome',
        'body': (
            'Demo này giúp bạn hiểu trực quan hai thuật toán genome assembly: '
            '<b>OLC</b> (Overlap-Layout-Consensus) và <b>DBG</b> (de Bruijn Graph). '
            'Mình sẽ dẫn bạn qua 4 khu vực chính trong 20 giây.'
        ),
        'target_text': None,
        'placement': 'center',
    },
    {
        'title': '🧬 1. Nhập genome (sidebar)',
        'body': (
            'Bắt đầu ở đây. Chọn cách lấy genome đầu vào: '
            '<b>Tạo ngẫu nhiên</b> (kiểm soát độ dài), '
            '<b>Ví dụ virus</b> (genome thật), hoặc '
            '<b>Nhập thủ công</b> (dán chuỗi A/T/G/C).'
        ),
        'target_text': 'Genome đầu vào',
        'target_in': '[data-testid="stSidebar"]',
        'placement': 'right',
    },
    {
        'title': '⚙️ 2. Tham số read + thuật toán',
        'body': (
            '<b>Độ dài read</b>: số bp mỗi mảnh (coverage tự động ~80 reads). '
            'Chọn <b>OLC</b>, <b>DBG</b>, hoặc <b>So sánh cả hai</b>. '
            'Mỗi thuật toán có tham số riêng (min_overlap / k).'
        ),
        'target_text': 'Thuật toán',
        'target_in': '[data-testid="stSidebar"]',
        'placement': 'right',
    },
    {
        'title': '▶️ 3. Chạy lắp ráp',
        'body': (
            'Bấm nút này để chạy thuật toán và sinh dữ liệu step-by-step. '
            'Bạn có thể chạy nhiều lần với tham số khác nhau để so sánh.'
        ),
        'target_text': 'Chạy lắp ráp',
        'target_in': '[data-testid="stSidebar"]',
        'placement': 'right',
    },
    {
        'title': '📋 4. Khu vực Phân mảnh',
        'body': (
            'Genome gốc + <b>Coverage Map</b> hiển thị reads xếp tại vị trí gốc. '
            'Vùng đỏ = coverage thấp → khả năng cao là gap khi assembly.'
        ),
        'target_text': 'Phân mảnh Genome',
        'placement': 'bottom',
    },
    {
        'title': '🔬 5. Khu vực Assembly từng bước',
        'body': (
            'Sau khi chạy: <b>Code trace</b> (pseudocode highlight dòng), '
            '<b>Đồ thị động</b> (cập nhật theo step), '
            'và <b>Action View</b> (cơ chế cụ thể của từng phase).'
        ),
        'target_text': 'Assembly từng bước',
        'placement': 'bottom',
    },
    {
        'title': '📊 6. Khu vực Kết quả',
        'body': (
            'Sau khi chạy: metrics tổng và <b>Phase Timeline</b> '
            '(so sánh thời gian từng phase giữa OLC vs DBG).'
        ),
        'target_text': 'Assembly từng bước',  # placeholder — Section 3 chưa render khi chưa chạy
        'placement': 'bottom',
    },
    {
        'title': '✓ Sẵn sàng!',
        'body': (
            'Bạn đã xem xong các khu vực chính. Bắt đầu bằng cách chọn genome ở '
            'sidebar bên trái và bấm <b>Chạy lắp ráp</b>. '
            'Mở lại spotlight bất cứ lúc nào bằng menu ⋯ ở góc phải.'
        ),
        'target_text': None,
        'placement': 'center',
    },
]


_OVERLAY_CSS = """
#gas-spotlight-backdrop {
    position: fixed; inset: 0;
    background: rgba(15, 23, 42, 0.62);
    z-index: 999998;
    pointer-events: auto;
    transition: clip-path 0.3s ease;
}
#gas-spotlight-tooltip {
    position: fixed;
    z-index: 999999;
    background: #ffffff;
    color: #1f2933;
    border-radius: 10px;
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.32),
                0 0 0 3px rgba(255, 193, 7, 0.45);
    padding: 18px 22px 14px 22px;
    width: 360px;
    max-width: calc(100vw - 32px);
    font-family: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
}
#gas-spotlight-tooltip .gas-title {
    font-size: 15px; font-weight: 700;
    color: #0f172a;
    margin-bottom: 8px;
}
#gas-spotlight-tooltip .gas-body {
    font-size: 13px; line-height: 1.55;
    color: #334155;
    margin-bottom: 14px;
}
#gas-spotlight-tooltip .gas-body b { color: #0f172a; }
#gas-spotlight-tooltip .gas-footer {
    display: flex; align-items: center; gap: 8px;
    padding-top: 10px;
    border-top: 1px solid #f1f5f9;
}
#gas-spotlight-tooltip .gas-progress {
    font-size: 11px; color: #94a3b8; flex: 1;
}
#gas-spotlight-tooltip button {
    border: 0; cursor: pointer; border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px; font-weight: 600;
    font-family: inherit;
    transition: filter 0.15s;
}
#gas-spotlight-tooltip button:hover { filter: brightness(0.92); }
#gas-spotlight-tooltip button:disabled { opacity: 0.4; cursor: not-allowed; }
#gas-spotlight-tooltip .gas-skip {
    background: transparent; color: #64748b;
}
#gas-spotlight-tooltip .gas-prev {
    background: #e2e8f0; color: #334155;
}
#gas-spotlight-tooltip .gas-next {
    background: #f59e0b; color: white;
}
#gas-spotlight-tooltip .gas-arrow {
    position: absolute;
    width: 14px; height: 14px;
    background: white;
    transform: rotate(45deg);
    box-shadow: -2px -2px 4px rgba(0,0,0,0.06);
}
#gas-spotlight-tooltip[data-placement="right"] .gas-arrow {
    left: -7px; top: 24px;
}
#gas-spotlight-tooltip[data-placement="bottom"] .gas-arrow {
    top: -7px; left: 36px;
}
#gas-spotlight-tooltip[data-placement="center"] .gas-arrow { display: none; }
"""


def _build_overlay_html() -> str:
    steps_json = json.dumps(SPOTLIGHT_STEPS, ensure_ascii=False)
    css = _OVERLAY_CSS

    # Note: parent DOM mutation - chạy trong iframe của components.html nhưng
    # inject vào window.parent.document để overlay nằm trên Streamlit chính.
    return f"""
<style>{css}</style>
<div id="gas-spotlight-anchor" style="display:none"></div>
<script>
(function() {{
    const STEPS = {steps_json};
    const STORAGE_KEY = 'gas_spotlight_v2';
    const parentDoc = window.parent.document;
    const parentWin = window.parent;

    let saved;
    try {{ saved = parentWin.localStorage.getItem(STORAGE_KEY); }} catch(e) {{ saved = null; }}
    if (saved === 'done') return;

    let current = 0;
    try {{
        const idx = parseInt(parentWin.localStorage.getItem(STORAGE_KEY + '_step') || '0', 10);
        if (!isNaN(idx)) current = Math.min(Math.max(0, idx), STEPS.length - 1);
    }} catch(e) {{}}

    // Inject CSS into parent document (only once)
    if (!parentDoc.getElementById('gas-spotlight-css')) {{
        const style = parentDoc.createElement('style');
        style.id = 'gas-spotlight-css';
        style.textContent = `{css}`;
        parentDoc.head.appendChild(style);
    }}

    // Remove any prior overlay (Streamlit reruns recreate the iframe)
    ['gas-spotlight-backdrop', 'gas-spotlight-tooltip'].forEach(id => {{
        const el = parentDoc.getElementById(id);
        if (el) el.remove();
    }});

    // Backdrop with cutout (via clip-path)
    const backdrop = parentDoc.createElement('div');
    backdrop.id = 'gas-spotlight-backdrop';
    parentDoc.body.appendChild(backdrop);

    // Tooltip
    const tip = parentDoc.createElement('div');
    tip.id = 'gas-spotlight-tooltip';
    tip.innerHTML = `
        <div class="gas-arrow"></div>
        <div class="gas-title"></div>
        <div class="gas-body"></div>
        <div class="gas-footer">
            <span class="gas-progress"></span>
            <button class="gas-skip" type="button">Bỏ qua</button>
            <button class="gas-prev" type="button">◀ Trước</button>
            <button class="gas-next" type="button">Tiếp ▶</button>
        </div>
    `;
    parentDoc.body.appendChild(tip);

    function persist() {{
        try {{ parentWin.localStorage.setItem(STORAGE_KEY + '_step', String(current)); }} catch(e) {{}}
    }}

    function finish() {{
        try {{ parentWin.localStorage.setItem(STORAGE_KEY, 'done'); }} catch(e) {{}}
        try {{ parentWin.localStorage.removeItem(STORAGE_KEY + '_step'); }} catch(e) {{}}
        backdrop.remove(); tip.remove();
        parentWin.removeEventListener('resize', renderStep);
        parentWin.removeEventListener('scroll', renderStep, true);
    }}

    function findTarget(step) {{
        if (!step.target_text) return null;
        let scope = parentDoc;
        if (step.target_in) {{
            scope = parentDoc.querySelector(step.target_in);
            if (!scope) return null;
        }}
        // Match in headers/labels/buttons by inclusion of text
        const tags = ['h1', 'h2', 'h3', 'h4', 'label', 'button', 'p'];
        for (const t of tags) {{
            const els = scope.querySelectorAll(t);
            for (const el of els) {{
                if ((el.textContent || '').trim().includes(step.target_text)) {{
                    return el;
                }}
            }}
        }}
        return null;
    }}

    function setCutout(rect) {{
        if (!rect) {{
            backdrop.style.clipPath = '';
            return;
        }}
        const pad = 8;
        const r = {{
            x: Math.max(0, rect.left - pad),
            y: Math.max(0, rect.top - pad),
            w: rect.width + 2 * pad,
            h: rect.height + 2 * pad,
        }};
        // even-odd clip-path: full screen minus the rectangle
        const path = `polygon(
            0 0, 100vw 0, 100vw 100vh, 0 100vh, 0 0,
            ${{r.x}}px ${{r.y}}px,
            ${{r.x}}px ${{r.y + r.h}}px,
            ${{r.x + r.w}}px ${{r.y + r.h}}px,
            ${{r.x + r.w}}px ${{r.y}}px,
            ${{r.x}}px ${{r.y}}px
        )`;
        backdrop.style.clipPath = path;
    }}

    function placeTooltip(targetRect, placement) {{
        const margin = 18;
        tip.dataset.placement = placement;
        let top, left;
        if (placement === 'center' || !targetRect) {{
            top = (parentWin.innerHeight - tip.offsetHeight) / 2;
            left = (parentWin.innerWidth - tip.offsetWidth) / 2;
        }} else if (placement === 'right') {{
            top = Math.max(16, targetRect.top);
            left = targetRect.right + margin;
            // If overflowing right edge, fall back to below
            if (left + tip.offsetWidth > parentWin.innerWidth - 16) {{
                placement = 'bottom';
                tip.dataset.placement = 'bottom';
                top = targetRect.bottom + margin;
                left = Math.max(16, targetRect.left);
            }}
        }} else {{ // bottom
            top = targetRect.bottom + margin;
            left = Math.max(16, targetRect.left);
            if (top + tip.offsetHeight > parentWin.innerHeight - 16) {{
                // try above instead
                top = Math.max(16, targetRect.top - tip.offsetHeight - margin);
            }}
        }}
        // Clamp horizontally
        left = Math.min(left, parentWin.innerWidth - tip.offsetWidth - 16);
        left = Math.max(16, left);
        tip.style.top = top + 'px';
        tip.style.left = left + 'px';
    }}

    function scrollIntoView(target) {{
        if (!target) return;
        const rect = target.getBoundingClientRect();
        if (rect.top < 60 || rect.bottom > parentWin.innerHeight - 60) {{
            target.scrollIntoView({{behavior: 'smooth', block: 'center'}});
        }}
    }}

    function renderStep() {{
        const step = STEPS[current];
        tip.querySelector('.gas-title').innerHTML = step.title;
        tip.querySelector('.gas-body').innerHTML = step.body;
        tip.querySelector('.gas-progress').textContent = `${{current + 1}} / ${{STEPS.length}}`;
        tip.querySelector('.gas-prev').disabled = (current === 0);
        tip.querySelector('.gas-next').textContent = (current === STEPS.length - 1) ? 'Xong ✓' : 'Tiếp ▶';

        const target = findTarget(step);
        if (target) scrollIntoView(target);
        // Re-measure after potential scroll, on next frame
        parentWin.requestAnimationFrame(() => {{
            const rect = target ? target.getBoundingClientRect() : null;
            setCutout(rect);
            placeTooltip(rect, step.placement || 'right');
        }});
    }}

    tip.querySelector('.gas-next').addEventListener('click', () => {{
        if (current < STEPS.length - 1) {{
            current += 1; persist(); renderStep();
        }} else {{
            finish();
        }}
    }});
    tip.querySelector('.gas-prev').addEventListener('click', () => {{
        if (current > 0) {{ current -= 1; persist(); renderStep(); }}
    }});
    tip.querySelector('.gas-skip').addEventListener('click', finish);

    parentWin.addEventListener('resize', renderStep);
    parentWin.addEventListener('scroll', renderStep, true);

    // Initial render after Streamlit's layout settles
    setTimeout(renderStep, 250);
}})();
</script>
"""


def render_spotlight():
    """Emit spotlight overlay (chỉ chạy thực sự lần đầu — localStorage gate)."""
    # Cờ Python để force replay (?spotlight=replay trong URL)
    try:
        qp = st.query_params
        if qp.get('spotlight') == 'replay':
            # Xoá localStorage flag bằng cách inject JS
            components.html(
                """
                <script>
                try {
                    window.parent.localStorage.removeItem('gas_spotlight_v2');
                    window.parent.localStorage.removeItem('gas_spotlight_v2_step');
                    const url = new URL(window.parent.location);
                    url.searchParams.delete('spotlight');
                    window.parent.history.replaceState({}, '', url);
                    window.parent.location.reload();
                } catch(e) {}
                </script>
                """,
                height=0,
            )
            return
    except Exception:
        pass

    components.html(_build_overlay_html(), height=0, scrolling=False)


def render_replay_button():
    """Nút phụ ở sidebar cho phép user mở lại spotlight."""
    if st.sidebar.button("❓ Hướng dẫn lại", use_container_width=True,
                          help="Mở lại spotlight giới thiệu"):
        components.html(
            """
            <script>
            try {
                window.parent.localStorage.removeItem('gas_spotlight_v2');
                window.parent.localStorage.removeItem('gas_spotlight_v2_step');
                window.parent.location.reload();
            } catch(e) {}
            </script>
            """,
            height=0,
        )
