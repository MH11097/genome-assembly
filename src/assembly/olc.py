"""
Thuật toán OLC (Overlap-Layout-Consensus) cho genome assembly.

OLC hoạt động theo 3 bước:
1. Overlap: Tìm tất cả overlaps giữa các reads (suffix-prefix matching)
2. Layout: Xây dựng overlap graph và tìm đường đi Hamilton
3. Consensus: Ghép các reads theo đường đi để tạo genome
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Set


@dataclass
class Overlap:
    """Thông tin về overlap giữa 2 reads."""
    read_a: int      # Index của read đầu tiên
    read_b: int      # Index của read thứ hai
    length: int      # Độ dài overlap
    score: float = 1.0  # Điểm chất lượng (1.0 = exact match)


@dataclass
class OLCState:
    """Trạng thái thuật toán cho visualization."""
    phase: str                           # 'overlap' | 'layout' | 'consensus'
    step: int                            # Bước hiện tại trong phase
    current_pair: Tuple[int, int] = (0, 0)  # Cặp reads đang xét
    overlaps_found: List[Overlap] = field(default_factory=list)
    path: List[int] = field(default_factory=list)
    visited: Set[int] = field(default_factory=set)
    message: str = ""                    # Giải thích bằng tiếng Việt


class OLCAssembler:
    """
    Lắp ráp genome bằng thuật toán OLC.

    Thuật toán:
    1. So sánh từng cặp reads để tìm overlaps
    2. Xây dựng đồ thị overlap (nodes=reads, edges=overlaps)
    3. Tìm đường đi Hamilton (đi qua mỗi node 1 lần) - dùng greedy
    4. Ghép reads theo đường đi

    Attributes:
        reads: Danh sách reads đầu vào
        min_overlap: Độ dài overlap tối thiểu
        overlaps: Danh sách overlaps tìm được
        path: Đường đi Hamilton
    """

    def __init__(self, reads: List[str], min_overlap: int = 3):
        """
        Khởi tạo assembler.

        Args:
            reads: Danh sách reads cần lắp ráp
            min_overlap: Độ dài overlap tối thiểu để xem là hợp lệ
        """
        self.reads = reads
        self.min_overlap = min_overlap
        self.overlaps: List[Overlap] = []
        self.graph: Dict[int, List[Tuple[int, int]]] = {}  # {read_idx: [(neighbor_idx, overlap_len)]}
        self.path: List[int] = []
        self._states: List[OLCState] = []

    def find_overlaps(self) -> List[Overlap]:
        """
        Bước 1: Tìm tất cả overlaps giữa các reads.

        So sánh suffix của read A với prefix của read B.
        Complexity: O(n² * m²) với n=số reads, m=độ dài read

        Returns:
            Danh sách các Overlap tìm được
        """
        self.overlaps = []
        n = len(self.reads)

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue

                overlap_len = self._find_suffix_prefix_overlap(
                    self.reads[i], self.reads[j]
                )

                if overlap_len >= self.min_overlap:
                    overlap = Overlap(read_a=i, read_b=j, length=overlap_len)
                    self.overlaps.append(overlap)

                    # Lưu state cho visualization
                    self._states.append(OLCState(
                        phase='overlap',
                        step=len(self._states),
                        current_pair=(i, j),
                        overlaps_found=self.overlaps.copy(),
                        message=f"Tìm thấy overlap: R{i} → R{j} ({overlap_len} bp)"
                    ))

        return self.overlaps

    def _find_suffix_prefix_overlap(self, read_a: str, read_b: str) -> int:
        """
        Tìm độ dài overlap lớn nhất giữa suffix của A và prefix của B.

        Args:
            read_a: Read đầu tiên (lấy suffix)
            read_b: Read thứ hai (lấy prefix)

        Returns:
            Độ dài overlap lớn nhất
        """
        max_overlap = min(len(read_a), len(read_b))

        for length in range(max_overlap, self.min_overlap - 1, -1):
            if read_a[-length:] == read_b[:length]:
                return length
        return 0

    def build_overlap_graph(self) -> Dict[int, List[Tuple[int, int]]]:
        """
        Xây dựng đồ thị overlap từ danh sách overlaps.

        Returns:
            Adjacency list: {node: [(neighbor, weight), ...]}
        """
        self.graph = {i: [] for i in range(len(self.reads))}

        for overlap in self.overlaps:
            self.graph[overlap.read_a].append((overlap.read_b, overlap.length))

        return self.graph

    def find_hamiltonian_path(self) -> List[int]:
        """
        Bước 2: Tìm đường đi Hamilton bằng greedy heuristic với backtracking.

        Greedy strategy: Tại mỗi bước, chọn edge có overlap lớn nhất.
        Khi gặp dead-end: thử backtrack trước khi chấp nhận path không hoàn chỉnh.

        Returns:
            Danh sách indices của reads theo thứ tự đường đi
        """
        if not self.graph:
            self.build_overlap_graph()

        n = len(self.reads)
        if n == 0:
            return []
        if n == 1:
            return [0]

        # Tìm node bắt đầu tốt nhất: ưu tiên node có out_degree > in_degree (source)
        in_degree = {i: 0 for i in range(n)}
        out_degree = {i: len(self.graph.get(i, [])) for i in range(n)}
        for neighbors in self.graph.values():
            for neighbor, _ in neighbors:
                in_degree[neighbor] = in_degree.get(neighbor, 0) + 1

        # Chọn source node (out > in) hoặc node có nhiều edges nhất
        start = None
        for node in range(n):
            if out_degree[node] > in_degree[node]:
                start = node
                break
        if start is None:
            start = max(range(n), key=lambda x: out_degree[x])

        visited: Set[int] = {start}
        path: List[int] = [start]
        tried_edges: Dict[int, Set[int]] = {i: set() for i in range(n)}

        self._states.append(OLCState(
            phase='layout',
            step=len(self._states),
            path=path.copy(),
            visited=visited.copy(),
            message=f"Bắt đầu từ R{start}"
        ))

        max_backtrack = min(n * 2, 50)  # Giới hạn số lần backtrack
        backtrack_count = 0

        while len(visited) < n:
            current = path[-1]
            neighbors = self.graph.get(current, [])

            # Lọc neighbors chưa thăm và chưa thử, sắp xếp theo overlap giảm dần
            unvisited = [(node, overlap) for node, overlap in neighbors
                         if node not in visited and node not in tried_edges[current]]
            unvisited.sort(key=lambda x: x[1], reverse=True)

            if unvisited:
                next_node, overlap_len = unvisited[0]
                tried_edges[current].add(next_node)
                path.append(next_node)
                visited.add(next_node)

                self._states.append(OLCState(
                    phase='layout',
                    step=len(self._states),
                    current_pair=(current, next_node),
                    path=path.copy(),
                    visited=visited.copy(),
                    message=f"Di chuyển: R{current} → R{next_node} (overlap {overlap_len} bp)"
                ))
            else:
                # Dead end - thử backtrack
                if len(path) > 1 and backtrack_count < max_backtrack:
                    # Quay lại node trước
                    dead_node = path.pop()
                    visited.remove(dead_node)
                    backtrack_count += 1

                    self._states.append(OLCState(
                        phase='layout',
                        step=len(self._states),
                        path=path.copy(),
                        visited=visited.copy(),
                        message=f"Dead-end tại R{dead_node}, backtrack về R{path[-1]}"
                    ))
                else:
                    # Không thể backtrack thêm - chấp nhận path hiện tại
                    # Thêm các node còn lại (disconnected) nếu cần thiết cho demo
                    remaining = [node for node in range(n) if node not in visited]
                    if remaining:
                        # Tìm node có overlap tốt nhất với bất kỳ node nào trong path
                        best_node = None
                        best_overlap = 0
                        for node in remaining:
                            for path_node in path:
                                overlap = self._get_overlap_length(path_node, node)
                                if overlap > best_overlap:
                                    best_overlap = overlap
                                    best_node = node
                        if best_node is None:
                            best_node = remaining[0]

                        path.append(best_node)
                        visited.add(best_node)
                        self._states.append(OLCState(
                            phase='layout',
                            step=len(self._states),
                            path=path.copy(),
                            visited=visited.copy(),
                            message=f"Đồ thị rời rạc, thêm R{best_node} (overlap={best_overlap}bp)"
                        ))

        self.path = path
        return path

    def _get_overlap_length(self, read_a_idx: int, read_b_idx: int) -> int:
        """Lấy độ dài overlap giữa 2 reads từ overlaps đã tìm."""
        for o in self.overlaps:
            if o.read_a == read_a_idx and o.read_b == read_b_idx:
                return o.length
        return 0

    def build_consensus(self) -> str:
        """
        Bước 3: Ghép các reads theo đường đi để tạo genome.

        Với mỗi cặp reads liên tiếp trong path:
        - Tìm overlap giữa chúng
        - Chỉ thêm phần không overlap của read sau

        Returns:
            Chuỗi genome đã lắp ráp
        """
        if not self.path:
            return ""

        # Tạo lookup cho overlaps
        overlap_map: Dict[Tuple[int, int], int] = {}
        for o in self.overlaps:
            overlap_map[(o.read_a, o.read_b)] = o.length

        # Bắt đầu với read đầu tiên
        consensus = self.reads[self.path[0]]

        self._states.append(OLCState(
            phase='consensus',
            step=len(self._states),
            path=self.path,
            message=f"Bắt đầu với R{self.path[0]}: {consensus[:20]}..."
        ))

        # Ghép từng read tiếp theo
        for i in range(len(self.path) - 1):
            curr_idx = self.path[i]
            next_idx = self.path[i + 1]

            overlap_len = overlap_map.get((curr_idx, next_idx), 0)
            next_read = self.reads[next_idx]

            if overlap_len > 0:
                # Thêm phần không overlap
                consensus += next_read[overlap_len:]
            else:
                # Không có overlap - thêm cả read
                consensus += next_read

            self._states.append(OLCState(
                phase='consensus',
                step=len(self._states),
                current_pair=(curr_idx, next_idx),
                message=f"Ghép R{next_idx} (overlap={overlap_len}): ...{consensus[-20:]}"
            ))

        return consensus

    def assemble(self) -> str:
        """
        Chạy toàn bộ pipeline OLC.

        Returns:
            Genome đã lắp ráp
        """
        self._states = []  # Reset states
        self.find_overlaps()
        self.find_hamiltonian_path()
        return self.build_consensus()

    def get_step_states(self) -> List[OLCState]:
        """Lấy danh sách states cho step-by-step visualization."""
        return self._states

    def get_overlap_matrix(self) -> List[List[int]]:
        """
        Tạo ma trận overlap cho visualization.

        Returns:
            Ma trận n×n với [i][j] = độ dài overlap từ read i đến read j
        """
        n = len(self.reads)
        matrix = [[0] * n for _ in range(n)]

        for o in self.overlaps:
            matrix[o.read_a][o.read_b] = o.length

        return matrix
