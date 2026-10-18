"""Run shared simpler shape proposals and render every case and alternative.

CPU only, existing observations; no new detection or model inference. GIS/images
stay local; hashes and numeric decisions can be copied into the task checkpoint.
"""
import sys,json,html,hashlib
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


def run(output):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);(out/'images').mkdir()
    source=ROOT/'workspace/reviews/option_b_refinement_20261018_final/refinement.gpkg'
    cfg=json.loads((ROOT/'workspace/option_b_refinement_20261018/config_replay.json').read_text())
    engine=PlatformService(ROOT).create_regional_roof_refiner([ROOT/p for p in cfg['orthophotos']])
    data=gpd.read_file(source,layer='B4_FINAL_REVIEW')
    baseline=gpd.read_file(source,layer='B0_BASELINE').set_index('candidate_id')
    assert data.crs.to_epsg()==3844
    previous=[];final=[];variants=[];decisions=[]
    for index,row in data.iterrows():
        ident=row.candidate_id;g=row.geometry
        if g.geom_type=='MultiPolygon' and len(g.geoms)==1:g=g.geoms[0]
        old=baseline.loc[ident].geometry
        if old.geom_type=='MultiPolygon' and len(old.geoms)==1:old=old.geoms[0]
        chosen,options=engine.shape_variations(g,old)
        # No new overlap with another proposal is silently introduced. Preserve
        # this object's former shape when the independently simpler fit worsens
        # pairwise intersection by more than 0.05 m² (development QA threshold).
        others=data.iloc[data.sindex.query(g.buffer(2),predicate='intersects')]
        for _,neighbor in others.iterrows():
            if neighbor.candidate_id==ident:continue
            if chosen['geometry'].intersection(neighbor.geometry).area>g.intersection(neighbor.geometry).area+.05:
                chosen=dict(geometry=g,vertices=vertices(g),family='UNRESOLVED',method='PREVIOUS_CONFLICT_GUARD',
                    eligible=False,reasons=['INCREASES_NEIGHBOR_OVERLAP'])
                break
        previous.append(dict(candidate_id=ident,geometry=g))
        record=dict(candidate_id=ident,geometry=chosen['geometry'],family=chosen['family'],
            vertices=chosen['vertices'],method=chosen['method'],owner_verdict='PENDING_OWNER_REVIEW',
            qa_status='SHAPE_PROPOSAL_REVIEW_REQUIRED',previous_qa_status=str(row.qa_status),
            reasons=chosen['reasons'])
        final.append(record)
        details=[]
        for number,option in enumerate(options,1):
            variants.append(dict(candidate_id=ident,variant_id=f'{ident}:V{number}',**option))
            details.append({k:v for k,v in option.items() if k!='geometry'})
        decisions.append(dict(candidate_id=ident,nodes_before=vertices(g),nodes_after=vertices(chosen['geometry']),
            selected={k:v for k,v in chosen.items() if k!='geometry'},alternatives=details))
        # Same geographic frame for every alternative; explicit validity mask.
        scene=engine.observe(g.buffer(2))
        panels=[('B anterior',g,'#ffad32'),('Propunere simpla',chosen['geometry'],'#00e2ff')]
        for n,option in enumerate(options,1):
            panels.append((f'V{n}: {option["family"]}, {option["vertices"]} colturi\n'+
                ('eligibila' if option['eligible'] else 'RESPINSA: '+', '.join(option['reasons'])),
                option['geometry'],'#3bea4d' if option['eligible'] else '#fa54be'))
        fig,axes=plt.subplots(2,4,figsize=(18,9),layout='constrained')
        rgb=np.dstack([scene['rgb'],scene['valid'].astype('uint8')*255])
        bottom,left,top,right=0,0,0,0
        west,south,east,north=array_bounds(*scene['valid'].shape,scene['transform'])
        for ax in axes.flat:ax.axis('off')
        for ax,(title,geom,color) in zip(axes.flat,panels):
            ax.imshow(rgb,extent=(west,east,south,north),interpolation='nearest')
            for ring in [geom.exterior]+list(geom.interiors):
                xy=np.asarray(ring.coords);ax.plot(xy[:,0],xy[:,1],color=color,lw=1.7)
            ax.set_xlim(west,east);ax.set_ylim(south,north);ax.set_title(title,fontsize=9)
        fig.suptitle(f'{ident}: {vertices(g)} → {vertices(chosen["geometry"])} colturi · ipoteze, fara acceptare automata')
        fig.savefig(out/'images'/(ident.replace(':','_')+'.jpg'),dpi=95);plt.close(fig)
        if index%20==0:print(f'{index+1}/{len(data)}',flush=True)
    # Joint update can introduce conflict even if each passes against old shapes.
    # Monotonically revert changed proposals until no pairwise area increases.
    by_old={r['candidate_id']:r['geometry'] for r in previous}
    reverted=[]
    while True:
        bad=[]
        for pair in overlap_pairs(final):
            a,b=pair['a'],pair['b']
            if pair['area_m2']>by_old[a].intersection(by_old[b]).area+.05:bad.extend([a,b])
        changed=False
        for r in final:
            if r['candidate_id'] in bad and not r['geometry'].equals(by_old[r['candidate_id']]):
                r.update(geometry=by_old[r['candidate_id']],method='JOINT_CONFLICT_GUARD',family='UNRESOLVED',
                    vertices=vertices(by_old[r['candidate_id']]),reasons=['JOINT_OVERLAP_INCREASE'])
                reverted.append(r['candidate_id']);changed=True
        if not changed:break
    # Do not silently mismatch rendered selections: stop for regeneration if any.
    if reverted:raise RuntimeError('Joint conflict revisions require rerender: '+str(reverted))
    gpkg=out/'simple_variations.gpkg'
    save_layer(gpkg,'B_PREVIOUS',previous);save_layer(gpkg,'B_SIMPLE',final);save_layer(gpkg,'B_VARIATIONS',variants)
    report=dict(input_count=len(data),output_count=len(final),variant_count=len(variants),
        total_nodes_before=sum(vertices(r['geometry']) for r in previous),
        total_nodes_after=sum(vertices(r['geometry']) for r in final),
        simplified_cases=sum(vertices(a['geometry'])>vertices(b['geometry']) for a,b in zip(previous,final)),
        conflicts_before=overlap_pairs(previous),conflicts_after=overlap_pairs(final),
        invalid_count=sum(not r['geometry'].is_valid for r in final),decisions=decisions,
        measured_accuracy=None,measured_recall=None,new_detection=False,new_sam2_inference=False,
        scope='EXISTING_B_PROPOSALS_SIMPLE_SHAPE_ALTERNATIVES',owner_acceptance_changed=False,
        parameters=dict(min_support=.92,min_coverage=.92,max_area_change=.08,max_boundary_distance_m=1.5,min_edge_m=1.))
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
        rows.append(f'<details><summary>{html.escape(d["candidate_id"])} · {d["nodes_before"]} → {d["nodes_after"]} colturi · {d["selected"]["family"]}</summary><a href="{e["path"]}"><img loading="lazy" src="{e["path"]}"></a></details>')
    page=f'''<!doctype html><html lang="ro"><meta charset="utf-8"><title>B — forme simple si variatii</title>
<style>body{{font:17px/1.5 system-ui;max-width:1550px;margin:30px auto;padding:20px;background:#f4f7f8;color:#183146}}img{{width:100%}}summary{{padding:14px;background:white;cursor:pointer;border-bottom:1px solid #ccd}}.note{{padding:20px;background:#fff0d5}}</style>
<h1>Varianta B — forme mai simple si alternative</h1><p class="note">{report['simplified_cases']} din 216 contururi simplificate. {report['total_nodes_before']} → {report['total_nodes_after']} colturi in total. {len(variants)} alternative pastrate. Toate necesita verificare; simplu nu inseamna automat corect.</p>
<p>Deschide fiecare caz pentru comparatia pe aceeasi imagine. Cyan = propunere selectata; verde = alternativa eligibila geometric; mov = alternativa respinsa. Niciuna dintre culori nu inseamna acceptare.</p>
<p>Dreptunghi, L, U, T sau decalaj, forme articulate, curte interioara si directii oblice sunt tratate ca familii posibile. Nu inventam toate aceste forme pentru fiecare cladire. T si Z nu sunt deosebite sigur doar din opt colturi. Corpurile diferite raman separate.</p>
<p>Limite de dezvoltare: sprijin/acoperire minimum 92%, schimbare de arie maximum 8%, abatere de contur maximum 1,5 m; nu sunt tolerante cadastrale. Curti pastrate, NoData si degradarea muchiilor blocheaza schimbarea. Suprapunerile existente raman in revizie. Nu exista o noua detectie pe zona si nu sunt recuperate cladiri lipsa prin simplificare.</p>
<p><a href="report.json">Raport complet</a> · <a href="simple_variations.gpkg">Straturi GIS</a> · <a href="http://127.0.0.1:8767/index.html">Etapa anterioara</a></p>
{''.join(rows)}<p>Cercetare: <a href="https://www.informatik.uni-wuerzburg.de/en/algo/research/geographic-information-systems/simplification-of-building-footprints/">Haunert si Wolff: reducerea muchiilor cu pastrarea topologiei</a>; <a href="https://www.mdpi.com/2220-9964/12/12/469">regularizarea contururilor ortogonale</a>. Implementare proprie limitata, folosind fitterul existent; nu reproducere integrala a algoritmilor publicati.</p></html>'''
    (out/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['decisions','conflicts_before','conflicts_after']},indent=2))

if __name__=='__main__':run(sys.argv[1])
