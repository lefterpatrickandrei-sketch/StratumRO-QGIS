"""Windowed automatic object proposals, with explicit roof/unknown routing.

SAM is class agnostic. These are unaccepted roof hypotheses, never a complete
building inventory or cadastral ground footprints. No reviewed anchors or GMW
reference contours enter this path. LiDAR is optional, contextual evidence.
"""
from contextlib import ExitStack
from dataclasses import dataclass, asdict
import hashlib
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import shapes, rasterize
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from scipy.ndimage import label, find_objects
from shapely.geometry import shape, box, Polygon
from shapely.strtree import STRtree


@dataclass(frozen=True)
class RegionalRoofConfig:
    resolution_m: float = .15
    core_m: float = 96.
    halo_m: float = 24.
    points_per_side: int = 16
    points_per_batch: int = 16
    min_area_m2: float = 8.
    max_area_m2: float = 12000.
    pred_iou_thresh: float = .70
    stability_score_thresh: float = .90
    max_window_pixels: int = 2048 * 2048

    def __post_init__(self):
        numeric = [self.resolution_m, self.core_m, self.halo_m, self.min_area_m2,
                   self.max_area_m2, self.pred_iou_thresh, self.stability_score_thresh]
        if not np.isfinite(numeric).all() or min(numeric[:5]) <= 0:
            raise ValueError('Finite positive physical parameters required')
        if self.min_area_m2 >= self.max_area_m2:
            raise ValueError('Ordered object area limits required')
        if any(not isinstance(x, int) or x < 1 for x in
               [self.points_per_side, self.points_per_batch, self.max_window_pixels]):
            raise ValueError('Positive integer point/memory limits required')
        if not all(0 < x <= 1 for x in numeric[-2:]):
            raise ValueError('Scores must be in (0, 1]')
        side = math.ceil((self.core_m + 2*self.halo_m) / self.resolution_m)
        if side*side > self.max_window_pixels:
            raise ValueError('Window exceeds explicit pixel budget')


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


class OrthoMosaic:
    """Bounded multi-source reads; explicit raster masks, including valid black.

    CRS must be declared. This reader never assigns a missing source CRS and
    never substitutes brightness or a fixed border exclusion for a valid mask.
    First valid source wins in overlap; source order is persisted by the runner.
    """
    def __init__(self, paths, crs='EPSG:3844', max_pixels=2048*2048):
        self.paths = [Path(p).resolve() for p in paths]
        if not self.paths or len(set(self.paths)) != len(self.paths):
            raise ValueError('Nonempty distinct raster sources required')
        self.crs = rasterio.crs.CRS.from_user_input(crs)
        if not self.crs.is_projected or self.crs.linear_units != 'metre':
            raise ValueError('Projected metric CRS required')
        self.max_pixels = max_pixels
        self.sources = []
        for path in self.paths:
            with rasterio.open(path) as src:
                if src.crs != self.crs or src.count < 3 or src.dtypes[:3] != ('uint8',)*3:
                    raise ValueError('Byte RGB sources in the declared common CRS required: '+str(path))
                if src.transform.b or src.transform.d:
                    raise ValueError('North-up sources required; reproject rotated sources first')
                self.sources.append(dict(path=str(path), bounds=list(src.bounds),
                    resolution=list(src.res), shape=list(src.shape), nodata=src.nodata,
                    mask_flags=[[f.name for f in flags] for flags in src.mask_flag_enums[:3]]))
        self.bounds = (min(s['bounds'][0] for s in self.sources), min(s['bounds'][1] for s in self.sources),
                       max(s['bounds'][2] for s in self.sources), max(s['bounds'][3] for s in self.sources))

    def read(self, bounds, resolution):
        a,b,c,d = map(float, bounds)
        if not np.isfinite([a,b,c,d,resolution]).all() or a >= c or b >= d or resolution <= 0:
            raise ValueError('Ordered finite bounds and positive resolution required')
        w,h = math.ceil((c-a)/resolution), math.ceil((d-b)/resolution)
        if w*h > self.max_pixels:
            raise ValueError('Read exceeds explicit pixel budget')
        tr = from_origin(a,d,resolution,resolution)
        rgb = np.zeros((3,h,w),dtype='uint8'); valid = np.zeros((h,w),dtype=bool)
        used = []
        for item in self.sources:
            if not box(*item['bounds']).intersects(box(a,b,c,d)):
                continue
            with rasterio.open(item['path']) as src:
                with WarpedVRT(src, crs=self.crs, transform=tr, width=w, height=h,
                               resampling=Resampling.bilinear, add_alpha=True) as vrt:
                    pixels = vrt.read([1,2,3]); mask = vrt.dataset_mask() > 0
                    take = mask & ~valid
                    if take.any():
                        rgb[:,take] = pixels[:,take]; valid |= take; used.append(item['path'])
        return np.moveaxis(rgb,0,-1), valid, tr, used


