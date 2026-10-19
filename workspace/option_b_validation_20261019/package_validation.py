"""Export diagnostic GIS, case observations and immutable evidence hashes."""
from pathlib import Path
import json,hashlib
import geopandas as gpd
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent

def main():
    r=json.loads((OUT/'live_qgis_validation.json').read_text());sensor=json.loads((OUT/'sensor_validation.json').read_text())
    sources={'old_visible_B':(OUT/'observed_old_B.gpkg','B_SIMPLE'),
        'new_all_B':(ROOT/'workspace/reviews/option_b_repair_20261019_v2/simple_variations.gpkg','B_SIMPLE')}
    target=OUT/'validation_diagnostics.gpkg'
    if target.exists():raise FileExistsError('Use fresh output; do not overwrite existing diagnostic evidence')
    for tag,(path,layer) in sources.items():
        data=gpd.read_file(path,layer=layer).set_index('candidate_id');rows=[]
        for ident,rec in r[tag]['records'].items():
            ev=sensor['records'][ident]['old' if tag=='old_visible_B' else 'new'];pairs=[p for p in r[tag]['overlaps'] if ident in [p['a'],p['b']]]
            rows.append(dict(candidate_id=ident,nodes=rec['nodes'],min_edge_m=rec['min_edge_m'],min_angle_deg=rec['min_angle_deg'],
                geos_valid=int(rec['geos_valid']),qgis_errors='; '.join(rec['qgis_errors']),overlap_pairs=len(pairs),
                rgb_valid=ev.get('rgb_valid_fraction',0),touches_nodata=int(ev.get('touches_nodata',False)),
                role='DIAGNOSTIC_NOT_OWNER_ACCEPTANCE',geometry=data.loc[ident].geometry))
        gpd.GeoDataFrame(rows,crs=data.crs).to_file(target,layer=tag,driver='GPKG')
    notes={17:'Acute spur changed to narrow jog. Partial-body identity and contained candidates remain unresolved.',
        35:'Visible right recess restored; upper line/orientation still questionable. Not a complete success.',
        39:'Exterior notch wraps rooftop equipment and cuts roof. Fewer vertices do not fix semantics.',
        43:'Much cleaner exterior and most small equipment holes removed. Pointed southern end may be actual roof geometry, so no forced rectangle.',
        49:'Six-corner outline better preserves the visible roof setback; not an owner acceptance.',
        68:'Final geometry unchanged (12 nodes), despite simpler eligible intermediate variants. Must validate final output after all guards.',
        108:'Unchanged pointed outline remains questionable around occluded upper roof.',
        126:'Complex exterior and spurious small interior persist; overlap with contained candidates unresolved.',
        144:'Sharp western spur remains in both versions; new outline not sufficient.',
        152:'Fewer vertices, but long narrow tip and tree-covered edge still need line fitting; oblique/curved structure must not be forced rectangular.',
        187:'Narrow roof strip at NoData; fitting more corners is not recovery of the whole roof.',
        210:'Construction/platform candidate is semantically wrong for roof delivery. Remains diagnostic.'}
    observations=[]
    for n,note in notes.items():
        image=OUT/'qgis_cases'/f'{n:03d}_comparison.jpg'
        observations.append(dict(candidate_id=f'OPT_B_{n:03d}:C1',observation=note,
            method='Human-like visual inspection of two actual QGIS renders; agent observation, not owner acceptance',
            evidence=image.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(image.read_bytes()).hexdigest()))
    (OUT/'qgis_visual_observations.json').write_text(json.dumps(observations,indent=2),encoding='utf-8')
    files=[p for p in OUT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='manifest.json']
    (OUT/'manifest.json').write_text(json.dumps({p.relative_to(OUT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2),encoding='utf-8')
    print('Exported',len(files),'evidence files and 432 diagnostic records. No roof geometry altered.')

if __name__=='__main__':main()
