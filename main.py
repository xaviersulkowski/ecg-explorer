from detectors.qrs_detectors import PanTompkinsDetector
from filters.ecg_signal_filter import BandPassEcgSignalFilter
from models.ecg import ECGContainer

from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle

import logging

logging.basicConfig(level=logging.INFO)

data = ECGContainer.from_dicom_file(
    # "./resources/20230131-170213/20230120-123756-95.dcm"
    "./resources/20230515-134025/20230512-141956-98655.dcm"
    # "./resources/20230217-133912/20230215-094910-62.dcm"
)

bp_filter = BandPassEcgSignalFilter()
r_detector = PanTompkinsDetector()

bp_filter.filter(data)
r_detector.detect(data)


fig, axes = plt.subplots(len(data.ecg_leads), sharex=True)
fig.suptitle("QRS complexes")

for i, lead in enumerate(data.ecg_leads):
    onsets = [i.onset for i in lead.ann.qrs_complex_positions]
    offsets = [i.offset for i in lead.ann.qrs_complex_positions]

    axes[i].plot(lead.waveform)
    axes[i].set_title(f"Lead: {lead.label}")
    axes[i].scatter(
        lead.ann.r_peak_positions,
        lead.waveform[lead.ann.r_peak_positions],
        c="red",
        marker="x",
    )

    for on, off in zip(onsets, offsets):
        axes[i].add_patch(
            Rectangle(
                (on, min(lead.waveform)),
                off - on,
                (abs(min(lead.waveform)) + max(lead.waveform)),
                facecolor=(1, 0, 0, 0.5),
                lw=2,
            )
        )

plt.subplots_adjust(bottom=0.05, top=0.93, hspace=0.5)
plt.show()
