"""Finite navigation proofs over the canonical tree and its captured pixels.

No capture, OCR, state retention, input or retries. Mapped navigation is the
only operation eligible for ignoring differences in an animated background.
"""
import numpy as np

from .observed_ui import field_value as value, validate_tree, operation_view, quest_view


def _panels(tree):
    return [n for n in tree['nodes'].values() if n['kind']=='panel'
            and value(n,'visible') is True and (value(n,'adapter')=='operations'
                or (value(n,'semantic_id')=='orbis_guide' and any(
                    tree['nodes'][i]['kind']=='group' for i in n['children'])))]


def _view(panel):
    return value(panel,'view') or value(panel,'semantic_id')


def _controls(tree, panel):
    return [tree['nodes'][identity] for identity in panel['children']
            if tree['nodes'][identity]['kind']=='control']


def _contains(node, point):
    box=value(node,'box')
    return bool(box and point and box[0]<=point[0]<box[0]+box[2]
                and box[1]<=point[1]<box[1]+box[3])


def _eligible(control):
    return (value(control,'visible') is True and value(control,'enabled') is not False
            and value(control,'consuming') is False and value(control,'navigation_destinations'))


def _ocr_nodes(tree):
    return [n for n in tree['nodes'].values() if value(n,'adapter')=='ocr'
            and value(n,'box') and value(n,'text')]


def _anchor_nodes(tree, panel):
    pointers={s.get('pointer') for s in panel['fields']['visible']['sources'] if s.get('kind')=='ocr'}
    return [n for n in _ocr_nodes(tree) if any(s.get('pointer') in pointers
            for s in n['fields']['box']['sources'])]


def _same_box(a,b):
    return max(abs(x-y) for x,y in zip(a,b))<=6


def _glyph_error(previous,current,box):
    x,y,w,h=map(int,box)
    old=previous[y:y+h,x:x+w,:3]
    new=current[y:y+h,x:x+w,:3]
    if old.shape!=new.shape or not old.size:
        return None,0
    # Only the bright neutral lettering, not its translucent animated backing.
    mask=(old.min(axis=2)>=210)&(old.max(axis=2)-old.min(axis=2)<=35)
    pixels=int(mask.sum())
    return (float(np.abs(old.astype(float)-new.astype(float))[mask].mean()) if pixels>=12 else None),pixels


