#!/usr/bin/env python3
"""
Final models for the VTA→hippocampus × motivated-memory analysis (ReadMe, Section C).

Reproduces the tables in §5b, §5c, §6b and §8 from the analysis-ready CSVs.

  1. Whole tract. NDI averaged over all 100 nodes, one value per subject per subregion,
     stacked long (two rows per subject: anterior, posterior). Mixed model:
         NDI ~ memory + subregion + ICV + tract length + streamline count + motion + age
     with a random intercept for subject; each row carries its own length and count.
     Fit by maximum likelihood. The interaction model adds memory × subregion and is
     compared by likelihood-ratio test (1 df). Main effect reported with the interaction dropped.
  2. Quartiles. Same model with NDI averaged within Q1 (nodes 0-24), Q2 (25-49),
     Q3 (50-74), Q4 (75-99).
  3. Metric comparison. The whole-tract model for ODI, FWF and FA.
  4. Hippocampal gray-matter NDI (corrected-dPar refit, scripts/run_noddi_gm.py), bilateral
     mean, regressed on each outcome with ICV, hippocampal volume, motion and age.
  5. HVLT. Collapsed whole-tract NDI (mean of both subregions) with each subregion's
     streamline count entered separately; trial 1, total recall, delayed recall.

Outcomes per domain: d′ (log-linear corrected), misattribution (false-alarm rate
residualised on criterion c), FABias (positive − negative false-alarm rate).

Out: data.check/final_models_summary.csv
"""
import os, warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import chi2, pearsonr

warnings.filterwarnings('ignore')

BASE = os.environ.get('MC_EXAMPLE_ROOT', './example_dataset/')  # root of the example dataset's analysis-ready files
BIL  = BASE + 'data.check/analysis_ready_bilateral/'
HPC  = BASE + 'Impact-Analyses/hpc_density_gm.csv'
VOL  = BASE + 'Impact-Analyses/hpc_volumes.csv'
OUT  = BASE + 'data.check/final_models_summary.csv'

COVS = ['ICV', 'Mean_tckstats', 'Count_tckstats', 'absolute_motion', 'maternal_age']
COV  = ' + '.join(COVS)
OUTCOMES = [('Social FABias', 'SOCIAL_FABias'),
            ('Social d′', 'SOCIAL_dprime_loglinear'),
            ('Social misattribution', 'SOCIAL_misattrib'),
            ('Monetary FABias', 'MONETARY_FABias'),
            ('Monetary d′', 'MONETARY_dprime_loglinear'),
            ('Monetary misattribution', 'MONETARY_misattrib')]
SEGMENTS = [('Q1', 0, 25), ('Q2', 25, 50), ('Q3', 50, 75), ('Q4', 75, 100), ('Whole', 0, 100)]
z = lambda s: (s - s.mean()) / s.std()


def load(metric):
    a = pd.read_csv(BIL + f'vta_anthipp__{metric}__analysis.csv')
    p = pd.read_csv(BIL + f'vta_posthipp__{metric}__analysis.csv')
    nodes = [c for c in a.columns if c.startswith(metric + '_') and c.split('_')[-1].isdigit()]
    return a, p, nodes


def outcomes_table():
    """Memory outcomes keyed by Subject; misattribution computed here for both domains."""
    ref = pd.read_csv(BIL + 'vta_anthipp__NDI__analysis.csv').copy()
    for dom in ['SOCIAL', 'MONETARY']:
        m = ref[[f'{dom}_fa', f'{dom}_criterion']].dropna()
        ref[f'{dom}_misattrib'] = np.nan
        ref.loc[m.index, f'{dom}_misattrib'] = smf.ols(f'{dom}_fa ~ {dom}_criterion', m).fit().resid
    return ref[['Subject'] + [o for _, o in OUTCOMES] +
               ['hvlt_trial1', 'hvlt_totalrecall', 'hvlt_delayedrecall']]


Y = outcomes_table()


def long_frame(metric, lo, hi):
    a, p, nodes = load(metric)
    rows = []
    for sub, df in [('anterior', a), ('posterior', p)]:
        t = df[['Subject'] + COVS].copy()
        t['M'] = df[nodes].values.astype(float)[:, lo:hi].mean(1)
        t['subregion'] = sub
        rows.append(t.merge(Y, on='Subject', how='left'))
    return pd.concat(rows, ignore_index=True)


def mixed(L, o):
    d = L.dropna(subset=[o, 'M']).copy()
    d['Mz'] = z(d['M']); d['yz'] = z(d[o])
    m0 = smf.mixedlm(f'Mz ~ yz + subregion + {COV}', d, groups=d.Subject).fit(reml=False)
    m1 = smf.mixedlm(f'Mz ~ yz*subregion + {COV}', d, groups=d.Subject).fit(reml=False)
    p_int = chi2.sf(max(2 * (m1.llf - m0.llf), 0), 1)
    return p_int, m0.params['yz'], m0.pvalues['yz'], int(len(d) / 2)


rows = []
print('=== 1. WHOLE TRACT, NDI: memory × subregion mixed model ===')
print(f"  {'outcome':24s} {'n':>3s} {'interaction p':>14s} {'main b':>8s} {'main p':>8s}")
L = long_frame('NDI', 0, 100)
for lbl, o in OUTCOMES:
    pi, b, pm, n = mixed(L, o)
    rows.append(dict(analysis='whole_tract', metric='NDI', segment='Whole', outcome=lbl,
                     n=n, interaction_p=pi, main_b=b, main_p=pm))
    print(f"  {lbl:24s} {n:3d} {pi:14.3f} {b:+8.3f} {pm:8.4f}{' *' if pm < .05 else ''}")

