"""Package recorded visual observations; does not infer verdicts or edit geometries."""
import hashlib
import html
import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASK = Path(__file__).resolve().parent
SOURCE = ROOT / "workspace/reviews/option_b_simple_variations_20261018_v2"
OUT = ROOT / "workspace/reviews/option_b_visual_audit_20261019"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    observations = [json.loads(line) for line in (TASK / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
    scope = json.loads((TASK / "scope.json").read_text(encoding="utf-8"))
    report = json.loads((SOURCE / "report.json").read_text(encoding="utf-8"))
    manifest = {r["candidate_id"]: r for r in json.loads((SOURCE / "visual_manifest.json").read_text(encoding="utf-8"))}
    decisions = {r["candidate_id"]: r for r in report["decisions"]}
    ids = [r["candidate_id"] for r in observations]
    assert len(ids) == len(set(ids)) == 216
    assert set(ids) == set(scope["ids"]) == set(manifest) == set(decisions)
    assert sum(len(r["alternatives"]) for r in decisions.values()) == 1026
    labels = {"PLAUSIBLE": "Plauzibil vizual", "REVIEW": "Necesită verificare", "INCORRECT": "Eroare vizibilă"}
    rows = []
    for observation in observations:
        cid = observation["candidate_id"]
        original = manifest[cid]
        digest = sha(SOURCE / original["path"])
        assert digest == original["sha256"], cid
        assert observation["visual_status"] in labels
        assert observation["owner_verdict"] == "UNCHANGED_PENDING"
        decision = decisions[cid]
        rows.append({**observation, "image_path": str((SOURCE / original["path"]).relative_to(ROOT)).replace("\\", "/"),
                     "image_sha256": digest, "nodes_before": decision["nodes_before"], "nodes_after": decision["nodes_after"],
                     "selected_algorithm_decision": decision["selected"], "alternative_count": len(decision["alternatives"]),
                     "alternatives_geometry_seen_in_sheet": True,
                     "individual_alternative_owner_verdicts": None})
    counts = dict(Counter(r["visual_status"] for r in rows))
    summary = {"date": "2026-10-19", "scope": "All 216 current B case sheets, before/selected and 1026 displayed alternatives",
               "visual_cases_reviewed": len(rows), "displayed_alternatives": 1026, "counts": counts,
               "is_measured_accuracy": False, "is_owner_acceptance": False, "geometry_edits": False,
               "review_basis": "Visual inspection of original 1710x855 rendered sheets; no native-source measurement or independent field truth",
               "limits": ["Some variant captions overlap; full algorithm reasons remain in source report.json",
                          "One observation per case; no separate acceptance verdict for each alternative",
                          "Only current B v2 and previous geometry shown beside it; not every archived experimental run",
                          "216 candidates include overlapping parts/whole hypotheses; not 216 proven distinct buildings",
                          "Missing buildings outside supplied cases were not exhaustively surveyed"],
               "source_files": {name: sha(SOURCE / name) for name in ("report.json", "visual_manifest.json", "simple_variations.gpkg")}}
    # Ensure this packaging step did not adopt a modified GIS output relative to the checkpoint.
    rel_gpkg = str((SOURCE / "simple_variations.gpkg").relative_to(ROOT)).replace("\\", "/")
    committed = subprocess.check_output(["git", "show", "HEAD:" + rel_gpkg], cwd=ROOT)
    assert hashlib.sha256(committed).hexdigest() == summary["source_files"]["simple_variations.gpkg"]
    summary["active_gpkg_matches_head"] = True
    OUT.mkdir(parents=True, exist_ok=True)
    (TASK / "audit.json").write_text(json.dumps({"summary": summary, "cases": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (TASK / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    esc = html.escape
    parts = ['<!doctype html><html lang="ro"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
             '<title>StratumRO — audit vizual integral B</title>',
             '<style>body{font:17px/1.55 system-ui,sans-serif;max-width:1450px;margin:32px auto;padding:0 24px;color:#182334;background:#f5f7fa}a{color:#064eab}h1{font-size:30px}h2{margin-top:36px}article{background:white;border:1px solid #ccd3dd;border-left:6px solid #926300;padding:20px;margin:24px 0}article.INCORRECT{border-left-color:#b91c1c}article.PLAUSIBLE{border-left-color:#287443}img{width:100%;height:auto;border:1px solid #ddd}table{border-collapse:collapse;background:white;width:100%}td,th{border:1px solid #ccd3dd;padding:10px;text-align:left}nav a{display:inline-block;margin:6px 16px 6px 0}small{color:#485467}summary{cursor:pointer}code{overflow-wrap:anywhere} .status{font-weight:bold}</style>',
             '<h1>Audit vizual integral al opțiunii B</h1><p>216/216 planșe inspectate, înainte/după și 1.026 variante afișate. Data: 19 octombrie 2026.</p>',
             '<p><strong>Verdict: B necesită corecții înainte de livrarea automată.</strong> Auditul nu modifică geometriile, selecția activă sau acceptările proprietarului.</p>',
             '<table><tr><th>Concluzie de inspecție</th><th>Cazuri</th><th>Interpretare</th></tr>']
    for status, explanation in [("INCORRECT", "Eroare vizibilă în rezultatul prezentat, inclusiv fragmente sau fals candidat."), ("REVIEW", "Incertitudini de contur, identitate, ocluzie sau completitudine; nu echivalează cu respins."), ("PLAUSIBLE", "Coerent vizual la scara planșei; nu este acceptare cadastrală sau a proprietarului.")]:
        parts.append(f'<tr><td>{labels[status]}</td><td>{counts[status]}</td><td>{explanation}</td></tr>')
    parts.extend(['</table><p>Aceste numere nu măsoară acuratețea modelului. Cazurile pot include aripi, componente suprapuse și același obiect în ipoteze diferite.</p>',
                  '<h2>Ce trebuie rezolvat</h2><ol><li>Identificarea acoperișului complet înainte de simplificare: B120, B143, B176, B204.</li><li>Falsuri pe arbori, platforme și șantier: B024, B066, B192, B210.</li><li>Protejarea retragerilor reale: B035, B049, B055, B096, B109; numărul minim de noduri nu decide singur.</li><li>Relații parte–întreg și suprapuneri: B126/B174, B154/B169/B215, B151/B190.</li><li>Goluri de echipament și zgomot confundate cu curți: B043, B068, B110, B157.</li><li>Citire completă peste NoData înainte de un contur final: B180–B184, B197, B213.</li></ol>',
                  '<p><a href="../option_b_simple_variations_20261018_v2/index.html">Raportul B original</a> · <a href="../option_b_simple_variations_20261018_v2/report.json">Deciziile algoritmului și motivele integrale</a></p>',
                  '<details><summary>Metodă și limite</summary><p>Am inspectat toate planșele originale 1710 × 855, comparând conturul anterior, selecția și variantele vizibile. Unele texte ale variantelor sunt suprapuse în planșe; motivele integrale se citesc în JSON-ul original. Observația este la nivel de caz; nu atribuie un verdict independent fiecăreia dintre cele 1.026 variante.</p><p>Nu am făcut măsurători pe sursa nativă, verificare de teren, verificare cadastrală sau inventar exhaustiv al clădirilor omise. Istoricul tuturor rulărilor arhivate nu este certificat prin acest audit. Hash-ul fiecărei planșe este verificat; GeoPackage-ul activ este identic cu HEAD.</p></details>',
                  '<h2>Index complet</h2><p>Folosește căutarea browserului pentru identificator sau deschide o planșă la rezoluția originală.</p><nav>'])
    for r in rows:
        cid = r["candidate_id"]
        parts.append(f'<a href="#{cid}">{cid[4:9]} — {esc(labels[r["visual_status"]])}</a>')
    parts.append('</nav>')
    for r in rows:
        cid = r["candidate_id"]
        image_url = '../option_b_simple_variations_20261018_v2/images/' + Path(r["image_path"]).name
        decision = r["selected_algorithm_decision"]
        parts.extend([f'<article class="{r["visual_status"]}" id="{cid}"><h2>{cid}</h2>',
                      f'<p class="status">{esc(labels[r["visual_status"]])}</p><p>{esc(r["observation"])}</p>',
                      f'<p>{r["nodes_before"]} → {r["nodes_after"]} noduri; {r["alternative_count"]} variante afișate. Familie selectată de algoritm: {esc(decision.get("family", ""))}. Verdict proprietar: neschimbat, în așteptare.</p>',
                      f'<a href="{image_url}"><img loading="lazy" width="1710" height="855" src="{image_url}" alt="{cid}: anterior, selectat și alternative"></a>',
                      f'<details><summary>Proveniență</summary><small>SHA-256 planșă: <code>{r["image_sha256"]}</code></small></details></article>'])
    parts.append('</html>')
    (OUT / "index.html").write_text('\n'.join(parts) + '\n', encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
