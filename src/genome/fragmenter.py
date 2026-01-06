"""
Module phân mảnh genome thành reads.

Mô phỏng quá trình sequencing trong thực tế, nơi genome được bẻ nhỏ
thành các đoạn ngắn (reads) để đọc trình tự.
"""

import random
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ReadInfo:
    """Thông tin chi tiết về một read."""
    sequence: str
    start_position: int
    end_position: int
    index: int


class ReadFragmenter:
    """
    Lớp bẻ nhỏ genome thành reads.

    Mô phỏng quá trình sequencing:
    - Genome được cắt ngẫu nhiên thành các đoạn có độ dài cố định
    - Số lượng reads phụ thuộc vào coverage (độ phủ)
    - Coverage = (số reads * độ dài read) / độ dài genome

    Examples:
        >>> frag = ReadFragmenter()
        >>> reads = frag.fragment("ATCGATCGATCG", read_length=4, coverage=3)
        >>> all(len(r) == 4 for r in reads)
        True
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Khởi tạo fragmenter.

        Args:
            seed: Random seed để tái tạo kết quả
        """
        if seed is not None:
            random.seed(seed)

    def fragment(
        self,
        genome: str,
        read_length: int,
        coverage: int
    ) -> List[str]:
        """
        Bẻ genome thành reads.

        Công thức tính số reads:
            num_reads = (len(genome) * coverage) / read_length

        Args:
            genome: Chuỗi DNA gốc
            read_length: Độ dài mỗi read (bp)
            coverage: Độ phủ mong muốn (VD: 10 = mỗi vị trí được đọc ~10 lần)

        Returns:
            Danh sách các reads

        Raises:
            ValueError: Nếu tham số không hợp lệ

        Examples:
            >>> frag = ReadFragmenter(seed=42)
            >>> reads = frag.fragment("A" * 100, read_length=10, coverage=5)
            >>> len(reads)  # ~50 reads
            50
        """
        if not genome:
            raise ValueError("Genome không được rỗng")
        if read_length <= 0:
            raise ValueError("Độ dài read phải lớn hơn 0")
        if read_length > len(genome):
            raise ValueError("Độ dài read không được lớn hơn genome")
        if coverage <= 0:
            raise ValueError("Coverage phải lớn hơn 0")

        # Tính số reads cần tạo
        genome_length = len(genome)
        num_reads = (genome_length * coverage) // read_length

        # Đảm bảo ít nhất 1 read
        num_reads = max(1, num_reads)

        reads = []
        max_start = genome_length - read_length

        for _ in range(num_reads):
            # Chọn vị trí bắt đầu ngẫu nhiên
            start = random.randint(0, max_start)
            read = genome[start:start + read_length]
            reads.append(read)

        return reads

    def fragment_with_info(
        self,
        genome: str,
        read_length: int,
        coverage: int
    ) -> List[ReadInfo]:
        """
        Bẻ genome thành reads kèm thông tin vị trí.

        Hữu ích cho visualization để hiển thị reads trên genome gốc.

        Args:
            genome: Chuỗi DNA gốc
            read_length: Độ dài mỗi read
            coverage: Độ phủ mong muốn

        Returns:
            Danh sách ReadInfo chứa sequence và vị trí

        Examples:
            >>> frag = ReadFragmenter(seed=42)
            >>> infos = frag.fragment_with_info("ATCGATCG", 4, 2)
            >>> all(isinstance(r, ReadInfo) for r in infos)
            True
        """
        if not genome:
            raise ValueError("Genome không được rỗng")
        if read_length <= 0:
            raise ValueError("Độ dài read phải lớn hơn 0")
        if read_length > len(genome):
            raise ValueError("Độ dài read không được lớn hơn genome")

        genome_length = len(genome)
        num_reads = (genome_length * coverage) // read_length
        num_reads = max(1, num_reads)

        reads = []
        max_start = genome_length - read_length

        for i in range(num_reads):
            start = random.randint(0, max_start)
            end = start + read_length
            read = genome[start:end]
            reads.append(ReadInfo(
                sequence=read,
                start_position=start,
                end_position=end,
                index=i
            ))

        return reads

    def add_errors(
        self,
        reads: List[str],
        error_rate: float = 0.01
    ) -> List[str]:
        """
        Thêm lỗi ngẫu nhiên vào reads (mô phỏng sequencing errors).

        Trong sequencing thật, có tỷ lệ lỗi nhỏ (~0.1-1% cho Illumina).
        Lỗi có thể là substitution (thay thế base).

        Args:
            reads: Danh sách reads gốc
            error_rate: Tỷ lệ lỗi (0.01 = 1%)

        Returns:
            Danh sách reads có lỗi

        Examples:
            >>> frag = ReadFragmenter(seed=42)
            >>> reads = ["ATCG", "GCTA"]
            >>> noisy = frag.add_errors(reads, error_rate=0.5)
            >>> noisy != reads  # Có thể có sự khác biệt
            True
        """
        if error_rate < 0 or error_rate > 1:
            raise ValueError("Error rate phải trong khoảng [0, 1]")

        bases = ['A', 'T', 'G', 'C']
        noisy_reads = []

        for read in reads:
            noisy_read = []
            for base in read:
                if random.random() < error_rate:
                    # Thay thế bằng base khác
                    other_bases = [b for b in bases if b != base]
                    noisy_read.append(random.choice(other_bases))
                else:
                    noisy_read.append(base)
            noisy_reads.append(''.join(noisy_read))

        return noisy_reads

    @staticmethod
    def calculate_theoretical_coverage(
        genome_length: int,
        read_length: int,
        num_reads: int
    ) -> float:
        """
        Tính coverage lý thuyết.

        Args:
            genome_length: Độ dài genome
            read_length: Độ dài read
            num_reads: Số reads

        Returns:
            Coverage value

        Examples:
            >>> ReadFragmenter.calculate_theoretical_coverage(1000, 100, 50)
            5.0
        """
        if genome_length <= 0:
            return 0.0
        return (num_reads * read_length) / genome_length
