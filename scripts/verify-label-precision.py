"""Float32 glyph-spacing reproducer for a small scene at1e14m; no OpenGL oracle."""
from pathlib import Path
import json,numpy as np
ROOT=Path(__file__).resolve().parents[1]
origin=np.array([1e14,0,0]);camera=origin+np.array([0,-1e8,6e7]);point=origin+np.array([1e7,0,0]);offsets=np.array([[x,0,z] for x in range(0,1000000,50000) for z in [0,150000]])
exact=point+offsets-camera
old=(point+offsets).astype(np.float32).astype(float)-camera
new=((point-camera)+offsets).astype(np.float32).astype(float)
report={'sample_glyph_vertices':len(offsets),'origin_m':origin.tolist(),'old_max_world_subtraction_component_error_m':float(np.max(abs(old-exact))),'camera_relative_max_component_error_m':float(np.max(abs(new-exact))),'old_unique_horizontal_coordinates':len(set(old[:,0])),'camera_relative_unique_horizontal_coordinates':len(set(new[:,0])),'expected_horizontal_coordinates':20,'scope':'Independent float32 precision reproducer of glyph spacing at1e14m; separate native images establish visual behavior.'}
assert report['old_unique_horizontal_coordinates']<20 and report['camera_relative_unique_horizontal_coordinates']==20
(ROOT/'evidence/label-precision-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
