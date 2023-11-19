from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class QRSComplex:
    onset: int
    offset: int


@dataclass
class Annotation:
    path: Optional[str] = None
    r_peak_positions: Optional[np.ndarray[int]] = None
    qrs_complex_positions: Optional[list[QRSComplex]] = None
