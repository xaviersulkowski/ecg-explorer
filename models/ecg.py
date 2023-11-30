import logging

import numpy as np
import pydicom as dicom

from dataclasses import dataclass, field
from typing import Any, Optional, Collection

from models.annotation import Annotation


@dataclass
class ECGLead:
    label: str
    raw_waveform: np.ndarray[float]
    waveform: Optional[np.ndarray[float]] = None
    units: Optional[str] = None
    fs: Optional[float] = None  # sampling frequency in Hz
    is_filtered: bool = False

    ann: Annotation = field(default_factory=Annotation)

    def __repr__(self):
        return f"\n{self.label}: \n\tunits: {self.units} \n\tsampling: {self.fs}Hz \n\tdata: {self.waveform}\n"

    def calculate_qrs_lengths(self):
        return [(pos.offset - pos.onset)/self.fs*1000 for pos in self.ann.qrs_complex_positions or []]

    def calculate_qrs_areas(self):
        return [np.round(np.trapz(np.abs(self.raw_waveform[pos.onset:pos.offset])), decimals=2) for pos in self.ann.qrs_complex_positions or []]


class ECGContainer:
    def __init__(self, ecg_leads: Collection[ECGLead], raw: Any):
        self.ecg_leads: Collection[ECGLead] = ecg_leads
        self.raw: Any = raw

    @property
    def n_leads(self): return len(self.ecg_leads)

    @classmethod
    def from_dicom_file(cls, path: str):
        try:
            raw = dicom.dcmread(path)
        except Exception as e:
            logging.warning(f"Couldn't read dicom file: {path}. Reason: {e}")
            raise e
        else:
            logging.info(f"Loaded file successfully")

        waveform = raw.WaveformSequence[0]
        waveform_data = raw.waveform_array(0)
        leads = list()

        for ii, channel in enumerate(waveform.ChannelDefinitionSequence):
            label = channel.ChannelLabel
            units = None
            if "ChannelSensitivity" in channel:  # Type 1C, may be absent
                units = channel.ChannelSensitivityUnitsSequence[0].CodeMeaning

            leads.append(
                ECGLead(label, waveform_data[:, ii], None, units, waveform.SamplingFrequency)
            )

        return cls(leads, raw)
