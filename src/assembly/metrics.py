"""
Các metrics đánh giá chất lượng genome assembly.

Metrics phổ biến:
- N50: Độ dài contig tại đó 50% genome được cover
- Accuracy: Tỷ lệ khớp với genome gốc
- Contig statistics: Số lượng, độ dài trung bình, etc.
"""

from typing import List


def calculate_n50(contig_lengths: List[int]) -> int:
    """
    Tính N50 - metric quan trọng nhất trong genome assembly.

    N50 là độ dài contig sao cho tổng các contigs có độ dài >= N50
    chiếm ít nhất 50% tổng độ dài genome.

    Args:
        contig_lengths: Danh sách độ dài các contigs

    Returns:
        Giá trị N50

    Examples:
        >>> calculate_n50([100, 50, 30, 20])  # total=200, 50% = 100
        100
        >>> calculate_n50([50, 50])
        50
    """
    if not contig_lengths:
        return 0

    sorted_lengths = sorted(contig_lengths, reverse=True)
    total = sum(sorted_lengths)
    target = total / 2
    cumsum = 0

    for length in sorted_lengths:
        cumsum += length
        if cumsum >= target:
            return length

    return 0


def alignment_accuracy(assembled: str, reference: str) -> float:
    """
    Tính độ chính xác của genome lắp ráp so với genome gốc.

    Sử dụng 2 metrics:
    1. Prefix match: So sánh từ đầu (quan trọng nhất cho assembly)
    2. Best substring match: Tìm đoạn khớp tốt nhất

    Args:
        assembled: Genome đã lắp ráp
        reference: Genome gốc (reference)

    Returns:
        Accuracy (0-100%)

    Examples:
        >>> alignment_accuracy("ATCG", "ATCG")
        100.0
        >>> alignment_accuracy("ATCG", "ATCC")
        75.0
    """
    if not reference:
        return 0.0
    if not assembled:
        return 0.0

    # Method 1: Prefix match (character-by-character từ đầu)
    min_len = min(len(assembled), len(reference))
    prefix_matches = sum(1 for i in range(min_len) if assembled[i] == reference[i])

    # Method 2: Best sliding window match (tìm vị trí khớp tốt nhất)
    best_match = prefix_matches
    max_shift = min(50, len(reference) // 4)  # Giới hạn tìm kiếm

    for shift in range(1, max_shift + 1):
        # Shift assembled to the right
        matches = sum(1 for i in range(min(len(assembled), len(reference) - shift))
                      if assembled[i] == reference[i + shift])
        best_match = max(best_match, matches)

        # Shift reference to the right
        matches = sum(1 for i in range(min(len(assembled) - shift, len(reference)))
                      if assembled[i + shift] == reference[i])
        best_match = max(best_match, matches)

    # Tính accuracy dựa trên max(assembled, reference) length
    max_len = max(len(assembled), len(reference))
    accuracy = (best_match / max_len) * 100

    return round(min(accuracy, 100.0), 1)


def contig_statistics(contigs: List[str]) -> dict:
    """
    Tính các thống kê về contigs.

    Args:
        contigs: Danh sách các contigs (chuỗi DNA)

    Returns:
        Dictionary với các metrics

    Examples:
        >>> stats = contig_statistics(["AAA", "TTTTTT", "GG"])
        >>> stats['num_contigs']
        3
        >>> stats['total_length']
        11
    """
    if not contigs:
        return {
            'num_contigs': 0,
            'total_length': 0,
            'mean_length': 0,
            'n50': 0,
            'longest': 0,
            'shortest': 0
        }

    lengths = [len(c) for c in contigs]

    return {
        'num_contigs': len(contigs),
        'total_length': sum(lengths),
        'mean_length': round(sum(lengths) / len(lengths), 2),
        'n50': calculate_n50(lengths),
        'longest': max(lengths),
        'shortest': min(lengths)
    }


def compare_assemblies(
    olc_result: str,
    dbg_result: str,
    reference: str,
    olc_time_ms: float = 0,
    dbg_time_ms: float = 0
) -> dict:
    """
    So sánh kết quả của OLC và DBG.

    Args:
        olc_result: Genome từ OLC
        dbg_result: Genome từ DBG
        reference: Genome gốc
        olc_time_ms: Thời gian chạy OLC (ms)
        dbg_time_ms: Thời gian chạy DBG (ms)

    Returns:
        Dictionary so sánh các metrics
    """
    return {
        'olc': {
            'length': len(olc_result),
            'accuracy': alignment_accuracy(olc_result, reference),
            'time_ms': round(olc_time_ms, 2)
        },
        'dbg': {
            'length': len(dbg_result),
            'accuracy': alignment_accuracy(dbg_result, reference),
            'time_ms': round(dbg_time_ms, 2)
        },
        'reference_length': len(reference)
    }
