"""Split short-ISI spikes out of a cluster so they can be removed.

Two actions, so you choose which spikes are selected:

  alt+shift+o   or snippet  :rsi1 <ms>    the earlier spike of each violating pair
  alt+shift+b   or snippet  :rsi2 <ms>    both spikes of each violating pair

The shortcut uses the default threshold of 3 ms. To use another value, type the
snippet in the GUI, for example  :rsi2 1.5  then Enter. No restart needed.

The flagged spikes are split into their own cluster. Nothing is deleted: press
alt+n to move that cluster to noise, or ctrl+z to undo the split.
"""

from phy import IPlugin, connect
import numpy as np
import logging

logger = logging.getLogger('phy')


class RemoveShortISI(IPlugin):
    def attach_to_controller(self, controller):

        def flag_short_isi(isi_ms, both):
            """Split the short-ISI spikes of the first selected cluster."""

            # Selected clusters across the cluster view and similarity view.
            cluster_ids = controller.supervisor.selected
            if not cluster_ids:
                logger.warn('No cluster selected')
                return

            # Same controller method as the amplitude view. load_all=True loads all
            # spikes of the selected clusters, not only the displayed selection.
            bunchs = controller._amplitude_getter(cluster_ids, name='template', load_all=True)

            # Spike ids and spike times of the first selected cluster.
            spike_ids = bunchs[0].spike_ids
            spike_times = controller.model.spike_times[spike_ids]
            dspike_times = np.diff(spike_times)

            # Index i of dspike_times is the gap between spike i and spike i+1.
            idx = np.where(dspike_times < float(isi_ms) / 1000.)[0]

            labels = np.ones(len(spike_ids), 'int64')
            labels[idx] = 2
            if both:
                labels[idx + 1] = 2

            n_flagged = int((labels == 2).sum())
            logger.info('Found %d spikes with ISI less than %s ms (%s of each pair)'
                        % (n_flagged, isi_ms, 'both' if both else 'first'))

            if n_flagged == 0:
                logger.info('Nothing to split')
                return

            assert spike_ids.shape == labels.shape
            controller.supervisor.actions.split(spike_ids, labels)
            logger.info('Split %d short ISI spikes into their own cluster' % n_flagged)

        @connect
        def on_gui_ready(sender, gui):

            @controller.supervisor.actions.add(shortcut='alt+shift+o', alias='rsi1')
            def RemoveShortISI_first(isi_ms=3):
                """Split off the EARLIER spike of each pair closer than the given ISI (ms)."""
                flag_short_isi(isi_ms, both=False)

            @controller.supervisor.actions.add(shortcut='alt+shift+b', alias='rsi2')
            def RemoveShortISI_both(isi_ms=3):
                """Split off BOTH spikes of each pair closer than the given ISI (ms)."""
                flag_short_isi(isi_ms, both=True)