def plan_windows(bounds, config):
    a,b,c,d = bounds
    rows,cols = math.ceil((d-b)/config.core_m),math.ceil((c-a)/config.core_m)
    windows = []
    for row in range(rows):
        for col in range(cols):
            x0=a+col*config.core_m; y1=d-row*config.core_m
            core = [x0,max(b,y1-config.core_m),min(c,x0+config.core_m),y1]
            halo = config.halo_m
            windows.append(dict(window_id=f'W{row:03d}_{col:03d}',core=core,
                context=[core[0]-halo,core[1]-halo,core[2]+halo,core[3]+halo]))
    return windows


def sample_evidence(path, transform, grid_shape):
    """Nearest contextual LiDAR read with unknown values retained as NaN."""
    if path is None:
        return np.full(grid_shape,np.nan,dtype='float32')
    with rasterio.open(path) as src:
        if src.crs != rasterio.crs.CRS.from_epsg(3844):
            raise ValueError('Context raster must already declare EPSG:3844')
        with WarpedVRT(src,crs=src.crs,transform=transform,width=grid_shape[1],
                       height=grid_shape[0],resampling=Resampling.nearest,
                       dtype='float32',nodata=float('nan')) as vrt:
            values = vrt.read(1,masked=True).filled(np.nan)
    return values


def route_summary(vegetation_fraction,class6_fraction):
    """Height alone cannot distinguish trees, roofs and elevated platforms.

    Class6 is provisional positive context only. Unsupported objects stay in
    unknown, including real roofs with no Class6; they are never discarded.
    """
    if vegetation_fraction>.40:return 'LIKELY_VEGETATION_REVIEW'
    if class6_fraction>=.12:return 'ROOF_CANDIDATE_REVIEW'
    return 'OPTICAL_UNKNOWN_REVIEW'


def route_surface(rgb, component, height, counts):
    """Transparent experimental routing, not a trained building classifier.

    Zero Class6, missing LiDAR and low height are never absence proofs. Optical
    fallback survives in the unknown queue and is not vetoed by building_fraction.
    """
    colors = rgb[component].astype(float)
    r,g,b = colors.T
    high=colors.max(axis=1); sat=(high-colors.min(axis=1))/np.maximum(high,1)
    vegetation=float(((sat>.25)&(g>.85*r)&(g>1.12*b)).mean())
    known=np.isfinite(height[component]); vals=height[component][known]
    cf=counts[component]; class6=float((cf>0).mean())
    elevated=float((vals>=1.8).mean()) if vals.size else None
    red=float(((r-g>14)&(r-b>14)&(r>55)).mean())
    neutral=float(((sat<=.25)&(high>=45)).mean())
    route=route_summary(vegetation,class6)
    return dict(route=route,vegetation_fraction=vegetation,class6_fraction=class6,
                height_coverage=float(known.mean()),elevated_fraction=elevated,
                red_fraction=red,neutral_fraction=neutral,
                lidar_role='EXPERIMENTAL_CONTEXT_NOT_IDENTITY_OR_GROUND_TRUTH')


