"""
Animation Controller cho step-by-step visualization.

Quản lý trạng thái thuật toán để hiển thị từng bước:
- Next/Previous step navigation
- Speed control
- Progress tracking
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Any, Optional, Union
from src.assembly.olc import OLCState
from src.assembly.dbg import DBGState


class AnimationPhase(Enum):
    """Các phase của thuật toán."""
    IDLE = "idle"
    OVERLAP = "overlap"
    GRAPH = "graph"
    PATH = "path"
    CONSENSUS = "consensus"
    KMER = "kmer"
    EULER = "euler"
    RECONSTRUCT = "reconstruct"


@dataclass
class AnimationFrame:
    """
    Một frame trong animation.

    Chứa thông tin cần thiết để render visualization tại một thời điểm.
    """
    phase: AnimationPhase
    step_index: int
    total_steps: int
    message: str
    # Data for visualization
    highlighted_nodes: List[Any] = field(default_factory=list)
    highlighted_edges: List[Any] = field(default_factory=list)
    current_path: List[Any] = field(default_factory=list)
    extra_data: dict = field(default_factory=dict)


class AnimationController:
    """
    State machine điều khiển animation từng bước.

    Nhận states từ OLCAssembler/DBGAssembler.get_step_states()
    và cung cấp interface để navigate qua các steps.
    """

    def __init__(self, states: Optional[List[Union[OLCState, DBGState]]] = None):
        self._raw_states = states or []
        self._frames = self._convert_to_frames(self._raw_states)
        self._current_index = 0
        self._speed = 1.0  # seconds per step
        self._is_playing = False

    def _convert_to_frames(self, states: List[Union[OLCState, DBGState]]) -> List[AnimationFrame]:
        """Convert OLCState/DBGState to AnimationFrame."""
        frames = []
        for i, state in enumerate(states):
            phase = self._get_phase(state)
            frame = AnimationFrame(
                phase=phase,
                step_index=i,
                total_steps=len(states),
                message=getattr(state, 'message', ''),
                current_path=list(getattr(state, 'path', [])),
                extra_data={'raw_state': state}
            )
            frames.append(frame)
        return frames

    def _get_phase(self, state: Union[OLCState, DBGState]) -> AnimationPhase:
        """Determine phase from state."""
        phase_str = getattr(state, 'phase', 'idle')
        phase_map = {
            'overlap': AnimationPhase.OVERLAP,
            'layout': AnimationPhase.PATH,
            'consensus': AnimationPhase.CONSENSUS,
            'kmer': AnimationPhase.KMER,
            'graph': AnimationPhase.GRAPH,
            'euler': AnimationPhase.EULER,
            'reconstruct': AnimationPhase.RECONSTRUCT,
        }
        return phase_map.get(phase_str, AnimationPhase.IDLE)

    @property
    def current_frame(self) -> Optional[AnimationFrame]:
        """Frame hiện tại."""
        if not self._frames:
            return None
        return self._frames[self._current_index]

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def total_frames(self) -> int:
        return len(self._frames)

    @property
    def is_first(self) -> bool:
        return self._current_index == 0

    @property
    def is_last(self) -> bool:
        return self._current_index >= len(self._frames) - 1

    @property
    def progress(self) -> float:
        """Progress từ 0.0 đến 1.0."""
        if not self._frames:
            return 0.0
        return (self._current_index + 1) / len(self._frames)

    @property
    def progress_percent(self) -> int:
        """Progress dạng phần trăm."""
        return int(self.progress * 100)

    def next_step(self) -> Optional[AnimationFrame]:
        """Tiến đến frame tiếp theo."""
        if not self.is_last:
            self._current_index += 1
        return self.current_frame

    def prev_step(self) -> Optional[AnimationFrame]:
        """Quay lại frame trước."""
        if not self.is_first:
            self._current_index -= 1
        return self.current_frame

    def go_to_step(self, index: int) -> Optional[AnimationFrame]:
        """Nhảy đến frame cụ thể."""
        if self._frames:
            self._current_index = max(0, min(index, len(self._frames) - 1))
        return self.current_frame

    def reset(self) -> Optional[AnimationFrame]:
        """Reset về đầu."""
        self._current_index = 0
        return self.current_frame

    def go_to_end(self) -> Optional[AnimationFrame]:
        """Nhảy đến cuối."""
        if self._frames:
            self._current_index = len(self._frames) - 1
        return self.current_frame

    @property
    def speed(self) -> float:
        return self._speed

    def set_speed(self, speed: float):
        """Set tốc độ (seconds per step)."""
        self._speed = max(0.1, min(5.0, speed))

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    def play(self):
        self._is_playing = True

    def pause(self):
        self._is_playing = False

    def toggle_play(self):
        self._is_playing = not self._is_playing

    def get_phase_summary(self) -> dict:
        """Thống kê số frames theo phase."""
        summary = {}
        for frame in self._frames:
            phase = frame.phase.value
            summary[phase] = summary.get(phase, 0) + 1
        return summary

    def has_frames(self) -> bool:
        return len(self._frames) > 0
