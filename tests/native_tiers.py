"""Audit transitive fixture/helper calls; fast never means `not fixtures`."""
import ast
import inspect
from pathlib import Path
import textwrap


NATIVE_CONSTRUCTORS={'Resource','Tasker','Win32Controller','CustomController','DbgController','ReplayController'}
NATIVE_METHODS={'post_bundle','post_recognition','run_recognition','run_recognition_direct',
                'post_task','post_action','framework','post_connection'}


def native_reasons(function,seen=None):
    seen=seen if seen is not None else set()
    function=inspect.unwrap(function)
    if function in seen:return []
    seen.add(function)
    try:tree=ast.parse(textwrap.dedent(inspect.getsource(function)))
    except (TypeError,OSError,IndentationError,SyntaxError):return []
    reasons=[]
    for call in (n for n in ast.walk(tree) if isinstance(n,ast.Call)):
        if isinstance(call.func,ast.Name):
            name=call.func.id
            if name in NATIVE_CONSTRUCTORS:reasons.append(name)
            helper=getattr(function,'__globals__',{}).get(name)
            if inspect.isfunction(helper) and Path(inspect.getsourcefile(helper) or '').parent.name=='tests':
                reasons.extend(native_reasons(helper,seen))
        elif isinstance(call.func,ast.Attribute) and call.func.attr in NATIVE_METHODS:
            reasons.append(call.func.attr)
    return sorted(set(reasons))


def classify(item):
    reasons=['test:'+r for r in native_reasons(item.obj)]
    info=getattr(item,'_fixtureinfo',None)
    for name,definitions in (info.name2fixturedefs if info else {}).items():
        for definition in definitions:
            reasons.extend('fixture:'+name+':'+r for r in native_reasons(definition.func))
    if item.get_closest_marker('native'):reasons.append('explicit_native_marker')
    return sorted(set(reasons))
