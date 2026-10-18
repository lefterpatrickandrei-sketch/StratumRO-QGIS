"""Fit two observed roof edges across an optical gap, without polygon clipping."""
import numpy as np
from scipy.ndimage import map_coordinates,gaussian_filter1d
from shapely.geometry import Polygon


def replace_observed_edge(polygon,index,coordinates,*,max_corner_shift_m=3.5,max_area_change=.15):
    """Intersect the observed straight edge with its two original neighbors.

    No subtraction against a neighboring hypothesis; other vertices are retained.
    """
    points=np.array(polygon.exterior.coords[:-1],dtype=float);n=len(points)
    a,b=np.asarray(coordinates,dtype=float)
    def intersection(p,q,r,s):
        matrix=np.column_stack([q-p,-(s-r)])
        if abs(np.linalg.det(matrix))<1e-8:raise ValueError('Parallel neighboring edge')
        t=np.linalg.solve(matrix,r-p)[0]
        return p+t*(q-p)
    first=intersection(points[(index-1)%n],points[index],a,b)
    last=intersection(points[(index+1)%n],points[(index+2)%n],a,b)
    if max(np.linalg.norm(first-points[index]),np.linalg.norm(last-points[(index+1)%n]))>max_corner_shift_m:
        raise ValueError('Observed edge requires excessive corner displacement')
    points[index]=first;points[(index+1)%n]=last
    result=Polygon(points,[r.coords for r in polygon.interiors])
    if not result.is_valid or abs(result.area-polygon.area)/polygon.area>max_area_change:
        raise ValueError('Invalid or excessive geometry change')
    return result


