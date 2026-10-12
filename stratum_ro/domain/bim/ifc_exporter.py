# -*- coding: utf-8 -*-
"""
StratumRO IFC4 Georeferenced BIM Exporter
=========================================
Exports 3D regularized cadastral buildings into ISO 16739-1 IFC4 format with
official buildingSMART georeferencing (IfcProjectedCRS & IfcMapConversion).

Solves the Revit 16 km limitation:
- Shifts coordinates to a local project origin near (0, 0, 0) to avoid floating-point jitter.
- Embeds EPSG:3844 (Stereo 70) geodetic CRS and translation offsets via IfcMapConversion.
- Enables native 'Link IFC' in Autodesk Revit 2027 and Nemetschek Allplan 2026.
"""

import os
import uuid
import datetime
from typing import List, Dict, Any, Optional, Tuple
from shapely.geometry import Polygon, MultiPolygon


def _create_guid() -> str:
    """Generates a compressed 22-character IFC GUID from a UUID4."""
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$"
    u = uuid.uuid4().int
    guid = ""
    for _ in range(22):
        guid = chars[u % 64] + guid
        u //= 64
    return guid


class IfcCadastralExporter:
    """
    Serializes 2.5D/3D regularized cadastral buildings to buildingSMART IFC4.
    """

    def __init__(self, crs_name: str = "EPSG:3844", crs_description: str = "Stereo 70 / Dealul Piscului 1970"):
        self.crs_name = crs_name
        self.crs_description = crs_description

    def export_buildings_to_ifc4(
        self,
        buildings: List[Dict[str, Any]],
        output_ifc_path: str,
        project_name: str = "StratumRO_Cadastre_BIM",
        default_height_m: float = 6.0,
        default_ground_z: float = 0.0
    ) -> str:
        """
        Exports a list of building dictionaries to a georeferenced IFC4 file.

        Each building dict should contain:
        - 'geometry': shapely.geometry.Polygon (in Stereo 70 coordinates)
        - 'height_m' or 'height': float (optional, defaults to default_height_m)
        - 'ground_z': float (optional, defaults to default_ground_z)
        - 'id' or 'cad_id': str/int (optional)
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_ifc_path)), exist_ok=True)

        # 1. Compute anchor centroid for local engineering CRS shift
        valid_buildings = []
        all_xs = []
        all_ys = []

        for b in buildings:
            geom = b.get("geometry")
            if geom is None:
                continue
            if isinstance(geom, Polygon) and not geom.is_empty and geom.area > 2.0:
                valid_buildings.append(b)
                all_xs.extend([pt[0] for pt in geom.exterior.coords])
                all_ys.extend([pt[1] for pt in geom.exterior.coords])
            elif isinstance(geom, MultiPolygon):
                for p in geom.geoms:
                    if not p.is_empty and p.area > 2.0:
                        valid_buildings.append({**b, "geometry": p})
                        all_xs.extend([pt[0] for pt in p.exterior.coords])
                        all_ys.extend([pt[1] for pt in p.exterior.coords])

        if not valid_buildings or not all_xs:
            raise ValueError("No valid building polygons found to export.")

        # Geodetic project base point (Map Conversion Anchor)
        east_anchor = round(sum(all_xs) / len(all_xs), 3)
        north_anchor = round(sum(all_ys) / len(all_ys), 3)
        height_anchor = round(float(valid_buildings[0].get("ground_z", default_ground_z)), 3)

        lines: List[str] = []
        step_id = 1

        def next_id() -> int:
            nonlocal step_id
            curr = step_id
            step_id += 1
            return curr

        # STEP Header
        now_iso = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        header = f"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [DesignTransferView]'),'2;1');
FILE_NAME('{os.path.basename(output_ifc_path)}','{now_iso}',('StratumRO'),('StratumRO Industrial Geomatics'),'StratumRO IFC4 Engine','Autodesk Revit 2027 / Allplan 2026 Compatible','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;"""
        lines.append(header)

        # Core project setup
        id_owner_history = next_id()
        id_person = next_id()
        id_org = next_id()
        id_person_org = next_id()
        id_app = next_id()

        lines.append(f"#{id_person} = IFCPERSON($,'Surveyor','Authorized',$,$,$,$,$);")
        lines.append(f"#{id_org} = IFCORGANIZATION($,'StratumRO Geomatics',$,$,$);")
        lines.append(f"#{id_person_org} = IFCPERSONANDORGANIZATION(#{id_person},#{id_org},$);")
        lines.append(f"#{id_app} = IFCAPPLICATION(#{id_org},'1.0','StratumRO','StratumRO');")
        lines.append(f"#{id_owner_history} = IFCOWNERHISTORY(#{id_person_org},#{id_app},.READWRITE.,.NOTDEFINED.,$,$,$,0);")

        # Dimensional units (Meters)
        id_si_meter = next_id()
        id_unit_assign = next_id()
        lines.append(f"#{id_si_meter} = IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);")
        lines.append(f"#{id_unit_assign} = IFCUNITASSIGNMENT((#{id_si_meter}));")

        # 3D Geometric Representation Context
        id_pt_zero = next_id()
        id_axis_z = next_id()
        id_axis_x = next_id()
        id_placement_world = next_id()
        lines.append(f"#{id_pt_zero} = IFCCARTESIANPOINT((0.,0.,0.));")
        lines.append(f"#{id_axis_z} = IFCDIRECTION((0.,0.,1.));")
        lines.append(f"#{id_axis_x} = IFCDIRECTION((1.,0.,0.));")
        lines.append(f"#{id_placement_world} = IFCAXIS2PLACEMENT3D(#{id_pt_zero},#{id_axis_z},#{id_axis_x});")

        id_context_model = next_id()
        lines.append(f"#{id_context_model} = IFCGEOMETRICREPRESENTATIONCONTEXT('Model','Model',3,1.E-05,#{id_placement_world},#3D_DIR_W_NORTH);")
        # Fix placeholder
        lines[-1] = lines[-1].replace("#3D_DIR_W_NORTH", "$")

        # --- BUILDINGSMART GEOREFERENCING ENTITIES (IFC4) ---
        id_projected_crs = next_id()
        id_map_conversion = next_id()
        lines.append(f"#{id_projected_crs} = IFCPROJECTEDCRS('{self.crs_name}','{self.crs_description}','Dealul Piscului 1970',$,'Oblique Stereographic','Stereo 70',#{id_si_meter});")
        lines.append(f"#{id_map_conversion} = IFCMAPCONVERSION(#{id_context_model},#{id_projected_crs},{east_anchor:.3f},{north_anchor:.3f},{height_anchor:.3f},1.,0.,1.);")

        # Spatial Hierarchy: Project -> Site -> Building
        id_project = next_id()
        id_site = next_id()
        id_building = next_id()
        id_rel_agg_project = next_id()
        id_rel_agg_site = next_id()

        lines.append(f"#{id_project} = IFCPROJECT('{_create_guid()}',#{id_owner_history},'{project_name}',$,$,$,$,(#{id_context_model}),#{id_unit_assign});")
        lines.append(f"#{id_site} = IFCSITE('{_create_guid()}',#{id_owner_history},'CadastralSite',$,$,#{id_placement_world},$,$,.ELEMENT.,(44,20,0),(25,50,0),{height_anchor:.3f},$,$);")
        lines.append(f"#{id_building} = IFCBUILDING('{_create_guid()}',#{id_owner_history},'SiteContextMasses',$,$,#{id_placement_world},$,$,.ELEMENT.,$,$,$);")

        lines.append(f"#{id_rel_agg_project} = IFCRELAGGREGATES('{_create_guid()}',#{id_owner_history},$,$,#{id_project},(#{id_site}));")
        lines.append(f"#{id_rel_agg_site} = IFCRELAGGREGATES('{_create_guid()}',#{id_owner_history},$,$,#{id_site},(#{id_building}));")

        building_element_ids: List[int] = []

        # 2. Iterate each building and generate extruded solids
        for idx, b in enumerate(valid_buildings, start=1):
            poly: Polygon = b["geometry"]
            b_height = float(b.get("height_m") or b.get("height") or default_height_m)
            b_height = max(b_height, 2.0)
            b_ground_z = float(b.get("ground_z", default_ground_z))
            b_id_label = str(b.get("id") or b.get("cad_id") or f"C{idx}")

            # Local coordinates relative to map anchor
            rel_coords = [(round(p[0] - east_anchor, 3), round(p[1] - north_anchor, 3)) for p in poly.exterior.coords][:-1]
            if len(rel_coords) < 3:
                continue

            # Points for polygon profile
            pt_ids = []
            for rx, ry in rel_coords:
                pid = next_id()
                lines.append(f"#{pid} = IFCCARTESIANPOINT(({rx:.3f},{ry:.3f}));")
                pt_ids.append(f"#{pid}")
            # Close loop
            pt_ids.append(pt_ids[0])

            id_poly = next_id()
            lines.append(f"#{id_poly} = IFCPOLYLINE(({','.join(pt_ids)}));")

            id_profile = next_id()
            lines.append(f"#{id_profile} = IFCARBITRARYCLOSEDPROFILEDEF(.AREA.,'Footprint_{b_id_label}',#{id_poly});")

            # Solid extrusion
            rel_z = round(b_ground_z - height_anchor, 3)
            id_pt_base = next_id()
            id_place_extrude = next_id()
            lines.append(f"#{id_pt_base} = IFCCARTESIANPOINT((0.,0.,{rel_z:.3f}));")
            lines.append(f"#{id_place_extrude} = IFCAXIS2PLACEMENT3D(#{id_pt_base},#{id_axis_z},#{id_axis_x});")

            id_solid = next_id()
            lines.append(f"#{id_solid} = IFCEXTRUDEDAREASOLID(#{id_profile},#{id_place_extrude},#{id_axis_z},{b_height:.3f});")

            # Shape representation
            id_shape_rep = next_id()
            id_prod_def = next_id()
            lines.append(f"#{id_shape_rep} = IFCSHAPEREPRESENTATION(#{id_context_model},'Body','SweptSolid',(#{id_solid}));")
            lines.append(f"#{id_prod_def} = IFCPRODUCTDEFINITIONSHAPE($,$,(#{id_shape_rep}));")

            # Building element proxy
            id_element = next_id()
            guid_elem = _create_guid()
            lines.append(f"#{id_element} = IFCBUILDINGELEMENTPROXY('{guid_elem}',#{id_owner_history},'{b_id_label}','Cadastral LoD1 Mass',$,#{id_placement_world},#{id_prod_def},$,.NOTDEFINED.);")
            building_element_ids.append(id_element)

        # Containment relationship
        if building_element_ids:
            id_rel_contain = next_id()
            elements_tuple = "(" + ",".join(f"#{eid}" for eid in building_element_ids) + ")"
            lines.append(f"#{id_rel_contain} = IFCRELCONTAINEDINSPATIALSTRUCTURE('{_create_guid()}',#{id_owner_history},'BuildingContainment',$,{elements_tuple},#{id_building});")

        lines.append("ENDSEC;")
        lines.append("END-ISO-10303-21;")

        # Write output file
        with open(output_ifc_path, "w", encoding="utf-8") as f_out:
            f_out.write("\n".join(lines) + "\n")

        return output_ifc_path
