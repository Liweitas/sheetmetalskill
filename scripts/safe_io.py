"""Refuse report/generated-output aliases of protected inputs, including existing hardlinks."""
import os
from pathlib import Path
def same_file(a,b):
 x=Path(a);y=Path(b)
 return x.resolve()==y.resolve() or x.exists() and y.exists() and os.path.samefile(x,y)
def guard_outputs(inputs,outputs):
 actual=[x for x in outputs if x]
 for out in actual:
  if any(same_file(out,src) for src in inputs if src):raise ValueError('output must not overwrite an input/source file')
 for i,out in enumerate(actual):
  if any(same_file(out,other) for other in actual[:i]):raise ValueError('different output artifacts must use different paths')