def vectorize_automatic_masks(masks, rgb, valid, transform, height, counts, config, window_id):
    """Retain all sizeable components, raw geometry and invalid-edge evidence."""
    records=[]; excluded={'below_min_area':0,'above_max_area':0}
    area=abs(transform.determinant); h,w=valid.shape
    frame=box(*rasterio.transform.array_bounds(h,w,transform))
    for number,item in enumerate(masks):
        observed=np.asarray(item['segmentation'],dtype=bool)
        labs,n=label(observed&valid)
        for part,sl in enumerate(find_objects(labs),1):
            if sl is None:continue
            local=labs[sl]==part
            size=float(local.sum()*area)
            if size<config.min_area_m2:
                excluded['below_min_area']+=1;continue
            if size>config.max_area_m2:
                excluded['above_max_area']+=1;continue
            comp=np.zeros(valid.shape,dtype=bool);comp[sl]=local
            geometries=[shape(g) for g,v in shapes(comp.astype('uint8'),mask=comp,transform=transform) if v]
            for geometry in geometries:
                if geometry.geom_type!='Polygon' or not geometry.is_valid:continue
                info=route_surface(rgb,comp,height,counts)
                # Invalid clipping can give a plausible straight artificial edge.
                # Check adjacency to invalid pixels, not just a retained-area ratio.
                from scipy.ndimage import binary_dilation
                missing=bool((binary_dilation(comp)&~valid).any())
                edge=geometry.distance(frame.boundary)<config.resolution_m*1.5
                ident=f'{window_id}_M{number:04d}_P{part:03d}_{len(records):04d}'
                records.append(dict(candidate_id=ident,window_id=window_id,
                    sam_score=float(item['predicted_iou']),stability=float(item['stability_score']),
                    touches_window=edge,touches_nodata=missing,geometry=geometry,
                    raw_area_m2=geometry.area,**info))
    return records,excluded


def deduplicate_candidates(records, iou_threshold=.60, containment=.92):
    """Suppress repeated observations, never union adjacent buildings.

    Nested masks are not suppressed by containment alone: they may be another
    roof body. Similar area is required, and lineage of suppressed views remains.
    """
    if not records:return [],[]
    rank=sorted(range(len(records)),key=lambda i:(records[i]['touches_window'] or records[i]['touches_nodata'],
        records[i]['route']!='ROOF_CANDIDATE_REVIEW',-records[i]['sam_score'],-records[i]['geometry'].area,
        records[i]['candidate_id']))
    tree=STRtree([r['geometry'] for r in records]);kept=set();links=[]
    for idx in rank:
        current=records[idx]; geom=current['geometry']; duplicate=None
        for other in sorted(int(j) for j in tree.query(geom,predicate='intersects') if int(j) in kept):
            target=records[other]['geometry']; overlap=geom.intersection(target).area
            ratio=min(geom.area,target.area)/max(geom.area,target.area)
            if overlap/geom.union(target).area>=iou_threshold or (ratio>=.75 and overlap/min(geom.area,target.area)>=containment):
                duplicate=other;break
        if duplicate is None:kept.add(idx)
        else:links.append(dict(suppressed=current['candidate_id'],retained=records[duplicate]['candidate_id']))
    return [records[i] for i in rank if i in kept],links


def simplify_regional_roof(raw, *, boundary_tolerance_m=.6, max_vertices=16):
    """Simple geometry only if no significant wing/hole is removed or invented.

    Shape agreement is with SAM, not reality. Save the raw observation and route
    complex masks to review instead of calling a many-corner mask a finished roof.
    """
    from .roof_simple_geometry import simple_roof_geometry
    anchor=raw.representative_point()
    if not raw.interiors:
        candidate,info=simple_roof_geometry(raw,min_support=.95,min_coverage=.95,max_vertices=max_vertices)
        if info['method']!='NEEDS_REVIEW' and candidate.boundary.hausdorff_distance(raw.boundary)<=boundary_tolerance_m:
            removed=raw.difference(candidate);added=candidate.difference(raw)
            pieces=lambda g:list(g.geoms) if hasattr(g,'geoms') else [g]
            # No globally small area loss may hide a real narrow but long wing.
            changes=[g for diff in [removed,added] for g in pieces(diff) if not g.is_empty and g.area>0]
            if all(g.area<=2. and min(g.minimum_rotated_rectangle.bounds[2]-g.minimum_rotated_rectangle.bounds[0],
                   g.minimum_rotated_rectangle.bounds[3]-g.minimum_rotated_rectangle.bounds[1])<=1.2 for g in changes):
                return candidate,dict(method=info['method'],status='SIMPLE_HYPOTHESIS_REVIEW',**{
                    k:info[k] for k in ['support','coverage']})
    candidate=raw.simplify(.25,preserve_topology=True)
    n=len(candidate.exterior.coords)-1+sum(len(r.coords)-1 for r in candidate.interiors)
    status='GEOMETRY_NEEDS_REVIEW' if n>max_vertices else 'OPTICAL_HYPOTHESIS_REVIEW'
    return candidate,dict(method='RAW_OPTICAL_SIMPLIFIED_NOT_FORCED',status=status)


