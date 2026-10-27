import sys; sys.path.insert(0, ".")
import pandas as pd
from labels import L
s = pd.read_parquet("label-sample.parquet").reset_index(drop=True)
assert len(s) == len(L) == 48
C = {"a": "crit_a_uniqueness", "c": "crit_c_life_history", "i": "crit_i_diversity_productivity", "n": "crit_n_processes", "q": "crit_q_impacts"}
for name, f in [("Laya", "pilot2-coded.parquet"), ("Jev", "pilot2-jev.parquet")]:
    m = pd.read_parquet(f).set_index("passage_id").loc[s.passage_id].reset_index()
    rc = [(m.content[i] > .5) == bool(L[i][0]) for i in range(48) if L[i][0] is not None]
    ok = [i for i in range(48) if L[i][0] == 1]
    site = sum(m.site[i] in L[i][1] for i in ok) / len(ok)
    tax = sum(m.taxon[i] in L[i][3] for i in ok) / len(ok)
    tp = fp = fn = tn = 0
    for i in ok:
        for k, col in C.items():
            y, p = k in L[i][2], m[col][i] > .5
            tp += y and p; fp += p and not y; fn += y and not p; tn += not y and not p
    print(f"{name}: content {sum(rc)}/{len(rc)}  site {site:.0%}  taxon {tax:.0%}  criteria (a,c,i,n,q): "
          f"recall {tp}/{tp+fn}  precision {tp}/{tp+fp}  agreement {(tp+tn)/(tp+tn+fp+fn):.0%}")
