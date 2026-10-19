"""Run shared simpler shape proposals and render every case and alternative.

CPU only, existing observations; no new detection or model inference. Results
are versioned with their assets under the owner policy of 2026-10-19.
"""
import sys,json,html,hashlib,textwrap
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import geopandas as gpd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rasterio.transform import array_bounds
from stratum_ro.api.service import PlatformService
from stratum_ro.regional_refinement import vertices,overlap_pairs
from tools.refine_regional_roofs import save_json,save_layer,sha


def render_case(engine,out,ident,g,chosen,options):
    # Same geographic frame for every alternative; explicit validity mask.
    scene=engine.observe(g.buffer(2))
    panels=[('B anterior',g,'#ffad32'),('Propunere simpla',chosen['geometry'],'#00e2ff')]
    for n,option in enumerate(options,1):
        panels.append((f'V{n}: {option["family"]}, {option["vertices"]} colturi\n'+
            ('eligibila' if option['eligible'] else 'RESPINSA: '+', '.join(option['reasons'])),
            option['geometry'],'#3bea4d' if option['eligible'] else '#fa54be'))
    fig,axes=plt.subplots(2,4,figsize=(18,9),layout='constrained')
    rgb=np.dstack([scene['rgb'],scene['valid'].astype('uint8')*255])
    west,south,east,north=array_bounds(*scene['valid'].shape,scene['transform'])
    for ax in axes.flat:ax.axis('off')
    for ax,(title,geom,color) in zip(axes.flat,panels):
        ax.imshow(rgb,extent=(west,east,south,north),interpolation='nearest')
        for ring in [geom.exterior]+list(geom.interiors):
            xy=np.asarray(ring.coords);ax.plot(xy[:,0],xy[:,1],color=color,lw=1.7)
        ax.set_xlim(west,east);ax.set_ylim(south,north);ax.set_title('\n'.join(textwrap.fill(line,48) for line in title.splitlines()),fontsize=8)
    fig.suptitle(f'{ident}: {vertices(g)} -> {vertices(chosen["geometry"])} colturi | ipoteze, fara acceptare automata')
    fig.savefig(out/'images'/(ident.replace(':','_')+'.jpg'),dpi=95);plt.close(fig)


