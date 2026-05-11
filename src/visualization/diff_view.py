"""
Diff View (View 7): so sánh chuỗi assembled vs original character-by-character.

Dùng Needleman-Wunsch alignment đơn giản (chỉ match/mismatch/gap)
để xếp 2 chuỗi và highlight chính xác chỗ insertion/deletion thay vì
chỉ shift bằng best-offset.
"""

from __future__ import annotations

from typing import List, Tuple


def _align(ref: str, query: str, match: int = 2, mismatch: int = -1,
            gap: int = -2) -> Tuple[str, str]:
    """
    Needleman-Wunsch global alignment.
    Trả về (ref_aligned, query_aligned) với '-' cho gap.

    Chỉ chạy được trên chuỗi ≤ ~2000 bp (đủ cho demo).
    Nếu input quá dài: fallback chỉ trả về best-offset alignment.
    """
    n, m = len(ref), len(query)
    if n == 0 and m == 0:
        return "", ""
    if max(n, m) > 1500:
        return _best_offset_align(ref, query)

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = gap * i
    for j in range(m + 1):
        dp[0][j] = gap * j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sc = match if ref[i - 1] == query[j - 1] else mismatch
            dp[i][j] = max(
                dp[i - 1][j - 1] + sc,
                dp[i - 1][j] + gap,
                dp[i][j - 1] + gap,
            )

    # traceback
    ra, qa = [], []
    i, j = n, m
    while i > 0 and j > 0:
        sc = match if ref[i - 1] == query[j - 1] else mismatch
        if dp[i][j] == dp[i - 1][j - 1] + sc:
            ra.append(ref[i - 1]); qa.append(query[j - 1])
            i -= 1; j -= 1
        elif dp[i][j] == dp[i - 1][j] + gap:
            ra.append(ref[i - 1]); qa.append('-')
            i -= 1
        else:
            ra.append('-'); qa.append(query[j - 1])
            j -= 1
    while i > 0:
        ra.append(ref[i - 1]); qa.append('-'); i -= 1
    while j > 0:
        ra.append('-'); qa.append(query[j - 1]); j -= 1
    return ''.join(reversed(ra)), ''.join(reversed(qa))


def _best_offset_align(ref: str, query: str) -> Tuple[str, str]:
    """Fallback alignment cho chuỗi quá dài để NW."""
    best_off, best_score = 0, -1
    for off in range(-min(50, len(query)), min(50, len(ref)) + 1):
        score = 0
        for k in range(max(0, off), min(len(ref), off + len(query))):
            if ref[k] == query[k - off]:
                score += 1
        if score > best_score:
            best_score = score
            best_off = off
    ra = ('-' * max(0, -best_off)) + ref + ('-' * max(0, len(query) + best_off - len(ref)))
    qa = ('-' * max(0, best_off)) + query + ('-' * max(0, len(ref) - best_off - len(query)))
    width = max(len(ra), len(qa))
    return ra.ljust(width, '-'), qa.ljust(width, '-')


def render_diff_html(reference: str, assembled: str, *, max_per_row: int = 80) -> str:
    """
    HTML diff view. Mỗi cột:
      - xanh nếu match
      - đỏ nếu mismatch
      - xám nhạt nếu gap ('-')
    Có chunked layout: mỗi hàng max_per_row ký tự.
    """
    ref_a, qry_a = _align(reference, assembled)
    width = max(len(ref_a), len(qry_a))
    ref_a = ref_a.ljust(width, '-')
    qry_a = qry_a.ljust(width, '-')

    matches = 0
    mismatches = 0
    gaps = 0
    for r, q in zip(ref_a, qry_a):
        if r == '-' or q == '-':
            gaps += 1
        elif r == q:
            matches += 1
        else:
            mismatches += 1

    chunks_html = []
    for start in range(0, width, max_per_row):
        end = min(start + max_per_row, width)
        ref_chunk = ref_a[start:end]
        qry_chunk = qry_a[start:end]

        ref_row = []
        qry_row = []
        mark_row = []
        for r, q in zip(ref_chunk, qry_chunk):
            if r == '-' or q == '-':
                cell_bg = '#ECEFF1'; mark = '·'
            elif r == q:
                cell_bg = '#C8E6C9'; mark = '|'
            else:
                cell_bg = '#FFCDD2'; mark = '×'
            ref_row.append(
                f'<span style="display:inline-block;width:13px;text-align:center;'
                f'background:{cell_bg};color:#212121;">{r}</span>'
            )
            qry_row.append(
                f'<span style="display:inline-block;width:13px;text-align:center;'
                f'background:{cell_bg};color:#212121;">{q}</span>'
            )
            mark_color = '#1B5E20' if mark == '|' else ('#B71C1C' if mark == '×' else '#9E9E9E')
            mark_row.append(
                f'<span style="display:inline-block;width:13px;text-align:center;color:{mark_color};">{mark}</span>'
            )
        chunks_html.append(
            f'<div style="margin-bottom:8px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;line-height:16px;">'
            f'<div style="color:#888;font-size:10px;">[{start}…{end - 1}]</div>'
            f'<div><span style="display:inline-block;width:50px;color:#0277BD;font-weight:600;">ref </span>{"".join(ref_row)}</div>'
            f'<div><span style="display:inline-block;width:50px;color:#888;"></span>{"".join(mark_row)}</div>'
            f'<div><span style="display:inline-block;width:50px;color:#E65100;font-weight:600;">asm </span>{"".join(qry_row)}</div>'
            f'</div>'
        )

    total = matches + mismatches + gaps
    pct = (matches / total * 100) if total > 0 else 0
    summary = (
        f'<div style="margin-bottom:8px;padding:8px;background:#FAFAFA;border-radius:6px;'
        f'font-size:13px;">'
        f'<b style="color:#1B5E20;">{matches}</b> match · '
        f'<b style="color:#B71C1C;">{mismatches}</b> mismatch · '
        f'<b style="color:#616161;">{gaps}</b> gap · '
        f'identity = <b>{pct:.1f}%</b>'
        f'</div>'
    )

    return summary + '<div style="max-height:340px;overflow-y:auto;">' + ''.join(chunks_html) + '</div>'
