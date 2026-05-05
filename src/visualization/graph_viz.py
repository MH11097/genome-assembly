"""
Module hiển thị đồ thị cho genome assembly.

Sử dụng PyVis để render:
- Overlap graph (OLC): nodes = reads, edges = overlaps
- de Bruijn graph (DBG): nodes = (k-1)-mers, edges = k-mers
"""

from typing import Dict, List, Set, Optional, Tuple, Any, TYPE_CHECKING
import tempfile
import os

try:
    from pyvis.network import Network
    PYVIS_AVAILABLE = True
except ImportError:
    PYVIS_AVAILABLE = False
    Network = None  # type: ignore

if TYPE_CHECKING:
    from pyvis.network import Network


class GraphVisualizer:
    """
    Render đồ thị assembly với PyVis.

    Color scheme:
    - Gray (#9E9E9E): Node chưa thăm
    - Yellow (#FFC107): Node đang xét
    - Green (#4CAF50): Node đã thăm
    - Red (#F44336): Node trên đường đi
    """

    COLORS = {
        'unvisited': '#9E9E9E',
        'current': '#FFC107',
        'visited': '#4CAF50',
        'path': '#F44336',
        'edge_default': '#888888',
        'edge_path': '#F44336',
    }

    def __init__(self, height: str = "400px", width: str = "100%"):
        self.height = height
        self.width = width

    def render_overlap_graph(
        self,
        reads: List[str],
        overlaps: List[Tuple[int, int, int]],
        visited: Optional[Set[int]] = None,
        current: Optional[int] = None,
        path: Optional[List[int]] = None
    ) -> str:
        """
        Render OLC overlap graph.

        Args:
            reads: Danh sách reads
            overlaps: List of (read_a, read_b, overlap_length)
            visited: Set các node đã thăm
            current: Node đang xét
            path: Đường đi hiện tại

        Returns:
            HTML string để embed vào Streamlit
        """
        if not PYVIS_AVAILABLE:
            return self._fallback_html("PyVis not installed")

        net = Network(
            height=self.height,
            width=self.width,
            directed=True,
            notebook=False,
            cdn_resources='in_line'
        )
        net.barnes_hut(gravity=-3000, spring_length=150)

        # Add nodes
        for i, read in enumerate(reads):
            color = self._get_node_color(i, visited, current, path)
            label = f"R{i}"
            title = f"Read {i}: {read[:30]}{'...' if len(read) > 30 else ''}"
            net.add_node(i, label=label, color=color, title=title, size=20)

        # Add edges
        path_edges = set()
        if path and len(path) > 1:
            path_edges = {(path[i], path[i+1]) for i in range(len(path)-1)}

        for src, dst, length in overlaps:
            edge_color = self.COLORS['edge_path'] if (src, dst) in path_edges else self.COLORS['edge_default']
            edge_width = 3 if (src, dst) in path_edges else 1
            net.add_edge(src, dst, value=length, title=f"Overlap: {length}bp",
                        color=edge_color, width=edge_width)

        return self._export_html(net)

    def render_debruijn_graph(
        self,
        graph: Dict[str, List[str]],
        visited_nodes: Optional[Set[str]] = None,
        current_node: Optional[str] = None,
        path: Optional[List[str]] = None
    ) -> str:
        """
        Render DBG de Bruijn graph.

        Args:
            graph: Adjacency list {node: [neighbors]}
            visited_nodes: Set các node đã thăm
            current_node: Node đang xét
            path: Đường đi hiện tại

        Returns:
            HTML string
        """
        if not PYVIS_AVAILABLE:
            return self._fallback_html("PyVis not installed")

        net = Network(
            height=self.height,
            width=self.width,
            directed=True,
            notebook=False,
            cdn_resources='in_line'
        )
        net.barnes_hut(gravity=-2000, spring_length=100)

        # Collect all nodes
        all_nodes = set(graph.keys())
        for targets in graph.values():
            all_nodes.update(targets)

        # Limit nodes for performance
        if len(all_nodes) > 200:
            all_nodes = set(list(all_nodes)[:200])

        path_set = set(path) if path else set()

        # Add nodes
        for node in all_nodes:
            color = self._get_node_color_str(node, visited_nodes, current_node, path_set)
            net.add_node(node, label=node, color=color, size=15, title=f"(k-1)-mer: {node}")

        # Add edges
        path_edges = set()
        if path and len(path) > 1:
            path_edges = {(path[i], path[i+1]) for i in range(len(path)-1)}

        for src, targets in graph.items():
            if src not in all_nodes:
                continue
            for dst in targets:
                if dst not in all_nodes:
                    continue
                edge_color = self.COLORS['edge_path'] if (src, dst) in path_edges else self.COLORS['edge_default']
                net.add_edge(src, dst, color=edge_color)

        return self._export_html(net)

    def _get_node_color(
        self,
        node_id: int,
        visited: Optional[Set[int]],
        current: Optional[int],
        path: Optional[List[int]]
    ) -> str:
        """Xác định màu node (int id)."""
        if current is not None and node_id == current:
            return self.COLORS['current']
        if path and node_id in path:
            return self.COLORS['path']
        if visited and node_id in visited:
            return self.COLORS['visited']
        return self.COLORS['unvisited']

    def _get_node_color_str(
        self,
        node: str,
        visited: Optional[Set[str]],
        current: Optional[str],
        path_set: Set[str]
    ) -> str:
        """Xác định màu node (string id)."""
        if current is not None and node == current:
            return self.COLORS['current']
        if node in path_set:
            return self.COLORS['path']
        if visited and node in visited:
            return self.COLORS['visited']
        return self.COLORS['unvisited']

    def _export_html(self, net: Any) -> str:
        """Export network to HTML string."""
        try:
            # Sử dụng generate_html() để lấy HTML trực tiếp, tránh lỗi encoding
            # PyVis >= 0.3.0 hỗ trợ generate_html()
            if hasattr(net, 'generate_html'):
                return net.generate_html()
            
            # Fallback: dùng temp file với binary mode để tránh encoding issues
            temp_path = tempfile.mktemp(suffix='.html')
            
            # Monkey-patch để force UTF-8 encoding
            import builtins
            original_open = builtins.open
            def utf8_open(*args, **kwargs):
                if len(args) > 1 and 'w' in str(args[1]) and 'b' not in str(args[1]):
                    kwargs.setdefault('encoding', 'utf-8')
                return original_open(*args, **kwargs)
            
            try:
                builtins.open = utf8_open
                net.save_graph(temp_path)
            finally:
                builtins.open = original_open

            with open(temp_path, 'r', encoding='utf-8') as f:
                html = f.read()

            os.unlink(temp_path)
            return html
        except Exception as e:
            return self._fallback_html(f"Error: {str(e)}")

    def _fallback_html(self, message: str) -> str:
        """Fallback HTML khi không render được."""
        return f"""
        <div style="padding: 20px; background: #f0f0f0; border-radius: 8px; text-align: center;">
            <p style="color: #666;">{message}</p>
            <p>Cài đặt PyVis: <code>pip install pyvis</code></p>
        </div>
        """

    @staticmethod
    def get_legend_html() -> str:
        """Trả về HTML cho legend giải thích màu sắc."""
        return """
        <div style="display: flex; gap: 15px; padding: 10px; background: #f5f5f5; border-radius: 5px; font-size: 12px; color: #333;">
            <span><span style="color: #9E9E9E;">●</span> Chưa thăm</span>
            <span><span style="color: #FFC107;">●</span> Đang xét</span>
            <span><span style="color: #4CAF50;">●</span> Đã thăm</span>
            <span><span style="color: #F44336;">●</span> Đường đi</span>
        </div>
        """
