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
    Tính độ chính xác = % ký tự reference khớp với assembled tại offset tốt nhất.

    Phiên bản giáo dục: Hamilton/Euler path không nhất thiết bắt đầu từ đầu
    reference, nên thử mọi offset (cả assembled lệch phải lẫn reference lệch
    phải) và lấy số ký tự khớp lớn nhất, chia cho len(reference).

    Args:
        assembled: Genome đã lắp ráp
        reference: Genome gốc (reference)

    Returns:
        Accuracy (0-100%) so với len(reference)

    Examples:
        >>> alignment_accuracy("ATCG", "ATCG")
        100.0
        >>> alignment_accuracy("ATCC", "ATCG")
        75.0
        >>> alignment_accuracy("XXATCGXX", "ATCG")
        100.0
    """
    if not reference or not assembled:
        return 0.0

    best = 0
    # assembled lệch phải s ký tự (so reference[s..] với assembled[0..])
    for s in range(len(reference)):
        m = sum(1 for i in range(min(len(assembled), len(reference) - s))
                if assembled[i] == reference[s + i])
        if m > best:
            best = m
    # reference lệch phải s ký tự (so assembled[s..] với reference[0..])
    for s in range(1, len(assembled)):
        m = sum(1 for i in range(min(len(reference), len(assembled) - s))
                if assembled[s + i] == reference[i])
        if m > best:
            best = m

    accuracy = (best / len(reference)) * 100
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
