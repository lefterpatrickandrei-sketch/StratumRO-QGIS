"""Package this review checkpoint; no geometry generation or owner acceptance."""
from pathlib import Path
import json, hashlib, subprocess

ROOT = Path(__file__).resolve().parents[2]
TASK = Path(__file__).resolve().parent
OUT = ROOT / 'workspace/reviews/option_b_repair_20261019_v2'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(p, data):
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')

def main():
    report = json.loads((OUT/'report.json').read_text())
    changed = json.loads((TASK/'changed_ids.json').read_text())
    notes = {
        3:'Bevels restored; boundaries need review against roof rather than rectangular prior.',
        10:'Small boundary adjustment; no visually major change at sheet scale.',
        11:'Small exterior jog remains; no owner acceptance.',
        13:'More exterior bevels than previous rectangle; still requires review.',
        14:'Oblique shoulder restored; needs corner review.',
        15:'Exterior corners changed; alignment review remains.',
        16:'Chamfered corners replace rectangle; occlusion/identity still uncertain.',
        17:'Acute triangular spur rejected; narrow original notch remains and body may be partial.',
        20:'Local steps restored; completeness still unproven.',
        27:'Step restored on lower edge; same partial body identity needs review.',
        35:'L recess restored instead of filled upper-right corner.',
        36:'Roof shoulder restored; minor bevels remain.',
        37:'Chamfered corners retained; review at valid-data boundary.',
        39:'Tiny interior removed with height support; exterior equipment-like notch remains wrong/suspect.',
        43:'Five tiny mask holes removed with height support, 89 to 11 total vertices vs active prior; pointed end still needs review.',
        47:'Local setbacks restored; shadowed boundary not accepted.',
        49:'Six-corner L preserves visible right-side recess; checked also in live QGIS.',
        55:'Six-corner L restores lower-edge recess.',
        60:'Bays restored but extra bevels require review.',
        65:'Simple rectangle retained with boundary shift; cemetery context needs semantic review.',
        66:'Tree false positive remains diagnostic; changed shape is not a repaired building.',
        70:'Setback restored; wing identity still requires review.',
        75:'Lower local recess restored; occluded edge remains uncertain.',
        79:'Corner/step follows observed roof more closely; not accepted.',
        81:'End bevel restored; valid-data context remains limited.',
        185:'Only roof fragment represented; new L is not completeness recovery.',
        46:'Opposite local setbacks preserved; corner/identity review remains.',
        89:'Hole cleanup and local outline changes; possible duplication/whole-body identity unresolved.',
        96:'Visible shoulder preserved rather than swallowed by rectangle.',
        99:'Small rectangle shift; existing partial-body identity unresolved.',
        100:'Main L retained; local steps added, requires comparison with accepted T05.',
        109:'Roof shoulder restored; rounded/bevelled edge still needs refinement.',
        110:'Tiny interior removed with height support; rectangle remains proposal.',
        114:'Minor corner changes only; no completeness claim.',
        115:'Local lower recess restored; identity of partial roof remains uncertain.',
        116:'NoData and jagged lower edge remain diagnostic.',
        126:'Some tiny holes removed; exterior still complex, not solved.',
        129:'Six-corner L restores lower-right recess.',
        200:'Tiny interior cleaned; seed cuts larger roof, still diagnostic.',
        202:'Interior cleanup partial; missing whole roof and noisy exterior remain diagnostic.',
        137:'Courtyard/vegetation false candidate retained only in diagnostic.',
        144:'Local notch retained but pointed spur still present; not solved.',
        145:'L retained with small boundary shift; no whole-building identity established.',
        147:'Local step restored; triangular end still suspect.',
        152:'Exterior simpler but elongated tip remains; not accepted.',
        153:'Interior cleaned; long partial roof and exterior spur remain diagnostic.',
        163:'Local shoulder restored; boundaries near NoData still review.',
        164:'Small interior cleaned and exterior shoulder restored; same roof identity review.',
        210:'Construction/platform candidate still diagnostic, not a roof recovery.',
        167:'L setback retained, minor outline change.',
        171:'Notch restored; still fragment of a larger roof.',
        172:'Shoulder and bevels retained; no independent precision measurement.',
        187:'Roof strip at NoData boundary remains incomplete diagnostic.',
        157:'Tiny interior cleaned but long cut and NoData remain diagnostic.'
    }
    assert len(notes)==len(changed)==54
    observations=[]
    for ident in changed:
        n=int(ident.split('_')[-1].split(':')[0]);image=OUT/'images'/(ident.replace(':','_')+'.jpg')
        observations.append(dict(candidate_id=ident, reviewer='Codex visual post-check',
            method='before/after panels in 9 contact sheets; 13 target cases also full alternatives',
            observation=notes[n], evidence_path=image.relative_to(ROOT).as_posix(),evidence_sha256=sha(image),
            owner_verdict='PENDING_OWNER_REVIEW'))
    post_review=dict(changed_cases=observations,
        full_sheet_target_ids=[17,35,39,43,49,55,68,96,108,109,115,129,144],
        unchanged_cases='162 geometries equal to prior active result; prior 216-case audit remains relevant, not re-certified',
        unresolved_priority=[39,108,126,144,147,152],automatic_delivery_ready=False)
    save(TASK/'post_repair_visual_review.json',post_review)
    save(OUT/'post_repair_visual_review.json',post_review)
    selector=ROOT/'workspace/building_workflow/CURRENT.json'
    selection=json.loads(selector.read_text())
    selection['active_review']=dict(directory=OUT.relative_to(ROOT).as_posix(),gpkg='simple_variations.gpkg',
        layer='B_ROOF_PROPOSALS',diagnostic_layer='B_DIAGNOSTIC_ONLY',all_cases_layer='B_SIMPLE',website='index.html')
    selection['review_actions']='workspace/option_b_repair_20261019/review_actions.json'
    selection['comparison_review']=dict(directory='workspace/reviews/option_b_simple_variations_20261018_v2',gpkg='simple_variations.gpkg',layer='B_SIMPLE')
    selection['report_command']='venv/Scripts/python.exe tools/review_simple_roof_variations.py <fresh-output-directory> --review-actions workspace/option_b_repair_20261019/review_actions.json'
    save(selector,selection)
    # Bind snapshots and presentation corrections separately from original generation hashes.
    paths=[p for p in OUT.rglob('*') if p.is_file() and p.name!='checkpoint_manifest.json']
    save(OUT/'checkpoint_manifest.json',dict(role='post-render edits and QGIS snapshots; original manifest remains generation evidence',
        files={p.relative_to(OUT).as_posix():sha(p) for p in paths},
        code_current={p:sha(ROOT/p) for p in ['stratum_ro/roof_simple_geometry.py','stratum_ro/regional_refinement.py','tools/review_simple_roof_variations.py','tools/show_simple_roof_variations_qgis.py']},
        code_git_index_sha256={p:hashlib.sha256(subprocess.check_output(['git','show',':'+p],cwd=ROOT)).hexdigest() for p in ['stratum_ro/roof_simple_geometry.py','stratum_ro/regional_refinement.py','tools/review_simple_roof_variations.py','tools/show_simple_roof_variations_qgis.py']},
        code_hash_note='code_current hashes working files; code_git_index_sha256 hashes staged source with Git line-ending normalization'))
    print('Packaged',len(paths),'review assets;',report['changed_vs_active'],'changed geometries')

if __name__=='__main__':main()
