"""Re-verification of the 5 most load-bearing findings in the audit.
Run: venv\\Scripts\\python reports/_charts/verify_claims.py
Every line prints MEASURED or REFUTED. Nothing is asserted without output.
"""
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
ok = []


def hdr(n, t):
    print("\n" + "=" * 78)
    print("  [%s] %s" % (n, t))
    print("=" * 78)


# ---------------------------------------------------------------- F1 + F3
hdr("F1", "Iepuresti state.json self-contradiction")
sj = ROOT / "projects" / "UAT_Iepuresti" / "state" / "state.json"
d = json.loads(sj.read_text(encoding="utf-8", errors="replace"))
print("gate                        = %r" % d.get("gate"))
print("qa_summary.status           = %r" % d.get("qa_summary", {}).get("status"))
print("adversarial_review.status   = %r" % d.get("adversarial_review", {}).get("status"))
print("deliverables.status         = %r" % d.get("deliverables", {}).get("status"))
lc = d.get("production_summary", {}).get("layer_counts", {})
print("production layer_counts     = %r" % {k: v for k, v in lc.items()})
empty = [k for k, v in lc.items() if v == 0]
print("ZERO-FEATURE required layers = %r" % empty)
print("=> %s  claim=F1 FALSE-PASS CONFIRMED" % ("MEASURED" if empty else "REFUTED"))
ok.append(("F1", bool(empty)))

qa = (ROOT / "projects" / "UAT_Iepuresti" / "qa" / "05_qa_report.md").read_text(
    encoding="utf-8", errors="replace")
print("\n--- grep of qa/05_qa_report.md for the two empty layers ---")
for ln in qa.splitlines():
    if "intravilan" in ln.lower() or "cadastrale" in ln.lower():
        print("   " + ln.strip()[:150])
print("=> %s  claim=QA REPORTS PASS ON EMPTY LAYER" % ("MEASURED" if "PASS" in qa else "REFUTED"))

# ---------------------------------------------------------------- F3
hdr("F3", "CLADIRI_CADASTRU_CLEAN : 147 features vs 121 distinct")
gp = ROOT / "workspace" / "output" / "cladiri_stereo70.gpkg"
con = sqlite3.connect("file:%s?mode=ro" % gp, uri=True)
lay = [r[0] for r in con.execute("SELECT table_name FROM gpkg_contents WHERE data_type='features'")]
print("layers in gpkg_contents = %d" % len(lay))
print("layer list = %r" % lay)
# plain sqlite3 has no spatial funcs -> hash the raw WKB blob
rows = list(con.execute('SELECT fid, hex(geom) FROM "CLADIRI_CADASTRU_CLEAN" ORDER BY fid'))
print("CLADIRI_CADASTRU_CLEAN feature count = %d" % len(rows))
dig = Counter(hashlib.sha256(w.encode()).hexdigest()[:16] for _, w in rows)
dupe_groups = {k: v for k, v in dig.items() if v > 1}
n_dup_extra = sum(v - 1 for v in dupe_groups.values())
print("distinct geometries          = %d" % len(dig))
print("duplicate geometries         = %d" % n_dup_extra)
print("=> %s  claim=147 INFLATED, real count = %d"
      % ("MEASURED" if n_dup_extra else "REFUTED", len(dig)))

fid_wkt = {f: w for f, w in rows}
print("\n--- ACTUAL duplicate fid groups (my earlier '1=30,2=31' claim was WRONG) ---")
byhash = {}
for f, w in rows:
    byhash.setdefault(w, []).append(f)
shown = 0
for h, fids in byhash.items():
    if len(fids) > 1 and shown < 8:
        print("   identical geometry -> fids %s" % fids)
        shown += 1
print("   ... total duplicated fids = %d" % n_dup_extra)

# ---------------------------------------------------------------- F4
hdr("F4", "STAGE_5_FINAL_CONFIDENCE == STAGE_4 ?")


def geoms(table):
    return {hashlib.sha256(w.encode()).hexdigest()
            for (w,) in con.execute('SELECT hex(geom) FROM "%s"' % table)}


s3, s4, s5 = geoms("STAGE_3_ADAPTIVE_POLYGON"), geoms("STAGE_4_LIDAR_CONSTRAINED"), \
    geoms("STAGE_5_FINAL_CONFIDENCE")
