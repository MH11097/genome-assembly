"""
Module xác thực chuỗi DNA.

Cung cấp các hàm kiểm tra và chuẩn hóa chuỗi DNA,
đảm bảo chỉ chứa các nucleotide hợp lệ (A, T, G, C).
"""

import re
from typing import Optional

# Các nucleotide hợp lệ trong DNA
VALID_BASES = frozenset('ATGC')


def validate_dna(sequence: str) -> bool:
    """
    Kiểm tra chuỗi DNA có hợp lệ không.

    Chuỗi hợp lệ chỉ chứa các ký tự A, T, G, C (không phân biệt hoa thường).

    Args:
        sequence: Chuỗi DNA cần kiểm tra

    Returns:
        True nếu chuỗi hợp lệ, False nếu không

    Examples:
        >>> validate_dna("ATCG")
        True
        >>> validate_dna("atcg")
        True
        >>> validate_dna("ATCX")
        False
        >>> validate_dna("")
        False
    """
    if not sequence:
        return False
    return all(base in VALID_BASES for base in sequence.upper())


def clean_sequence(sequence: str) -> str:
    """
    Chuẩn hóa chuỗi DNA.

    - Chuyển thành chữ hoa
    - Loại bỏ khoảng trắng và ký tự xuống dòng
    - Chỉ giữ lại các nucleotide hợp lệ

    Args:
        sequence: Chuỗi DNA đầu vào

    Returns:
        Chuỗi DNA đã chuẩn hóa

    Examples:
        >>> clean_sequence("atcg")
        'ATCG'
        >>> clean_sequence("A T C G")
        'ATCG'
        >>> clean_sequence("ATCG\\n")
        'ATCG'
        >>> clean_sequence("ATCX123G")
        'ATCG'
    """
    # Loại bỏ tất cả ký tự không phải nucleotide
    return ''.join(base for base in sequence.upper() if base in VALID_BASES)


def get_sequence_info(sequence: str) -> dict:
    """
    Lấy thông tin cơ bản về chuỗi DNA.

    Args:
        sequence: Chuỗi DNA (đã validate)

    Returns:
        Dictionary chứa thông tin: length, gc_content, base_counts

    Examples:
        >>> info = get_sequence_info("ATCGATCG")
        >>> info['length']
        8
        >>> info['gc_content']
        50.0
    """
    if not sequence:
        return {
            'length': 0,
            'gc_content': 0.0,
            'base_counts': {'A': 0, 'T': 0, 'G': 0, 'C': 0}
        }

    seq = sequence.upper()
    length = len(seq)

    base_counts = {
        'A': seq.count('A'),
        'T': seq.count('T'),
        'G': seq.count('G'),
        'C': seq.count('C')
    }

    gc_count = base_counts['G'] + base_counts['C']
    gc_content = (gc_count / length) * 100 if length > 0 else 0.0

    return {
        'length': length,
        'gc_content': round(gc_content, 2),
        'base_counts': base_counts
    }