def run(output, review_actions=None):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);(out/'images').mkdir()
    selection=json.loads((ROOT/'workspace/building_workflow/CURRENT.json').read_text(encoding='utf-8'))
    source=ROOT/selection['simplification_input']['path']
    cfg=json.loads((ROOT/selection['reader_config']).read_text(encoding='utf-8'))
    engine=PlatformService(ROOT).create_regional_roof_refiner([ROOT/p for p in cfg['orthophotos']],
        height_path=ROOT/cfg['height'] if cfg.get('height') else None)
    data=gpd.read_file(source,layer=selection['simplification_input']['layer'])
    baseline=gpd.read_file(source,layer=selection['simplification_input']['baseline_layer']).set_index('candidate_id')
    assert data.crs.to_epsg()==3844
    records=[]
    for _,row in data.iterrows():
        g=row.geometry;old=baseline.loc[row.candidate_id].geometry
        if g.geom_type=='MultiPolygon' and len(g.geoms)==1:g=g.geoms[0]
        if old.geom_type=='MultiPolygon' and len(old.geoms)==1:old=old.geoms[0]
        records.append(dict(candidate_id=row.candidate_id,geometry=g,baseline_geometry=old,qa_status=str(row.qa_status)))
    annotations={}
    if review_actions:
        package=json.loads(Path(review_actions).read_text(encoding='utf-8'))
        for ident,annotation in package['annotations'].items():
            evidence=ROOT/annotation['evidence_path']
            if sha(evidence)!=annotation['evidence_sha256']:raise ValueError('Review evidence hash mismatch: '+ident)
            annotations[ident]=annotation
    result=engine.simplify_shapes(records,review_annotations=annotations)
    previous=result['previous'];final=result['final'];variants=result['variants'];decisions=result['decisions']
    compare=previous
    comparison_source=None
    if review_actions:
        active=selection.get('comparison_review',selection['active_review'])
        comparison_source=ROOT/active['directory']/active['gpkg']
        prior=gpd.read_file(comparison_source,layer=active.get('all_cases_layer',active['layer'])).set_index('candidate_id')
        compare=[dict(candidate_id=r['candidate_id'],geometry=prior.loc[r['candidate_id']].geometry) for r in previous]
        for old,new,decision in zip(compare,final,decisions):
            decision['changed_vs_active']=not old['geometry'].equals(new['geometry'])
    for index,(old,selected) in enumerate(zip(compare,final)):
        ident=selected['candidate_id']
        options=[v for v in variants if v['candidate_id']==ident]
        render_case(engine,out,ident,old['geometry'],selected,options)
        if index%20==0:print(f'{index+1}/{len(data)}',flush=True)
    gpkg=out/'simple_variations.gpkg'
    save_layer(gpkg,'B_PREVIOUS',previous);save_layer(gpkg,'B_SIMPLE',final);save_layer(gpkg,'B_VARIATIONS',variants)
    save_layer(gpkg,'B_BEFORE_REPAIR',compare)
    proposals=[r for r in final if r['display_role']=='ROOF_PROPOSAL']
    diagnostic=[r for r in final if r['display_role']=='DIAGNOSTIC_ONLY']
    if proposals:save_layer(gpkg,'B_ROOF_PROPOSALS',proposals)
    if diagnostic:save_layer(gpkg,'B_DIAGNOSTIC_ONLY',diagnostic)
    report=dict(input_count=len(data),output_count=len(final),variant_count=len(variants),
        total_nodes_before=sum(vertices(r['geometry']) for r in previous),
        total_nodes_after=sum(vertices(r['geometry']) for r in final),
        simplified_cases=sum(vertices(a['geometry'])>vertices(b['geometry']) for a,b in zip(previous,final)),
        conflicts_before=overlap_pairs(previous),conflicts_after=overlap_pairs(final),
        invalid_count=sum(not r['geometry'].is_valid for r in final),decisions=decisions,
        measured_accuracy=None,measured_recall=None,new_detection=False,new_sam2_inference=False,
        scope='EXISTING_B_PROPOSALS_SIMPLE_SHAPE_ALTERNATIVES',owner_acceptance_changed=False,
        roof_proposal_count=len(proposals),diagnostic_only_count=len(diagnostic),
        changed_vs_active=sum(d.get('changed_vs_active',False) for d in decisions),
        comparison_source=str(comparison_source) if comparison_source else None,
        review_actions_sha256=sha(Path(review_actions)) if review_actions else None,
        parameters=dict(min_support=.92,min_coverage=.92,max_area_change=.08,max_boundary_distance_m=1.5,min_edge_m=1.,local_change_tolerance_m=.35,max_local_change_area_m2=.75,significant_recess_min_area_m2=1.,significant_recess_depth_m=.8,max_recess_fill_fraction=.30))
    save_json(out/'report.json',report)
    entries=[]
    for d in decisions:
        ident=d['candidate_id'];path='images/'+ident.replace(':','_')+'.jpg'
        entries.append(dict(candidate_id=ident,path=path,sha256=sha(out/path)))
    save_json(out/'visual_manifest.json',entries)
    save_json(out/'manifest.json',dict(source=str(source),source_sha256=sha(source),
        code={p:sha(ROOT/p) for p in ['stratum_ro/roof_simple_geometry.py','stratum_ro/regional_refinement.py','tools/review_simple_roof_variations.py']},
        gpkg_sha256=sha(gpkg),config=cfg))
    rows=[]
    for d,e in zip(decisions,entries):
        note=d.get('review_annotation',{})
        rows.append(f'<details><summary>{html.escape(d["candidate_id"])}  |  {d["nodes_before"]} -> {d["nodes_after"]} colturi  |  {d["selected"]["family"]}  |  {d.get("display_role", "REVIEW")}</summary><p>Observatie din auditul initial, nu verdict dupa corectie: {html.escape(note.get("observation", ""))}</p><p>Actiune: {note.get("action", "REVIEW")}; diagnostic pastrat separat pentru NON_ROOF/INCOMPLETE. Ipoteze, fara acceptare automata.</p><a href="{e["path"]}"><img loading="lazy" src="{e["path"]}"></a></details>')
    page=f'''<!doctype html><html lang="ro"><meta charset="utf-8"><title>B - forme simple si variatii</title>
<style>body{{font:17px/1.5 system-ui;max-width:1550px;margin:30px auto;padding:20px;background:#f4f7f8;color:#183146}}img{{width:100%}}summary{{padding:14px;background:white;cursor:pointer;border-bottom:1px solid #ccd}}.note{{padding:20px;background:#fff0d5}}</style>
<h1>Varianta B - forme mai simple si alternative</h1><p class="note">{report['simplified_cases']} din 216 contururi simplificate. {report['total_nodes_before']} -> {report['total_nodes_after']} colturi in total. {len(variants)} alternative pastrate. Toate necesita verificare; simplu nu inseamna automat corect.</p>
<p>Deschide fiecare caz pentru comparatia pe aceeasi imagine. Cyan = propunere selectata; verde = alternativa eligibila geometric; mov = alternativa respinsa. Niciuna dintre culori nu inseamna acceptare.</p>
<p>Dreptunghi, L, U, T sau decalaj, forme articulate, curte interioara si directii oblice sunt tratate ca familii posibile. Nu inventam toate aceste forme pentru fiecare cladire. T si Z nu sunt deosebite sigur doar din opt colturi. Corpurile diferite raman separate.</p>
<p>Limite de dezvoltare: sprijin/acoperire minimum 92%, schimbare de arie maximum 8%, abatere de contur maximum 1,5 m; nu sunt tolerante cadastrale. Retragerile semnificative sunt protejate. Golurile mici pot fi eliminate numai cu sprijin de inaltime valid; celelalte raman neverificate. NoData si degradarea muchiilor blocheaza schimbarea. Suprapunerile existente raman in revizie. Nu exista o noua detectie pe zona si nu sunt recuperate cladiri lipsa prin simplificare.</p>
<p><a href="report.json">Raport complet</a>  |  <a href="simple_variations.gpkg">Straturi GIS</a>  |  <a href="../option_b_refinement_20261018_final/index.html">Etapa anterioara</a></p>
{''.join(rows)}<p>Cercetare: <a href="https://www.informatik.uni-wuerzburg.de/en/algo/research/geographic-information-systems/simplification-of-building-footprints/">Haunert si Wolff: reducerea muchiilor cu pastrarea topologiei</a>; <a href="https://www.mdpi.com/2220-9964/12/12/469">regularizarea contururilor ortogonale</a>. Implementare proprie limitata, folosind fitterul existent; nu reproducere integrala a algoritmilor publicati.</p></html>'''
    (out/'index.html').write_text(page,encoding='utf-8')
    if review_actions:
        page=page.replace('<h1>',f'<p>{len(proposals)} propuneri in revizie; {len(diagnostic)} cazuri izolate in diagnostic, fara stergere. {report["changed_vs_active"]} geometrii schimbate fata de B activ anterior. Aceste numere nu inseamna cladiri corectate sau acceptate.</p><h1>',1)
        (out/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['decisions','conflicts_before','conflicts_after']},indent=2))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output');parser.add_argument('--review-actions')
    args=parser.parse_args();run(args.output,args.review_actions)
