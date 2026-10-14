# phy2-plugins (Liu Lab)

Fork of [petersenpeter/phy2-plugins](https://github.com/petersenpeter/phy2-plugins)
with plugins added for human microwire curation at NYU.

Upstream was written by Peter Petersen (phy1), made compatible with phy2 by
Thomas Hainmueller, with later additions by Mingze Dou. The `liulab` branch adds
the plugins below and does not modify any upstream file.

## What is added

| Plugin | Class | Shortcut | What it does |
|---|---|---|---|
| `SplitShortISI.py` | `SplitShortISI` | `alt+shift+v`, `:vsi <ms>` | Upstream `VisualizeShortISI` with the ISI threshold passed at run time instead of fixed at 1.5 ms |
| `RemoveShortISI.py` | `RemoveShortISI` | `alt+shift+o`, `alt+shift+b` | Splits short-ISI spikes off so they can be moved to noise. Two actions: earlier spike of each pair, or both |
| `FlexibleISIAnalysis.py` | `FlexibleISIAnalysis` | `alt+shift+f` | Upstream `ImprovedISIAnalysis` with all five thresholds editable in a dialog |
| `CoincidenceScan.py` | `CoincidenceScan` | `alt+shift+n`, `:coinc <ms>` | Reports clusters co-firing with the selected cluster at near-zero lag, for finding the same neuron detected on two wires |

Nothing in this repository deletes spikes. Plugins split a cluster; moving the
split-off cluster to noise (`alt+n`) stays a manual decision.

## Install

1. Copy the plugin files into your phy user directory:
   - Linux / Mac: `~/.phy/plugins/`
   - Windows: `C:\Users\<YourUserName>\.phy\plugins\`
2. List the class names in `~/.phy/phy_config.py`:

```python
from phy import IPlugin

c = get_config()
c.Plugins.dirs = [r'~/.phy/plugins']
c.TemplateGUI.plugins = [
    'SplitShortISI',
    'RemoveShortISI',
    'FlexibleISIAnalysis',
    'CoincidenceScan',
]
```

3. Restart phy. Press `H` to confirm the shortcuts.

Copying a file into the folder is not enough. A plugin runs only if its **class**
name is in `c.TemplateGUI.plugins`. The filename does not matter.

## Two things that break silently

**Duplicate class names.** phy imports every `.py` file in the plugins folder.
If two files define the same class, the second registration wins and shortcuts
behave unpredictably. Upstream ships both `SplitShortISI.py` and
`SplitShortISI_v2.py`, which both define `class SplitShortISI`. Keep one.

**Overlapping shortcuts.** Upstream binds `ImprovedISIAnalysis` to `alt+i`.
The plugins here avoid `alt+i`, `alt+x`, `alt+k`, `alt+t` and the `alt+shift+k/t/q/x`
set that upstream already uses. After any change, press `H` and check that each
shortcut appears once.

## Plugin notes

### SplitShortISI

Splits spikes whose interspike interval is shorter than the threshold into a
separate cluster. For looking, not for cutting. Merge back or `ctrl+z` afterwards.

Flags the **earlier** spike of each violating pair only, since index `i` of
`np.diff` is the gap between spike `i` and `i+1`. The partner stays in the
main cluster.

`alt+shift+v` runs at 1.5 ms. `:vsi 3` runs at 3 ms.

If no spike falls under the threshold, every spike gets the same label and phy
renumbers the cluster instead of splitting it. That looks like nothing happened.

### RemoveShortISI

Same split, but with a choice of which spikes to take, and a guard that stops
if nothing is flagged.

- `alt+shift+o` or `:rsi1 <ms>` takes the earlier spike of each pair
- `alt+shift+b` or `:rsi2 <ms>` takes both spikes of each pair

Both default to 3 ms, the usual refractory criterion for human MTL units.

### FlexibleISIAnalysis

A spike is flagged only if it has a short ISI **and** the spikes around it change
in amplitude or in waveform. Timing alone cannot separate contamination from
bursting, which is the reason for the second test.

The dialog takes five numbers:

| Parameter | Upstream value | Meaning |
|---|---|---|
| `isi_ms` | 1.5 | Short-ISI threshold in ms |
| `amp_factor` | 1.5 | Local amplitude variation, in units of the cluster's own amplitude SD |
| `wave_dist` | 0.1 | Correlation distance between the feature vectors of neighbouring spikes |
| `min_spikes` | 10 | Refuse to split fewer flagged spikes than this |
| `max_pct` | 50 | Refuse to split if more than this percentage of the cluster is flagged |

Raise `amp_factor` and `wave_dist` to flag fewer spikes. The two tests are joined
by `or`, inherited from upstream, so loosening either one flags more.

The log reports candidates and flagged spikes separately, so a zero result tells
you whether there were no short ISIs or no physical change.

Uses `controller.model._load_features()`, a private method that can break between
phy versions. The failure is logged rather than swallowed.

### CoincidenceScan

For every cluster, counts how many of its spikes fall within a window of a spike
of the selected cluster, and compares that count with the chance expectation for
two independent Poisson trains. Prints the best channel of each cluster.

Reports only. Nothing is split, merged or labelled.

Reading the output:

- Judge by **fraction**, not by the ratio. The ratio assumes a constant firing
  rate over the whole recording, so any shared non-stationarity inflates every
  row at once.
- The same neuron on two wires overlaps at 50 to 90 percent, at a lag within one
  or two samples. Narrow the window (`:coinc 0.2`) and a duplicate keeps its
  fraction while synchrony and artifacts collapse.
- Many clusters on one channel elevated together points to a shared artifact or
  common drive, not duplication.
- Coincidences inflate the measured amplitude of **both** clusters, because each
  wire records the sum of the two spikes. So amplitude alone does not identify
  which wire owns the neuron.
- Do not use the correlogram view for this. phy removes the central bin, so an
  exact zero-lag duplicate is invisible there.

## Deciding between duplicate, split unit, and two neurons

| Evidence | Same neuron, two clusters | Two neurons |
|---|---|---|
| Cross-correlogram at zero | Refractory dip, matching the autocorrelograms | Fills in |
| Mean waveform footprint across channels | Same shape, same relative size on both channels | Opposite footprints, each large on its own wire |
| Feature view | One overlapping cloud | Separate clouds |
| Amplitude view | One band | Two bands |

Across wires the correlogram test is weaker, because a sorter that refuses to
assign two spikes to the same sample produces a dip without any shared neuron.
Weight the waveform comparison more for cross-wire pairs.

A narrow spike exactly at zero on an otherwise flat cross-correlogram is not an
interaction. It is the same physical event detected twice.

## Credit and licence

Upstream: https://github.com/petersenpeter/phy2-plugins
DOI: https://zenodo.org/badge/latestdoi/126424002

The upstream repository has no licence file. Check with the authors before
redistributing this fork publicly.