def fit_roof_gap(rgb,transform,valid,start,end,*,search_m=3.,step_m=.03,profiles=41):
    """Return independent edge lines only when a stable dark gap is observed.

    start/end indicate the approximate overlapping edge, not a desired answer.
    Returned line coordinates are observations, never cadastral acceptance.
    """
    p=np.asarray(start,dtype=float);q=np.asarray(end,dtype=float)
    vec=q-p;length=np.linalg.norm(vec)
    if length<3 or rgb.shape[:2]!=valid.shape:raise ValueError('Aligned RGB/mask and edge length >=3m required')
    direction=vec/length;normal=np.array([direction[1],-direction[0]])
    distances=np.arange(-search_m,search_m+step_m/2,step_m)
    samples=[]
    inv=~transform
    for t in np.linspace(.15,.85,profiles):
        center=p+t*vec;xy=center[None,:]+distances[:,None]*normal
        col,row=inv*(xy[:,0],xy[:,1]);coords=[row-.5,col-.5]
        ok=map_coordinates(valid.astype(float),coords,order=0,mode='constant',cval=0)>.5
        if not ok.all():continue
        brightness=np.mean([map_coordinates(rgb[:,:,k].astype(float),coords,order=1,mode='nearest') for k in range(3)],axis=0)
        smooth=gaussian_filter1d(brightness,max(1,.08/step_m))
        # Both adjacent roof interiors must be brighter than the valley.
        left=np.median(smooth[:max(3,len(smooth)//6)]);right=np.median(smooth[-max(3,len(smooth)//6):])
        lo=int(np.argmin(smooth));floor=smooth[lo]
        if min(left,right)-floor<15:continue
        threshold=floor+.45*(min(left,right)-floor)
        a=lo;b=lo
        while a>0 and smooth[a-1]<threshold:a-=1
        while b<len(smooth)-1 and smooth[b+1]<threshold:b+=1
        width=distances[b]-distances[a]
        if a==0 or b==len(smooth)-1 or not .12<=width<=2.5:continue
        samples.append([t*length,distances[a],distances[b],float(min(left,right)-floor)])
    if len(samples)<max(8,.6*profiles):
        return {'status':'UNRESOLVED_NO_STABLE_OPTICAL_GAP','profiles_used':len(samples),'profiles_requested':profiles}
    arr=np.array(samples);lines=[]
    for i in [1,2]:
        keep=np.ones(len(arr),dtype=bool)
        for _ in range(3):
            slope,intercept=np.polyfit(arr[keep,0],arr[keep,i],1)
            residual=np.abs(arr[:,i]-(slope*arr[:,0]+intercept))
            keep=residual<=max(.15,3*np.median(residual))
        if keep.sum()<.6*profiles or abs(slope)>np.tan(np.deg2rad(10)):
            return {'status':'UNRESOLVED_UNSTABLE_EDGE','profiles_used':int(keep.sum())}
        coords=[(p+direction*s+normal*(slope*s+intercept)).tolist() for s in [0,length]]
        lines.append({'coordinates':coords,'median_residual_m':float(np.median(residual[keep])),
                      'profiles_used':int(keep.sum())})
    return {'status':'OBSERVED_OPTICAL_GAP_REQUIRES_REVIEW','edges':lines,
            'median_gap_width_m':float(np.median(arr[:,2]-arr[:,1])),
            'samples':arr.tolist(),'normal':normal.tolist(),'automatic_acceptance':False}


def fit_red_roof_edge(rgb,transform,valid,start,end,inside_point,*,search_m=3.,profiles=51,
                      signal_kind='RED_CHROMATIC'):
    """Fit a red-roof transition along its full side, independently of its neighbor."""
    p=np.asarray(start,dtype=float);q=np.asarray(end,dtype=float);v=q-p
    length=np.linalg.norm(v);direction=v/length;normal=np.array([direction[1],-direction[0]])
    if np.dot(np.asarray(inside_point)-(p+q)/2,normal)<0:normal=-normal
    dist=np.arange(-search_m,search_m+.025,.05);inv=~transform
    colors=rgb.astype(float)
    if signal_kind=='BRIGHTNESS':signal=colors.mean(axis=2)/255.
    elif signal_kind=='RED_CHROMATIC':signal=(colors[:,:,0]-colors[:,:,1])/np.maximum(colors.sum(axis=2),1)
    else:raise ValueError('Unknown edge signal')
    points=[]
    for t in np.linspace(.08,.92,profiles):
        center=p+t*v;xy=center+dist[:,None]*normal
        c,r=inv*(xy[:,0],xy[:,1]);where=[r-.5,c-.5]
        if not (map_coordinates(valid.astype(float),where,order=0,mode='constant',cval=0)>.5).all():continue
        values=gaussian_filter1d(map_coordinates(signal,where,order=1,mode='nearest'),2)
        gradient=np.gradient(values,.05)
        indices=np.arange(5,len(dist)-5)
        idx=indices[np.argmax(gradient[indices])]
        contrast=values[idx+4]-values[idx-4]
        if contrast<.035:continue
        points.append([t*length,dist[idx],contrast])
    if len(points)<.6*profiles:return {'status':'UNRESOLVED_NO_STABLE_COLOR_EDGE','profiles_used':len(points)}
    arr=np.array(points);keep=np.ones(len(arr),dtype=bool)
    for _ in range(4):
        slope,intercept=np.polyfit(arr[keep,0],arr[keep,1],1)
        residual=np.abs(arr[:,1]-(slope*arr[:,0]+intercept))
        keep=residual<=max(.18,3*np.median(residual))
    if keep.sum()<.6*profiles or abs(slope)>np.tan(np.deg2rad(10)):
        return {'status':'UNRESOLVED_UNSTABLE_COLOR_EDGE','profiles_used':int(keep.sum())}
    return {'status':'OBSERVED_RED_ROOF_EDGE_REQUIRES_REVIEW',
        'coordinates':[(p+direction*s+normal*(slope*s+intercept)).tolist() for s in [0,length]],
        'profiles_used':int(keep.sum()),'profiles_requested':profiles,
        'median_residual_m':float(np.median(residual[keep])),'samples':arr.tolist(),
        'automatic_acceptance':False}
