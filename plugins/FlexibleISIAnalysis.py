"""ImprovedISIAnalysis (shortISI_v3) with all thresholds exposed in a dialog.

Same method as the original: a spike is flagged only if it has a short ISI AND
the spikes around it change in amplitude or in waveform. The difference is that
every threshold is editable instead of hard coded.

  alt+shift+f   opens a dialog with the five parameters

Parameters, in the order they appear in the dialog:

  isi_ms       short-ISI threshold in ms                      (original 1.5)
  amp_factor   amplitude change, in units of the cluster's
               own amplitude standard deviation               (original 1.5)
  wave_dist    waveform change, correlation distance          (original 0.1)
  min_spikes   do not split if fewer flagged spikes           (original 10)
  max_pct      do not split if more than this % of cluster    (original 50)

Raise amp_factor and wave_dist to flag fewer spikes.
The dialog remembers the last values used in this session.
"""

from phy import IPlugin, connect
from phy.gui import input_dialog
import numpy as np
import logging
from scipy.spatial.distance import cdist

logger = logging.getLogger('phy')


class FlexibleISIAnalysis(IPlugin):
    def attach_to_controller(self, controller):

        # Last values used, so the dialog reopens with them.
        last = {'text': '1.5 1.5 0.1 10 50'}

        def run(isi_ms, amp_factor, wave_dist, min_spikes, max_pct):
            cluster_ids = controller.supervisor.selected
            if not cluster_ids:
                logger.warn('No cluster selected')
                return

            bunchs = controller._amplitude_getter(cluster_ids, name='template', load_all=True)
            spike_ids = bunchs[0].spike_ids
            spike_times = controller.model.spike_times[spike_ids]
            spike_amps = bunchs[0].amplitudes

            try:
                data = controller.model._load_features().data[spike_ids]
                waveforms = np.reshape(data, (data.shape[0], -1))
            except Exception as e:
                logger.error('Could not load features: %s' % str(e))
                return

            n_spikes = len(spike_times)
            isi_threshold = float(isi_ms) / 1000.

            isi_prev = np.diff(spike_times, prepend=spike_times[0] - 1)
            isi_next = np.diff(spike_times, append=spike_times[-1] + 1)

            amp_sd = np.std(spike_amps)
            suspicious = np.zeros(n_spikes, dtype=bool)
            n_candidates = 0

            for i in range(n_spikes):
                if isi_prev[i] < isi_threshold or isi_next[i] < isi_threshold:
                    n_candidates += 1
                    window = slice(max(0, i - 1), min(n_spikes, i + 2))

                    amp_variation = np.std(spike_amps[window])

                    waves = waveforms[window]
                    wave_variation = np.mean(cdist(waves, waves, metric='correlation'))

                    if (amp_variation > amp_sd * float(amp_factor) or
                            wave_variation > float(wave_dist)):
                        suspicious[i] = True

            n_susp = int(suspicious.sum())
            logger.info('ISI < %s ms: %d candidate spikes, %d flagged by amplitude '
                        '(> %s SD) or waveform (> %s) change, out of %d spikes'
                        % (isi_ms, n_candidates, n_susp, amp_factor, wave_dist, n_spikes))

            if n_susp == 0:
                logger.info('Nothing to split')
                return
            if n_susp < float(min_spikes):
                logger.info('Fewer than %s flagged spikes, not splitting' % min_spikes)
                return
            if n_susp > n_spikes * float(max_pct) / 100.:
                logger.info('More than %s%% of the cluster flagged, not splitting' % max_pct)
                return

            labels = np.ones(n_spikes, dtype=int)
            labels[suspicious] = 2
            controller.supervisor.actions.split(spike_ids, labels)
            logger.info('Split %d flagged spikes into their own cluster' % n_susp)

        @connect
        def on_gui_ready(sender, gui):

            @controller.supervisor.actions.add(shortcut='alt+shift+f')
            def FlexibleISIAnalysis():
                """Open a dialog to set the five ISI analysis thresholds, then run."""
                text = input_dialog(
                    'Flexible ISI analysis',
                    'isi_ms  amp_factor  wave_dist  min_spikes  max_pct',
                    last['text'])
                if isinstance(text, (tuple, list)):
                    text = text[0] if text else None
                if not text:
                    return

                parts = str(text).split()
                if len(parts) != 5:
                    logger.warn('Expected 5 values: isi_ms amp_factor wave_dist '
                                'min_spikes max_pct')
                    return
                try:
                    values = [float(p) for p in parts]
                except ValueError:
                    logger.warn('All five values must be numbers')
                    return

                last['text'] = ' '.join(parts)
                run(*values)
