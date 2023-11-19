import logging
import numpy as np
from scipy import signal

from models.annotation import QRSComplex
from models.ecg import ECGContainer, ECGLead


class PanTompkinsDetector:
    """
    Credits:
    Pan, J. and Tompkins, W., 1985. A Real-Time QRS Detection Algorithm. IEEE Transactions on Biomedical Engineering,
    BME-32(3), pp.230-236.

    PanTompkins algorithm steps:
        1. Signal bandpass filtering.
        2. Signal differentiation.
        3. Signal powering
        4. Signal integration.
        5. R-peak selection.
        6. QRS detection.

    """

    def __init__(self):
        self.window_size = 150  # PanTompkins processing window size = milliseconds
        self.min_peak_distance = 200  # milliseconds
        self.max_qrs_width = 120  # milliseconds

    def detect(self, ecg: ECGContainer):
        for lead in ecg.ecg_leads:
            logging.info(f"Detecting R peaks for: {lead.label}")
            r_peak_indices = self._detect_r_peaks(lead)
            lead.ann.r_peak_positions = r_peak_indices
            qrs_complexes = self._detect_qrs_onset_and_offset(lead)
            lead.ann.qrs_complex_positions = qrs_complexes

    def _detect_r_peaks(self, lead: ECGLead):
        window_size_samples = int(self.window_size * lead.fs / 1000)
        peak_distance_samples = int(self.min_peak_distance * lead.fs / 1000)

        # STEP 1: Signal filtering
        if lead.is_filtered is not True:
            raise Exception(
                "Signal must be filtered. Make sure to run bandpass filtering first."
            )

        ecg_signal = lead.waveform

        # STEP 2: Derivative
        features_signal = np.ediff1d(ecg_signal)

        # differentiation remove one sample, so we add zero to keep the original size
        features_signal = np.insert(features_signal, 0, 0)

        # STEP 3: Squaring
        features_signal = features_signal**2

        # STEP 4: Moving-window integration.
        features_signal = np.convolve(features_signal, np.ones(window_size_samples))

        # STEP 5: Peaks selection.

        # default wavelet is "ricker" aka "mex hat"
        peak_candidates = signal.find_peaks_cwt(
            vector=features_signal, widths=peak_distance_samples
        )

        peak_indices = self._adjust_peaks(
            ecg_signal, peak_candidates, int(peak_distance_samples / 2)
        )

        return peak_indices

    def _detect_qrs_onset_and_offset(self, lead: ECGLead) -> list[QRSComplex]:
        if lead.ann.r_peak_positions is None:
            raise Exception("R peaks must be detected!")

        ecg_signal = lead.waveform
        r_peaks = lead.ann.r_peak_positions

        peak_distance_samples = int(self.min_peak_distance * lead.fs / 1000)

        qrs_onsets = np.zeros(shape=r_peaks.shape, dtype=np.int64)
        qrs_offsets = np.zeros(shape=r_peaks.shape, dtype=np.int64)

        shift = int(peak_distance_samples / 2)

        for i, peak in enumerate(r_peaks):
            window_start = max(0, peak - shift)
            window_end = min(peak + shift, ecg_signal.size)
            window = ecg_signal[window_start:window_end]

            relative_peak_position = peak - window_start

            # TODO: adjust widths
            cwt = signal.cwt(window, wavelet=signal.wavelets.ricker, widths=(7,))
            cwt = np.squeeze(cwt)

            # second derivative to find zero crossing points,
            # padded with two zeros since each diff operation removes one sample
            cwt_diff_2 = np.insert(np.ediff1d(np.ediff1d(cwt)), [0, 1], [0, 0])
            zc_points = np.flatnonzero(np.diff(np.signbit(cwt_diff_2)))

            if isinstance(zc_points, tuple):
                zc_points = zc_points[0]

            r_peak_zc_idx = np.argmin(np.abs(zc_points - relative_peak_position))
            cwt_qrs_onset_idx = r_peak_zc_idx - 1
            cwt_qrs_offset_idx = r_peak_zc_idx + 1

            # TODO: if zc point not found, then we need to approximate QRS onset and offset using max qrs width
            #    and magnitude changes
            onset = zc_points[cwt_qrs_onset_idx]
            offset = zc_points[cwt_qrs_offset_idx]

            qrs_onsets[i] = peak - onset
            qrs_offsets[i] = peak + offset

        return [
            QRSComplex(onset=onset, offset=offset)
            for onset, offset in zip(qrs_onsets, qrs_offsets)
        ]

    @staticmethod
    def _adjust_peaks(
        data: np.ndarray[float], peaks: np.ndarray[int], shift: int = 120
    ) -> np.ndarray[int]:
        """
        Find local r-peaks using wavelet components
        """

        new_peaks = np.zeros(shape=peaks.shape, dtype=np.int64)

        for i, peak in enumerate(peaks):
            window_start = max(0, peak - shift)
            window_end = min(peak + shift, data.size)
            window = data[window_start:window_end]

            cwt = signal.cwt(window, wavelet=signal.wavelets.ricker, widths=(7,))
            cwt = np.squeeze(cwt)

            new_peaks[i] = window_start + np.argmax(np.abs(cwt))

        return new_peaks