def expand_edge_candidate(record, mosaic, predictor, config, height_path=None, counts_path=None):
    """One automatic context retry; no seed-box clipping or fabricated review.

    The original view remains in window records. A retry must retain the same
    observed component, cover its automatic anchor and preserve >=80% of that
    view; added area is still a hypothesis, not proof of object identity.
    """
    import torch
    raw=record['geometry'];anchor=raw.representative_point()
    bounds=box(*raw.bounds).buffer(config.halo_m*2).bounds
    try:rgb,valid,tr,used=mosaic.read(bounds,config.resolution_m)
    except ValueError as exc:
        return record,dict(status='EXPANSION_NOT_READ',reason=str(exc),bounds=bounds)
    predictor.set_image(rgb)
    px=(~tr)*(anchor.x,anchor.y)
    with torch.inference_mode():
        masks,scores,_=predictor.predict(point_coords=np.array([px],dtype='float32'),
            point_labels=np.array([1],dtype='int32'),multimask_output=True)
    height=sample_evidence(height_path,tr,valid.shape);counts=sample_evidence(counts_path,tr,valid.shape)
    options,exclusions=vectorize_automatic_masks([dict(segmentation=m,predicted_iou=s,stability_score=0.)
        for m,s in zip(masks,scores) if float(s)>=config.pred_iou_thresh],
        rgb,valid,tr,height,counts,config,record['window_id']+'_EXPANDED')
    consistent=[r for r in options if r['geometry'].covers(anchor) and
                r['geometry'].intersection(raw).area/raw.area>=.80]
    audit=dict(bounds=bounds,used_sources=used,anchor=[anchor.x,anchor.y],
               option_count=len(options),consistent_options=len(consistent),excluded=exclusions)
    if not consistent:
        return record,dict(**audit,status='NO_CONSISTENT_EXPANDED_MASK')
    best=max(consistent,key=lambda r:(not r['touches_window'],-abs(r['geometry'].area-raw.area)/raw.area,r['sam_score']))
    best.update(candidate_id=record['candidate_id'],window_id=record['window_id'],
        stability=record['stability'],expanded_context=True)
    return best,dict(**audit,status='EXPANDED_HYPOTHESIS_REVIEW')


def ground_footprint_scenarios(roof, offsets_m):
    """Illustrative eave assumptions only; no fixed default or measured footprint."""
    if roof.geom_type!='Polygon' or not roof.is_valid:
        raise ValueError('Valid roof polygon required')
    results=[]
    for offset in offsets_m:
        if not np.isfinite(offset) or offset<=0:raise ValueError('Explicit positive assumed eave offsets required')
        ground=roof.buffer(-float(offset),join_style=2)
        if ground.is_empty or ground.geom_type!='Polygon' or not ground.is_valid:
            raise ValueError('Assumed offset collapses or splits the roof; wall observations required')
        results.append(dict(offset_m=float(offset),geometry=ground,
            status='ILLUSTRATIVE_ASSUMPTION_NOT_MEASURED_GROUND_FOOTPRINT',
            roof_area_m2=roof.area,scenario_area_m2=ground.area))
    return results
