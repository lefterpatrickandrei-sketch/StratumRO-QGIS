"""Build a local visual review document from actual stage outputs, no services."""
import argparse,hashlib,html,json,re
from pathlib import Path

def build(out):
    out=Path(out).resolve();report=json.loads((out/'report.json').read_text())
    manifest=json.loads((out/'visual_manifest.json').read_text())
    assert len(manifest)==report['input_count']
    for item in manifest:
        assert hashlib.sha256((out/item['path']).read_bytes()).hexdigest()==item['sha256']
    rows=[]
    by_id={r['candidate_id']:r for r in report['decisions']}
    for item in manifest:
        d=by_id.get(item['final_id'],{})
        ident=html.escape(item['candidate_id']);path=html.escape(item['path'])
        reasons=html.escape('; '.join(d.get('review_reasons',[])) or 'Ipoteza simpla; necesita acceptare vizuala')
        rows.append(f'<tr><td><a href="{path}">{ident}</a></td><td>{html.escape(item["qa_status"])}</td><td>{d.get("nodes_before","—")} → {d.get("nodes_after","—")}</td><td>{reasons}</td></tr>')
    cards=[]
    for ident in ['OPT_B_046_C1','OPT_B_006_C1','OPT_B_154_C1','OPT_B_169_C1','OPT_B_120_C1','OPT_B_201_C1']:
        cards.append(f'<h3>{ident}</h3><a href="images/{ident}_stages.png"><img loading="lazy" src="images/{ident}_stages.png" alt="Etape {ident}"></a>')
    a=len(report['baseline_conflicts']);b=len(report['conflicts'])
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="760" height="150" viewBox="0 0 760 150"><rect width="760" height="150" fill="white"/><g font-family="sans-serif" font-size="17" fill="#183146"><text x="12" y="25">Perechi cu suprapunere &gt; 0,05 m² (nu precizie / recall)</text><text x="12" y="67">B inițial</text><text x="12" y="122">După rafinare</text><rect x="180" y="42" width="{a*4}" height="32" fill="#f3a33b"/><rect x="180" y="97" width="{b*4}" height="32" fill="#29b3cb"/><text x="{190+a*4}" y="65">{a}</text><text x="{190+b*4}" y="120">{b}</text></g></svg>'''
    (out/'summary.svg').write_text(svg,encoding='utf-8')
    simple=report['status_counts'].get('SIMPLE_ROOF_HYPOTHESIS',0)
    review=report['status_counts'].get('NEEDS_REVIEW',0)
    page=f'''<!doctype html><html lang="ro"><meta charset="utf-8"><title>StratumRO — B: etape și revizie</title>
<style>body{{max-width:1250px;margin:32px auto;padding:0 20px;font:17px/1.55 system-ui;color:#183146;background:#f6f8fa}}h1,h2{{line-height:1.2}}img{{max-width:100%;height:auto;border:1px solid #ccd7df}}table{{border-collapse:collapse;width:100%;background:white;font-size:14px}}td,th{{border:1px solid #dce3e8;padding:10px;text-align:left;vertical-align:top}}a{{color:#006a8e}}.notice{{background:#fff0d5;padding:18px;border-left:5px solid #e6991c}}.numbers{{font-size:23px;background:white;padding:20px}}details{{margin:18px 0}}</style>
<h1>StratumRO — rafinarea variantei B</h1>
<p>2026-10-18 · comparații randate în QGIS · toate rezultatele rămân ipoteze</p>
<p class="notice"><b>{simple} propuneri trec porțile automate de formă; {review} necesită revizie.</b> Aceste numere nu înseamnă clădiri corecte sau acceptate. Nu există acuratețe ori recall măsurate independent.</p>
<p class="numbers">216 intrări · {report['final_count']} propuneri păstrate · 71 respinși anterior păstrați în coada de verificare</p>
<h2>Etapele efectiv executate</h2>
<ol><li>Citire B inițial și legare la observațiile optice originale, cu proveniență.</li><li>Citire mozaic cu mască validă și evidență nDSM; NoData rămâne necunoscut.</li><li>Deduplicare prudentă și simplificare cu garduri de arie/contur; curțile sunt păstrate.</li><li>SAM2 real pe patru propuneri, după trei selecții vizuale verificate; toate încercările sunt păstrate.</li><li>Măștile nesigure sau prea complexe rămân diagnostic; rezultatul anterior nu este înlocuit automat.</li><li>QA după geometrie și comparație cu celelalte loturi, apoi încărcare în proiectul QGIS comun.</li></ol>
<img src="summary.svg" alt="Suprapuneri înainte și după"><p>Conflictele nu au fost ascunse prin decuparea sau unirea forțată a poligoanelor. Unele se reduc prin revenirea la observația optică originală. Cele rămase sunt explicit în revizie.</p>
<p>Au fost găsite {len(report['existing_lot_conflicts'])} intersecții cu alte loturi, pentru {len(set(r['candidate_id'] for r in report['existing_lot_conflicts']))} propuneri B. Pot fi observații repetate sau corpuri învecinate; nu sunt șterse automat.</p>
<h2>Comparații detaliate pe șase etape</h2><p>Cyan în planșe arată conturul etapei. În proiectul QGIS: cyan = ipoteză simplă, portocaliu = revizie. Culoarea nu înseamnă acceptare.</p>{''.join(cards)}
<h2>Toate cele {len(manifest)} obiecte</h2><p>Fiecare identificator deschide imaginea înainte/după, în aceeași fereastră geografică. Numărul de noduri este observație → propunere, nu B inițial → propunere.</p>
<table><thead><tr><th>Obiect / imagine</th><th>Stare</th><th>Noduri</th><th>Motive / limitări</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>Dovezi și cercetare</h2><p><a href="report.json">Raport numeric</a> · <a href="manifest.json">Intrări și cod</a> · <a href="retry_audit.json">Încercările SAM2</a> · <a href="refinement.gpkg">Pachetul GIS cu etape</a></p>
<p><a href="https://github.com/facebookresearch/sam2">SAM2 oficial</a> · <a href="https://mdpi-res.com/d_attachment/remotesensing/remotesensing-16-02661/article_deploy/remotesensing-16-02661.pdf">LiDAR și indicii automate SAM</a> · <a href="https://isprs-annals.copernicus.org/articles/X-2-2024/217/2024/">Orientare înainte de regularizare</a> · <a href="https://github.com/wchh-2000/SAMPolyBuild">SAMPolyBuild: alternativă de benchmark</a></p>
<p>Document local; fără componente externe, încărcări de date sau cereri automate către aceste surse.</p></html>'''
    (out/'index.html').write_text(page,encoding='utf-8')
    return {'image_count':len(manifest),'report':str(out/'index.html')}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    print(json.dumps(build(parser.parse_args().output)))