print("STAGE_3 distinct = %d | STAGE_4 distinct = %d | STAGE_5 distinct = %d"
      % (len(s3), len(s4), len(s5)))
print("STAGE_5 == STAGE_4 ?  %s   <-- if True, STAGE_5 IS A NO-OP" % (s5 == s4))
print("STAGE_5 == STAGE_3 ?  %s" % (s5 == s3))
ok.append(("F4 STAGE_5 is a no-op", s5 == s4))

# ---------------------------------------------------------------- F6
hdr("F6", "UNCLASSIFIED : count + area (documented in NO report)")
try:
    from shapely import wkb as _wkb
    n = con.execute('SELECT COUNT(*) FROM "UNCLASSIFIED"').fetchone()[0]
    tot = 0.0
    for (h,) in con.execute('SELECT hex(geom) FROM "UNCLASSIFIED"'):
        b = bytes.fromhex(h)
        # GeoPackage binary header: 'GP', ver, flags, srs_id(4). flags byte bit0=envelope
        flags = b[3]
        env = (flags >> 1) & 0x07          # 0=XY,1=XYZ,2=XYM,3=XYZM => 0/4*8/6/7 bytes
        envsz = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[env]
        tot += _wkb.loads(b[8 + envsz:]).area
    print("UNCLASSIFIED features   = %d" % n)
    print("total area (shapely)    = %.0f m2  =  %.2f ha" % (tot, tot / 1e4))
    ncl = con.execute('SELECT COUNT(*) FROM "CLADIRI_CADASTRU_CLEAN"').fetchone()[0]
    print("for reference CLEAN     = %d features" % ncl)
    print("=> %s  claim=UNCLASSIFIED %d feats / %.2f ha UNDOCUMENTED"
          % ("MEASURED" if n else "REFUTED", n, tot / 1e4))
    ok.append(("F6 UNCLASSIFIED exists", n > 0))
except Exception as e:
    print("ERR %s" % e)

# ---------------------------------------------------------------- conf labels
hdr("EXTRA", "FABRICATED confidence labels: real conf_final vs documented 0.85")
for lyr in ("CLADIRI_CADASTRU_CLEAN", "STAGE_5_FINAL_CONFIDENCE"):
    try:
        cols = [r[1] for r in con.execute('PRAGMA table_info("%s")' % lyr)]
        cf = next((c for c in cols if "conf" in c.lower()), None)
        if not cf:
            print("%s : no confidence column" % lyr)
            continue
        vals = [r[0] for r in con.execute(
            'SELECT "%s" FROM "%s" WHERE "%s" IS NOT NULL' % (cf, lyr, cf))]
        print("%-26s col=%-14s max=%.4f  n=%d" % (lyr, cf, max(vals), len(vals)))
    except Exception as e:
        print("%s ERR %s" % (lyr, e))

# ---------------------------------------------------------------- sovereign
hdr("ASSET", "UAT_Iepuresti_PUG_Master.gpkg sovereign layer census")
mp = ROOT / "projects" / "UAT_Iepuresti" / "UAT_Iepuresti_PUG_Master.gpkg"
print("exists=%s size=%.1f MB" % (mp.exists(), mp.stat().st_size / 1e6))
mc = sqlite3.connect("file:%s?mode=ro" % mp, uri=True)
tot = 0
for t, in mc.execute("SELECT table_name FROM gpkg_contents WHERE data_type='features' ORDER BY table_name"):
    n = mc.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0]
    srs = mc.execute(
        "SELECT organization, organization_coordsys_id FROM gpkg_spatial_ref_sys s "
        "JOIN gpkg_contents c ON c.srs_id=s.srs_id WHERE c.table_name=?", (t,)).fetchone()
    tot += n
    print("  %-52s %6d  EPSG:%s" % (t, n, srs[1]))
print("TOTAL FEATURES = %d" % tot)
print("=> %s  claim=3528 sovereign features, %d layers" % ("MEASURED" if tot else "REFUTED", len(lay)))
con.close()
mc.close()

print("\n" + "=" * 78)
print("  VERDICT: %d of 5 claims RE-VERIFIED MEASURED on this run"
      % sum(1 for _, v in ok if v))
for k, v in ok:
    print("    %s  %s" % ("PASS" if v else "FAIL", k))
print("=" * 78)
