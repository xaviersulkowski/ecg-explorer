from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class QRSComplex:
    onset: int
    offset: int


@dataclass
class Annotation:
    path: Optional[str] = None
    r_peak_positions: np.ndarray[int] = field(default_factory=list)
    qrs_complex_positions: list[QRSComplex] = field(default_factory=list)

    @property
    def is_empty(self):
        return self.r_peak_positions is None or len(self.r_peak_positions) == 0

    @property
    def onsets(self):
        return [i.onset for i in self.qrs_complex_positions]

    @property
    def offsets(self):
        return [i.offset for i in self.qrs_complex_positions]
