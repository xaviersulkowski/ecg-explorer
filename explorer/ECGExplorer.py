import os
import statistics
from typing import Optional, Callable

import pandas as pd

from detectors.qrs_detectors import PanTompkinsDetector
from filters.ecg_signal_filter import FilterConfig, EcgSignalFilter
from models.annotation import QRSComplex
from models.ecg import ECGContainer, LeadName


class ECGExplorer:
    def __init__(
        self,
        container: ECGContainer,
        filter_config: Optional[FilterConfig] = None,
    ):

        self._container = container
        self._filter_config = filter_config
        self._filter: Optional[EcgSignalFilter] = EcgSignalFilter(filter_config) if filter_config else None
        self._r_detector = PanTompkinsDetector()

    @classmethod
    def load_from_file(
        cls,
        filepath: str,
        filter_config: Optional[FilterConfig] = None
    ):
        if not os.path.isfile(filepath):
            raise FileNotFoundError()

        ext = os.path.splitext(filepath)[-1].lower()

        if ext == ".dcm":
            return cls(ECGContainer.from_dicom_file(filepath), filter_config)
        if ext.lower() == ".xml":
            return cls(ECGContainer.from_ge_xml_file(filepath), filter_config)

    def process(self):
        self._filter.filter(self._container)
        self._r_detector.detect(self._container)

    @property
    def container(self):
        return self._container

    @property
    def filter_config(self):
        return self._filter_config

    @filter_config.setter
    def filter_config(self, filter_config: FilterConfig):
        self._filter_config = filter_config
        self._filter = EcgSignalFilter(self._filter_config)

    def overwrite_annotations(self, lead_name: LeadName, qrs: list[QRSComplex]):
        lead = self._container.get_lead(lead_name)
        if lead:
            lead.ann.qrs_complex_positions = qrs

    def generate_report(self) -> pd.DataFrame:
        def _padded(data: list, size: int) -> list:
            out = [None] * size
            for cnt, l in enumerate(data):
                out[cnt] = l
            return out

        def _safe_statistics(data: list[Optional[float]], statistic: Callable) -> Optional[float]:
            if len(data) > 0 and any([x is not None for x in data]):
                d = [x for x in data if x is not None]
                return float(f"{(statistic(d)):.2f}")
            else:
                return None

        report = pd.DataFrame()

        max_size = max(
            len(lead.ann.qrs_complex_positions) for lead in self._container.ecg_leads
        )

        for lead in self._container.ecg_leads:
            column_root = lead.label.lower().replace(" ", "_")

            qrs_lengths = _padded(lead.calculate_qrs_lengths(), max_size)
            # None to add one empty line before mean value
            qrs_lengths.extend([None, _safe_statistics(qrs_lengths, statistics.mean), _safe_statistics(qrs_lengths, statistics.stdev)])
            qrs_areas = _padded(lead.calculate_qrs_areas(), max_size)
            # None to add one empty line before mean value
            qrs_areas.extend([None, _safe_statistics(qrs_areas, statistics.mean), _safe_statistics(qrs_areas, statistics.stdev)])

            row_names = [str(x) for x in range(len(_padded(lead.calculate_qrs_lengths(), max_size)))]
            row_names.extend(["", "mean", "std"])

            report[f"index"] = pd.Series(row_names)
            report[f"{column_root}_width_ms"] = pd.Series(qrs_lengths)
            report[f"{column_root}_area_uV.s"] = pd.Series(qrs_areas)

        return report

    def save_annotations(self, filename):
        self._container.save_annotations(filename)

    def load_annotations(self, filename):
        self._container.load_annotations(filename)
