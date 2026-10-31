"""Numerical CAD Boolean volume provenance; no physical tolerance or fit-threshold change."""
import math
DISPLAY_DECIMALS=6
AUTHORITY='Actual exported/read-back BODY STEP compound common with formed LID STEP'
def finite_volume(v):
 if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:raise ValueError('INTERFERENCE_MEASUREMENT: finite nonnegative volume required')
 return v
def display_volume(v):return format(finite_volume(v),'.6f')
def comparison_tolerance(a,b):return max(1e-6,1e-8*max(finite_volume(a),finite_volume(b)))
def require_same_measurement(authority,fresh):
 if abs(finite_volume(authority)-finite_volume(fresh))>comparison_tolerance(authority,fresh):raise ValueError('INTERFERENCE_AUTHORITY: repeated actual BODY/LID common differs from authoritative recorded value')
 return True
def measurement(authority,pair_sum=None):
 finite_volume(authority)
 if pair_sum is not None:finite_volume(pair_sum)
 return {'authoritative_source':AUTHORITY,'authoritative_volume_mm3':authority,'display_decimal_places':DISPLAY_DECIMALS,'display_volume_mm3':display_volume(authority),'pairwise_sum_mm3':pair_sum,'pair_sum_minus_authority_mm3':pair_sum-authority if pair_sum is not None else None,'numerical_comparison_absolute_mm3':1e-6,'numerical_comparison_relative':1e-8,'meaning':'CAD Boolean arithmetic only; raw digits are trace data, not physical accuracy. Pairwise sum is a separate diagnostic operation.','fit_intersection_threshold_unchanged_mm3':1e-7}
