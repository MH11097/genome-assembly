"""
Module tạo genome ngẫu nhiên và load genome virus mẫu.

Cung cấp các phương thức để:
- Tạo genome ngẫu nhiên với độ dài tùy chọn
- Tạo genome có vùng lặp lại (tandem repeats)
- Load genome virus thật từ file JSON
"""

import random
import json
from pathlib import Path
from typing import Optional, List


class GenomeGenerator:
    """
    Lớp tạo genome cho mục đích demo và giáo dục.

    Attributes:
        BASES: Danh sách 4 nucleotide cơ bản của DNA

    Examples:
        >>> gen = GenomeGenerator()
        >>> genome = gen.generate_random(100)
        >>> len(genome)
        100
    """

    BASES = ['A', 'T', 'G', 'C']

    def __init__(self, seed: Optional[int] = None):
        """
        Khởi tạo generator.

        Args:
            seed: Random seed để tái tạo kết quả (optional)
        """
        if seed is not None:
            random.seed(seed)
        self._virus_data = None

    def generate_random(self, length: int) -> str:
        """
        Tạo genome ngẫu nhiên với độ dài cho trước.

        Mỗi vị trí được chọn ngẫu nhiên từ 4 nucleotide với xác suất bằng nhau.

        Args:
            length: Độ dài genome mong muốn (bp)

        Returns:
            Chuỗi DNA ngẫu nhiên

        Raises:
            ValueError: Nếu length <= 0 hoặc > 10000

        Examples:
            >>> gen = GenomeGenerator(seed=42)
            >>> genome = gen.generate_random(10)
            >>> len(genome)
            10
        """
        if length <= 0:
            raise ValueError("Độ dài phải lớn hơn 0")
        if length > 10000:
            raise ValueError("Độ dài tối đa là 10000 bp")

        return ''.join(random.choices(self.BASES, k=length))

    def generate_with_repeats(
        self,
        length: int,
        repeat_unit: str = "ATATAT",
        num_copies: int = 3,
        num_repeat_regions: int = 1
    ) -> str:
        """
        Tạo genome có chứa vùng tandem repeat.

        Tandem repeat là các đoạn DNA lặp lại liên tiếp, thường gặp trong genome thật.
        Đây là một trong những thách thức chính của genome assembly.

        Args:
            length: Độ dài tổng thể của genome (bp)
            repeat_unit: Đơn vị lặp lại (VD: "ATATAT")
            num_copies: Số lần lặp lại của repeat_unit
            num_repeat_regions: Số vùng repeat trong genome

        Returns:
            Chuỗi DNA chứa vùng repeat

        Examples:
            >>> gen = GenomeGenerator(seed=42)
            >>> genome = gen.generate_with_repeats(100, "AT", 5)
            >>> "ATATATATAT" in genome  # 5 copies of "AT"
            True
        """
        if length <= 0:
            raise ValueError("Độ dài phải lớn hơn 0")
        if length > 10000:
            raise ValueError("Độ dài tối đa là 10000 bp")

        # Validate repeat_unit
        repeat_unit = repeat_unit.upper()
        if not all(base in 'ATGC' for base in repeat_unit):
            raise ValueError("Repeat unit chỉ được chứa A, T, G, C")

        # Tạo repeat block
        repeat_block = repeat_unit * num_copies
        total_repeat_length = len(repeat_block) * num_repeat_regions

        if total_repeat_length >= length:
            # Nếu repeat quá dài, chỉ trả về repeat
            return repeat_block[:length]

        # Tạo backbone ngẫu nhiên
        backbone_length = length - total_repeat_length
        backbone = self.generate_random(backbone_length)

        # Chèn repeat blocks vào các vị trí ngẫu nhiên
        result = list(backbone)
        for _ in range(num_repeat_regions):
            if len(result) == 0:
                insert_pos = 0
            else:
                insert_pos = random.randint(0, len(result))
            # Chèn repeat block
            result = result[:insert_pos] + list(repeat_block) + result[insert_pos:]

        return ''.join(result)

    def _load_virus_data(self) -> dict:
        """Load virus data từ file JSON."""
        if self._virus_data is None:
            data_path = Path(__file__).parent.parent.parent / "data" / "virus_examples.json"
            if data_path.exists():
                with open(data_path, 'r', encoding='utf-8') as f:
                    self._virus_data = json.load(f)
            else:
                # Fallback nếu file không tồn tại
                self._virus_data = {"viruses": []}
        return self._virus_data

    def get_virus_names(self) -> List[str]:
        """
        Lấy danh sách tên các virus có sẵn.

        Returns:
            Danh sách tên virus

        Examples:
            >>> gen = GenomeGenerator()
            >>> names = gen.get_virus_names()
            >>> isinstance(names, list)
            True
        """
        data = self._load_virus_data()
        return [v['name'] for v in data.get('viruses', [])]

    def load_virus_example(self, name: str) -> str:
        """
        Load genome virus theo tên.

        Args:
            name: Tên virus (từ get_virus_names())

        Returns:
            Chuỗi DNA của virus

        Raises:
            ValueError: Nếu không tìm thấy virus

        Examples:
            >>> gen = GenomeGenerator()
            >>> genome = gen.load_virus_example("Phi X 174 (fragment)")
            >>> len(genome) > 0
            True
        """
        data = self._load_virus_data()
        for virus in data.get('viruses', []):
            if virus['name'] == name:
                return virus['sequence']
        raise ValueError(f"Không tìm thấy virus: {name}")

    def get_virus_info(self, name: str) -> dict:
        """
        Lấy thông tin chi tiết về virus.

        Args:
            name: Tên virus

        Returns:
            Dictionary chứa name, description, sequence, length

        Raises:
            ValueError: Nếu không tìm thấy virus
        """
        data = self._load_virus_data()
        for virus in data.get('viruses', []):
            if virus['name'] == name:
                return virus
        raise ValueError(f"Không tìm thấy virus: {name}")
