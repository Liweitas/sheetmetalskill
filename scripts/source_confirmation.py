"""Actual source triangulation previews using the same rasterizer as new boxes."""
def write_source_previews(report,mesh,out):
 from confirmation_png import previews
 points=[p for x in mesh['parts'].values() for p in x['vertices']];extent=[max(p[k] for p in points)-min(p[k] for p in points) for k in range(3)]
 resolved={'id':'SOURCE_REVIEW','L':round(extent[0],6),'W':round(extent[1],6),'H':round(extent[2],6),'t':'see measured source audit'}
 return previews(resolved,{'parts':mesh['parts'],'source_review':True},mesh,out,'HOLD')
