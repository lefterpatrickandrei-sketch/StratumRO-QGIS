import sqlite3

conn = sqlite3.connect('workspace/output/cladiri_stereo70.gpkg')
c = conn.cursor()
for t in ['CLADIRI_SOL_ANCPI', 'CORONAMENT_ARBORI', 'ARBORI', 'MARGINE_SIGURANTA_ORTOFOTO']:
    try:
        cnt = c.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
        gtype = c.execute(f'SELECT geometry_type_name FROM gpkg_geometry_columns WHERE table_name="{t}"').fetchone()[0]
        print(f'{t:30s}: {cnt:5d} entities, geometry: {gtype}')
    except Exception as e:
        print(f'{t:30s}: error {e}')
conn.close()