print('\n=== 2. QUARTILES, NDI ===')
seg = {}
for s, lo, hi in SEGMENTS:
    Ls = long_frame('NDI', lo, hi)
    for lbl, o in OUTCOMES:
        seg[(s, lbl)] = mixed(Ls, o)
        if s != 'Whole':
            pi, b, pm, n = seg[(s, lbl)]
            rows.append(dict(analysis='quartile', metric='NDI', segment=s, outcome=lbl,
                             n=n, interaction_p=pi, main_b=b, main_p=pm))
for title, k in [('interaction p', 0), ('main-effect p', 2)]:
    print(f"  -- {title}")
    print(f"  {'outcome':24s}" + ''.join(f"{s:>8s}" for s, _, _ in SEGMENTS))
    for lbl, _ in OUTCOMES:
        print(f"  {lbl:24s}" + ''.join(f"{seg[(s, lbl)][k]:8.3f}" for s, _, _ in SEGMENTS))

print('\n=== 3. METRIC COMPARISON, whole tract: main-effect p ===')
mets = ['NDI', 'ODI', 'FWF', 'FA']
comp = {}
for met in mets:
    Lm = long_frame(met, 0, 100)
    for lbl, o in OUTCOMES:
        comp[(met, lbl)] = mixed(Lm, o)
        rows.append(dict(analysis='metric', metric=met, segment='Whole', outcome=lbl,
                         n=comp[(met, lbl)][3], interaction_p=comp[(met, lbl)][0],
                         main_b=comp[(met, lbl)][1], main_p=comp[(met, lbl)][2]))
print(f"  {'outcome':24s}" + ''.join(f"{m:>8s}" for m in mets))
for lbl, _ in OUTCOMES:
    print(f"  {lbl:24s}" + ''.join(f"{comp[(m, lbl)][2]:8.3f}" for m in mets))

print('\n=== 4. HIPPOCAMPAL GRAY-MATTER NDI (corrected dPar), bilateral, +HPC volume ===')
h = pd.read_csv(HPC); v = pd.read_csv(VOL)
a0 = pd.read_csv(BIL + 'vta_anthipp__NDI__analysis.csv')[['Subject', 'ICV', 'absolute_motion', 'maternal_age']]
d = a0.merge(Y, on='Subject').merge(h[['Subject', 'L_HPC_NDI', 'R_HPC_NDI']], on='Subject') \
      .merge(v[['Subject', 'L_HPC_vol_mm3', 'R_HPC_vol_mm3']], on='Subject', how='left')
d['NDI'] = d[['L_HPC_NDI', 'R_HPC_NDI']].mean(axis=1)
d['HPCvol'] = d[['L_HPC_vol_mm3', 'R_HPC_vol_mm3']].sum(axis=1)
print(f"  {'outcome':24s} {'n':>3s} {'beta':>8s} {'p':>8s}")
for lbl, o in OUTCOMES:
    x = d[['NDI', 'ICV', 'absolute_motion', 'maternal_age', 'HPCvol', o]].dropna().copy()
    for c in x.columns: x[c] = z(x[c])
    m = smf.ols(f'{o} ~ NDI + ICV + absolute_motion + maternal_age + HPCvol', x).fit()
    rows.append(dict(analysis='hpc_gm_ndi', metric='NDI', segment='ROI', outcome=lbl,
                     n=int(m.nobs), interaction_p=np.nan, main_b=m.params['NDI'], main_p=m.pvalues['NDI']))
    print(f"  {lbl:24s} {int(m.nobs):3d} {m.params['NDI']:+8.3f} {m.pvalues['NDI']:8.4f}"
          f"{' *' if m.pvalues['NDI'] < .05 else ''}")

print('\n=== 5. HVLT: collapsed whole-tract NDI, each subregion count entered separately ===')
a, p, nodes = load('NDI')
D = pd.DataFrame({'Subject': a['Subject'],
                  'WHOLE': (a[nodes].values.mean(1) + p[nodes].values.mean(1)) / 2,
                  'ICV': a['ICV'], 'mot': a['absolute_motion'], 'age': a['maternal_age'],
                  'len': (a['Mean_tckstats'] + p['Mean_tckstats']) / 2,
                  'cnt_a': a['Count_tckstats'], 'cnt_p': p['Count_tckstats']}).merge(Y, on='Subject')
for o, lbl in [('hvlt_trial1', 'HVLT trial 1'), ('hvlt_totalrecall', 'HVLT total recall'),
               ('hvlt_delayedrecall', 'HVLT delayed recall')]:
    x = D[['WHOLE', 'ICV', 'len', 'cnt_a', 'cnt_p', 'mot', 'age', o]].dropna().copy()
    for c in x.columns: x[c] = z(x[c])
    m = smf.ols(f'{o} ~ WHOLE + ICV + len + cnt_a + cnt_p + mot + age', x).fit()
    rows.append(dict(analysis='hvlt', metric='NDI', segment='Whole', outcome=lbl,
                     n=int(m.nobs), interaction_p=np.nan, main_b=m.params['WHOLE'], main_p=m.pvalues['WHOLE']))
    print(f"  {lbl:24s} {int(m.nobs):3d} {m.params['WHOLE']:+8.3f} {m.pvalues['WHOLE']:8.4f}"
          f"{' *' if m.pvalues['WHOLE'] < .05 else ''}")
hv = D[['hvlt_trial1', 'SOCIAL_dprime_loglinear']].dropna()
print(f"  r(HVLT trial 1, RAFT social d′) = {pearsonr(hv.iloc[:, 0], hv.iloc[:, 1])[0]:+.3f}  (n={len(hv)})")

pd.DataFrame(rows).to_csv(OUT, index=False)
print(f"\n-> wrote {OUT}")
