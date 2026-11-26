#!/usr/bin/env python3
"""Candidate side-screw layout. Actual formed/unfolded interference checks remain required."""
import math

def plan_side_fixings(length,width,*,overhang,edge_inset=12.0,max_pitch=150.0):
    vals=[length,width,overhang,edge_inset,max_pitch]
    if any(isinstance(x,bool) or not isinstance(x,(float,int)) or not math.isfinite(x) for x in vals):raise ValueError('finite dimensions required')
    if min(length,width,edge_inset,max_pitch)<=0 or overhang<0:raise ValueError('positive size/inset/pitch and nonnegative overhang required')
    if min(length,width)<=2*(edge_inset-overhang):raise ValueError('body is too small for the selected end inset')
    def row(size):
        a=edge_inset-overhang;b=size+overhang-edge_inset
        if not 0<a<b<size:raise ValueError('inset cannot produce two distinct hole centers within body face')
        # At least three evenly spaced points on any selected wall row; long rows
        # add further points so the 150 mm maximum pitch is never exceeded.
        intervals=max(2,math.ceil((b-a)/max_pitch))
        return [a+(b-a)*i/intervals for i in range(intervals+1)]
    # Always fasten the two longer walls. Add the shorter walls when their entire cap span exceeds the limit.
    xs=row(length) if length>=width or length+2*overhang>max_pitch else []
    ys=row(width) if width>length or width+2*overhang>max_pitch else []
    return {'long_x':xs,'short_y':ys,'connection_count':2*(len(xs)+len(ys)),'edge_inset_on_lid_mm':edge_inset,'max_pitch_rule_mm':max_pitch,'long_row_max_pitch_mm':max((b-a for a,b in zip(xs,xs[1:])),default=0),'short_row_max_pitch_mm':max((b-a for a,b in zip(ys,ys[1:])),default=0),'rule_source':'shop candidate default selected for user request; not a load certification','actual_geometry_clearance_check_required':True}