def navigation_proof(saved_tree,current_tree,previous,current,*,action,point=None,key=None):
    """Return accepted/rejected/not_applicable; never an executable handle."""
    report={'status':'not_applicable','input_sent':False,'anchors':[]}
    if action not in ('click','key'):
        return report
    validate_tree(saved_tree);validate_tree(current_tree)
    saved_panels=_panels(saved_tree)
    if len(saved_panels)!=1:
        return report
    panel=saved_panels[0]
    controls=_controls(saved_tree,panel)
    back=action=='key' and key=='escape' and value(panel,'back_destinations')
    if back:
        candidates=[]
        destinations=back
        control=None
    else:
        candidates=[n for n in controls if _eligible(n) and (
            _contains(n,point) if action=='click' else value(n,'navigation_shortcut')==key)]
        if not candidates:
            return report
        if len(candidates)!=1:
            return {**report,'status':'rejected','reason':'ambiguous_navigation_control'}
        control=candidates[0]
        destinations=value(control,'navigation_destinations')
    report.update(status='rejected',view=_view(panel),
                  control=value(control,'semantic_id') if control else 'back',
                  destinations=destinations)
    def reject(reason):
        return {**report,'reason':reason}
    if (not isinstance(destinations,list) or not destinations or
            any(not isinstance(d,dict) or not isinstance(d.get('view'),str) for d in destinations)):
        return reject('invalid_navigation_role')
    if saved_tree['context']['window']!=current_tree['context']['window']:
        # Foreground/minimized are incidental here; Runtime checks window
        # identity and minimization separately immediately before input.
        fields=('hwnd','pid','process_name','window_title','window_class','client_size')
        if any(saved_tree['context']['window'].get(k)!=current_tree['context']['window'].get(k) for k in fields):
            return reject('window_identity_changed')
    if previous.shape!=current.shape or list(current.shape[:2][::-1])!=current_tree['context']['client_size']:
        return reject('frame_size_changed')
    panels=_panels(current_tree)
    if (len(panels)!=1 or _view(panel)!=_view(panels[0])
            or value(panel,'mode')!=value(panels[0],'mode')):
        return reject('navigation_panel_changed')
    now=panels[0]
    if back:
        if value(now,'back_destinations')!=destinations:
            return reject('navigation_role_changed')
    else:
        matches=[n for n in _controls(current_tree,now) if value(n,'semantic_id')==value(control,'semantic_id')]
        if len(matches)!=1 or not _eligible(matches[0]):
            return reject('navigation_control_missing')
        target=matches[0]
        if (value(target,'navigation_destinations')!=destinations
                or value(target,'text')!=value(control,'text')
                or not _same_box(value(target,'box'),value(control,'box'))
                or (action=='click' and not _contains(target,point))
                or (action=='key' and value(target,'navigation_shortcut')!=key)):
            return reject('navigation_control_changed')
    # Preserve an identified subject; a current unreadable/different name is
    # not permission to act on the subject from the earlier observation.
    def subject(tree,p):
        items=[tree['nodes'][i] for i in p['children'] if value(tree['nodes'][i],'semantic_id')=='context']
        return value(items[0],'hero_name') if len(items)==1 else None
    if subject(saved_tree,panel) is not None and subject(saved_tree,panel)!=subject(current_tree,now):
        return reject('navigation_subject_changed')
    anchors=_anchor_nodes(saved_tree,panel)
    if control:
        anchors.append(control)
    unique={tuple(value(n,'box')):n for n in anchors if value(n,'box')}
    if len(unique)<2:
        return reject('insufficient_context_anchors')
    centers=[(b[0]+b[2]/2,b[1]+b[3]/2) for b in unique]
    if max(max(x for x,y in centers)-min(x for x,y in centers),
           max(y for x,y in centers)-min(y for x,y in centers))<120:
        return reject('context_anchors_not_separated')
    current_text=_ocr_nodes(current_tree)
    proven=[]
    for box,anchor in unique.items():
        if control and anchor['id']==control['id']:
            matches=[target]  # Its current native region/role were checked above.
        else:
            matches=[n for n in current_text if value(n,'text')==value(anchor,'text')
                     and _same_box(value(n,'box'),box)]
        if len(matches)!=1:
            return reject('context_anchor_missing_or_ambiguous')
        error,pixels=_glyph_error(previous,current,box)
        report['anchors'].append({'node_id':anchor['id'],'box':list(box),
                                  'glyph_pixels':pixels,'pixel_mae':round(error,3) if error is not None else None})
        if error is None:
            if control and box==tuple(value(control,'box')):
                return reject('navigation_target_has_no_glyph_proof')
            continue
        if error>18:
            return reject('context_anchor_pixels_changed')
        proven.append(box)
    if len(proven)<2 or max(max(b[0] for b in proven)-min(b[0] for b in proven),
                            max(b[1] for b in proven)-min(b[1] for b in proven))<120:
        return reject('insufficient_separated_pixel_anchors')
    report.update(status='accepted',reason='current_non_consuming_navigation_and_stable_glyphs')
    return report


def navigation_arrived(observation,proof):
    """An accepted dispatch is not proof that the destination actually opened."""
    current=operation_view(observation)
    if not current and quest_view(observation).get('group_id'):
        current={'view':'orbis_guide','mode':quest_view(observation).get('path')}
    return any(current.get('view')==d.get('view') and
               ('mode' not in d or current.get('mode')==d['mode'])
               for d in proof.get('destinations',[]))
