"""Scan all clusters for near-zero-lag co-firing with the selected cluster.

Same neuron recorded on two wires gives coincidences at essentially zero lag,
because it is the same physical event. Two different neurons do not.

  alt+shift+n   or snippet  :coinc <ms>

The window is a half-width in ms (0.5 by default). For every other cluster the
action counts how many of its spikes fall within +/- window of a spike of the
selected cluster, compares that with the count expected by chance, and logs the
clusters sorted by that ratio, with the best channel of each.

Nothing is changed in the clustering. This only reports numbers to the log.
"""

from phy import IPlugin, connect
import numpy as np
import logging

logger = logging.getLogger('phy')


class CoincidenceScan(IPlugin):
    def attach_to_controller(self, controller):

        @connect
        def on_gui_ready(sender, gui):

            @controller.supervisor.actions.add(shortcut='alt+shift+n', alias='coinc')
            def CoincidenceScan(window_ms=0.5):
                """Report clusters co-firing with the selected cluster within +/- window_ms."""

                cluster_ids = controller.supervisor.selected
                if not cluster_ids:
                    logger.warn('No cluster selected')
                    return
                ref = cluster_ids[0]

                # Current clustering, so manual merges and splits are taken into account.
                clustering = controller.supervisor.clustering
                sc = clustering.spike_clusters
                st = controller.model.spike_times

                w = float(window_ms) / 1000.
                duration = st.max() - st.min()

                t_ref = np.sort(st[sc == ref])
                if len(t_ref) == 0:
                    logger.warn('Selected cluster has no spikes')
                    return

                rows = []
                for cid in clustering.cluster_ids:
                    if cid == ref:
                        continue
                    t = np.sort(st[sc == cid])
                    if len(t) == 0:
                        continue

                    # For each spike of cid, how many spikes of ref fall within +/- w.
                    left = np.searchsorted(t_ref, t - w, side='left')
                    right = np.searchsorted(t_ref, t + w, side='right')
                    n_obs = int((right - left).sum())
                    if n_obs == 0:
                        continue

                    # Chance expectation for two independent Poisson trains.
                    n_exp = len(t_ref) * len(t) * 2. * w / duration
                    ratio = n_obs / n_exp if n_exp > 0 else np.inf

                    rows.append((ratio, cid, len(t), n_obs, n_exp))

                rows.sort(reverse=True)

                logger.info('Coincidences with cluster %d (ch %s), window +/- %s ms, %d spikes'
                            % (ref, controller.get_best_channel(ref), window_ms, len(t_ref)))
                logger.info('  cluster   ch   n_spikes    obs      exp    ratio')
                for ratio, cid, n, n_obs, n_exp in rows[:20]:
                    logger.info('  %7d  %3s  %9d  %5d  %7.1f  %7.1f'
                                % (cid, controller.get_best_channel(cid), n, n_obs, n_exp, ratio))
