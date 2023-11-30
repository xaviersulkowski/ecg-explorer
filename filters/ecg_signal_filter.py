import numpy as np

from scipy import signal

from models.ecg import ECGContainer, ECGLead


class BandPassEcgSignalFilter:
    def __init__(self):
        self.filter_lowcut_frequency = 5.0
        self.filter_highcut_frequency = 15.0
        self.filter_order = 1

    def filter(self, ecg: ECGContainer):
        for lead in ecg.ecg_leads:
            lead.waveform = self._do_filter(lead)
            lead.is_filtered = True

    def _do_filter(self, lead: ECGLead):
        fs = lead.fs
        ecg_signal = lead.raw_waveform

        filtered = self._bandpass_filtering(
            ecg_signal,
            fs,
            self.filter_lowcut_frequency,
            self.filter_highcut_frequency,
            self.filter_order,
        )
        filtered[:5] = filtered[5]
        return filtered

    @staticmethod
    def _bandpass_filtering(
        ecg_signal: np.ndarray,
        fs: float,
        lowcut_frequency: float,
        highcut_frequency: float,
        filter_order: int,
    ) -> np.ndarray:
        nyquist_frequency = 0.5 * fs
        low = lowcut_frequency / nyquist_frequency
        high = highcut_frequency / nyquist_frequency
        b, a = signal.butter(filter_order, [low, high], btype="bandpass")
        return signal.lfilter(b, a, ecg_signal)
