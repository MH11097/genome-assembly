"""
Thuật toán de Bruijn Graph (DBG) cho genome assembly.

DBG hoạt động theo 4 bước:
1. Tạo k-mers từ reads
2. Xây dựng de Bruijn graph (nodes = (k-1)-mers, edges = k-mers)
3. Tìm đường đi Euler (Hierholzer algorithm)
4. Ghép các nodes thành genome
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from copy import deepcopy


@dataclass
class DBGState:
    """Trạng thái thuật toán cho visualization."""
    phase: str           # 'kmer' | 'graph' | 'euler' | 'reconstruct'
    step: int
    current_kmer: str = ""
    current_node: str = ""
    next_node: str = ""              # Node sắp đi tới (phase euler)
    read_index: int = -1             # Read đang được xử lý (phase kmer)
    window_pos: int = -1             # Vị trí sliding window trên read (phase kmer)
    stack_snapshot: List[str] = field(default_factory=list)  # Hierholzer stack
    edges_remaining: int = -1        # Cạnh còn lại (phase euler)
    edges_total: int = -1
    visited_edges: List[Tuple[str, str]] = field(default_factory=list)
    genome_so_far: str = ""          # Genome đang xây (phase reconstruct)
    graph: Dict[str, List[str]] = field(default_factory=dict)
    path: List[str] = field(default_factory=list)
    message: str = ""


class DBGAssembler:
    """
    Lắp ráp genome bằng de Bruijn Graph.

    Ưu điểm so với OLC:
    - Complexity O(n) thay vì O(n²)
    - Hiệu quả với short reads
    - Tìm đường Euler (polynomial) thay vì Hamilton (NP-hard)
    """

    def __init__(self, reads: List[str], k: int = 11, max_states: Optional[int] = None):
        self.reads = reads
        self.k = k
        self.max_states = max_states  # None = không giới hạn (cho demo nhỏ)
        self.kmers: Dict[str, int] = {}
        self.graph: Dict[str, List[str]] = defaultdict(list)
        self.in_degree: Dict[str, int] = defaultdict(int)
        self.out_degree: Dict[str, int] = defaultdict(int)
        self.path: List[str] = []
        self._states: List[DBGState] = []
        # Per-phase timing (ms) – đặt bởi assemble()
        self.timing_ms: Dict[str, float] = {}

    def generate_kmers(self) -> Dict[str, int]:
        """Bước 1: Tạo k-mers từ tất cả reads."""
        self.kmers = defaultdict(int)

        for read_idx, read in enumerate(self.reads):
            for i in range(len(read) - self.k + 1):
                kmer = read[i:i + self.k]
                self.kmers[kmer] += 1

                if self.max_states is None or len(self._states) < self.max_states:
                    self._states.append(DBGState(
                        phase='kmer', step=len(self._states),
                        current_kmer=kmer,
                        read_index=read_idx,
                        window_pos=i,
                        message=f"Read R{read_idx}[{i}:{i+self.k}] → k-mer {kmer}"
                    ))

        return dict(self.kmers)

    def build_debruijn_graph(self) -> Dict[str, List[str]]:
        """
        Bước 2: Xây dựng de Bruijn graph.

        Node = (k-1)-mer, Edge = k-mer
        Edge từ prefix (k-1)-mer đến suffix (k-1)-mer

        GIÁO DỤC: dedupe edges để mỗi k-mer = 1 edge → graph dễ visualize
        (không multi-edge song song giữa 2 node). Hệ quả: mất khả năng
        xử lý đúng vùng repeat — DBG production phải dùng MultiGraph và
        track multiplicity của k-mer để Hierholzer đi qua mỗi instance.
        """
        self.graph = defaultdict(list)
        self.in_degree = defaultdict(int)
        self.out_degree = defaultdict(int)
        added_edges: Set[tuple] = set()

        for kmer in self.kmers.keys():
            left = kmer[:-1]   # (k-1)-mer prefix
            right = kmer[1:]   # (k-1)-mer suffix

            # Chỉ thêm edge nếu chưa tồn tại (tránh duplicate)
            if (left, right) not in added_edges:
                self.graph[left].append(right)
                self.out_degree[left] += 1
                self.in_degree[right] += 1
                added_edges.add((left, right))

        self._states.append(DBGState(
            phase='graph', step=len(self._states),
            graph=dict(self.graph),
            message=f"Đồ thị: {len(self.graph)} nodes, {sum(len(v) for v in self.graph.values())} edges"
        ))

        return dict(self.graph)

    def find_eulerian_path(self) -> List[str]:
        """
        Bước 3: Tìm đường Euler bằng Hierholzer algorithm.

        Đường Euler đi qua mỗi EDGE đúng 1 lần.
        Điều kiện: tối đa 1 node có out > in (start), 1 node có in > out (end).
        """
        if not self.graph:
            return []

        # Tìm node bắt đầu (out_degree > in_degree).
        # Sort để đảm bảo deterministic - không phụ thuộc PYTHONHASHSEED.
        start = None
        all_nodes = sorted(set(self.out_degree.keys()) | set(self.in_degree.keys()))
        for node in all_nodes:
            if self.out_degree[node] > self.in_degree[node]:
                start = node
                break

        if start is None:
            start = sorted(self.graph.keys())[0] if self.graph else None

        if start is None:
            return []

        # Hierholzer algorithm
        graph_copy = {k: v[:] for k, v in self.graph.items()}
        stack = [start]
        path = []
        edges_total = sum(len(v) for v in self.graph.values())
        visited_edges: List[Tuple[str, str]] = []

        while stack:
            current = stack[-1]
            if graph_copy.get(current):
                next_node = graph_copy[current].pop()
                stack.append(next_node)
                visited_edges.append((current, next_node))

                if self.max_states is None or len(self._states) < self.max_states:
                    self._states.append(DBGState(
                        phase='euler', step=len(self._states),
                        current_node=current,
                        next_node=next_node,
                        stack_snapshot=stack[:],
                        edges_remaining=edges_total - len(visited_edges),
                        edges_total=edges_total,
                        visited_edges=visited_edges[:],
                        path=path[:],
                        message=f"Đi cạnh {current} → {next_node}  ({len(visited_edges)}/{edges_total})"
                    ))
            else:
                popped = stack.pop()
                path.append(popped)
                if self.max_states is None or len(self._states) < self.max_states:
                    self._states.append(DBGState(
                        phase='euler', step=len(self._states),
                        current_node=popped,
                        stack_snapshot=stack[:],
                        edges_remaining=edges_total - len(visited_edges),
                        edges_total=edges_total,
                        visited_edges=visited_edges[:],
                        path=path[:],
                        message=f"Hết cạnh tại {popped} → đẩy vào path"
                    ))

        self.path = path[::-1]
        return self.path

    def reconstruct_genome(self) -> str:
        """Bước 4: Ghép path thành genome."""
        if not self.path:
            return ""

        genome = self.path[0]
        # State đầu: chỉ có (k-1)-mer đầu tiên
        self._states.append(DBGState(
            phase='reconstruct', step=len(self._states),
            current_node=self.path[0],
            path=self.path,
            genome_so_far=genome,
            message=f"Khởi tạo bằng {self.path[0]} ({len(genome)} bp)"
        ))

        for idx, node in enumerate(self.path[1:], start=1):
            genome += node[-1]
            self._states.append(DBGState(
                phase='reconstruct', step=len(self._states),
                current_node=node,
                path=self.path,
                genome_so_far=genome,
                message=f"Thêm '{node[-1]}' từ {node} → genome {len(genome)} bp"
            ))

        return genome

    def assemble(self) -> str:
        """Chạy toàn bộ pipeline DBG, đo timing từng phase."""
        import time
        self._states = []
        self.timing_ms = {}

        t0 = time.perf_counter()
        self.generate_kmers()
        self.timing_ms['kmer'] = (time.perf_counter() - t0) * 1000.0

        t0 = time.perf_counter()
        self.build_debruijn_graph()
        self.timing_ms['graph'] = (time.perf_counter() - t0) * 1000.0

        t0 = time.perf_counter()
        self.find_eulerian_path()
        self.timing_ms['euler'] = (time.perf_counter() - t0) * 1000.0

        t0 = time.perf_counter()
        result = self.reconstruct_genome()
        self.timing_ms['reconstruct'] = (time.perf_counter() - t0) * 1000.0

        return result

    def get_step_states(self) -> List[DBGState]:
        """Lấy states cho visualization."""
        return self._states

    def get_graph_stats(self) -> dict:
        """Thống kê về đồ thị."""
        nodes = set(self.graph.keys())
        for targets in self.graph.values():
            nodes.update(targets)

        return {
            'num_nodes': len(nodes),
            'num_edges': sum(len(v) for v in self.graph.values()),
            'k': self.k,
            'unique_kmers': len(self.kmers)
        }
