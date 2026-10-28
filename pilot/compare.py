"""Compare Kev with the stored Laya and Jev answers on the 1,534 pilot passages."""
import sys; sys.path.insert(0, ".")
import numpy as np
import pandas as pd
from labels import L

ID = "passage_id"
M = {n: pd.read_parquet(f).set_index(ID) for n, f in
     [("Laya", "pilot2-coded.parquet"), ("Jev", "pilot2-jev.parquet"), ("Kev", "pilot2-kev.parquet")]}
full = pd.read_parquet("../full/coded-jev.parquet").set_index(ID)
ids = M["Jev"].index
M = {n: m.loc[ids] for n, m in M.items()}
M["Jev full run"] = full.loc[ids]
crit = [c for c in M["Jev"].columns if c.startswith("crit_")]
choices = ["site", "direction", "evidence_type", "taxon", "zone", "pressure"]

# 1. Reference labels, as in score.py
s = pd.read_parquet("label-sample.parquet").reset_index(drop=True)
C = {"a": "crit_a_uniqueness", "c": "crit_c_life_history", "i": "crit_i_diversity_productivity",
     "n": "crit_n_processes", "q": "crit_q_impacts"}
print("## Against the 48 reference labels")
for name, m0 in M.items():
    m = m0.loc[s[ID]].reset_index()
    rc = [(m.content[i] > .5) == bool(L[i][0]) for i in range(48) if L[i][0] is not None]
    ok = [i for i in range(48) if L[i][0] == 1]
    site = sum(m.site[i] in L[i][1] for i in ok) / len(ok)
    tax = sum(m.taxon[i] in L[i][3] for i in ok) / len(ok)
    for th in (.5, .7):
        tp = fp = fn = 0
        for i in ok:
            for k, col in C.items():
                y, p = k in L[i][2], (m[col][i] > th) if pd.notna(m[col][i]) else False
                tp += y and p; fp += p and not y; fn += y and not p
        print(f"{name:13s} th={th}: content {sum(rc)}/{len(rc)}  site {site:.0%}  taxon {tax:.0%}  "
              f"recall {tp}/{tp+fn}  precision {tp}/{tp+fp}")
    print(f"{'':13s} strength SD {m0.strength.std():.2f}  content>0.5 {(m0.content > .5).sum()}")

# 2. Agreement with the stored Jev answers on all passages
def agree(a, b):
    out = {"content r": a.content.corr(b.content),
           "content agree": ((a.content > .5) == (b.content > .5)).mean()}
    both = (a.content > .5) & (b.content > .5)
    x, y = a.loc[both, crit], b.loc[both, crit]
    out["crit r (pooled)"] = np.corrcoef(x.values.ravel(), y.values.ravel())[0, 1]
    for th in (.5, .7):
        px, py = x > th, y > th
        out[f"crit flags/passage @{th}"] = px.values.sum() / both.sum()
        out[f"crit agree @{th}"] = (px == py).values.mean()
        tp = (px & py).values.sum()
        out[f"crit F1 vs Jev @{th}"] = 2 * tp / (px.values.sum() + py.values.sum())
    out["strength r"] = a.loc[both, "strength"].corr(b.loc[both, "strength"])
    for c in choices:
        w = both if c != "site" else slice(None)
        out[f"{c} agree"] = (a.loc[w, c] == b.loc[w, c]).mean()
    return out

print("\n## Agreement with the stored Jev answers (pilot2-jev) on 1,534 passages")
rows = {n: agree(M[n], M["Jev"]) for n in ["Laya", "Kev", "Jev full run"]}
print(pd.DataFrame(rows).round(2).to_string())

print("\n## Per-criterion correlation with Jev, passages both screened in")
both = lambda n: (M[n].content > .5) & (M["Jev"].content > .5)
pc = pd.DataFrame({n: [M[n].loc[both(n), c].corr(M["Jev"].loc[both(n), c]) for c in crit]
                   for n in ["Laya", "Kev"]}, index=crit)
pc["Kev rate>0.7"] = [(M["Kev"].loc[both("Kev"), c] > .7).mean() for c in crit]
pc["Jev rate>0.7"] = [(M["Jev"].loc[both("Kev"), c] > .7).mean() for c in crit]
print(pc.round(2).to_string())

print("\n## Site distribution")
print(pd.DataFrame({n: M[n].site.value_counts() for n in ["Laya", "Jev", "Kev"]}).fillna(0).astype(int).to_string())
print("\n## Mean probability spread (SD) of criteria, screened-in passages")
for n in ["Laya", "Jev", "Kev"]:
    m = M[n][M[n].content > .5]
    print(n, round(m[crit].stack().std(), 3), "mean", round(m[crit].stack().mean(), 3))
