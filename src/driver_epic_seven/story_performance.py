"""Reject impossible candidates; a positive still needs the complete UI tree."""


def candidate_matcher(vision, frame, matcher, params):
    """Return a frame-local matcher, or None when necessary anchors are absent.

    This negative filter never supplies an observation or input proof. Unknown
    anchors remain possible. No result survives this callback; native calls on
    its one image are reused only within it.
    """
    recognized = {}
    def recognize(name):
        if name not in recognized:
            recognized[name] = matcher(name)
        return recognized[name]
    if params.get('observe') or params.get('session') or params.get('quest'):
        return recognize
    path = params.get('path', {})
    kind = path.get('kind')
    state = params.get('state') if not path else {
        'story_skip': 'story', 'story_hold': 'story',
        'prequel_story_skip': 'story', 'prequel_story_hold': 'story',
        'prequel_clear': 'stage_clear', 'prequel_defeat': 'battle_failed',
        'prequel_supporter': 'supporter_selection',
    }.get(kind)
    states = (('episode_map','prequel_ready_map','prequel_story_map')
              if kind in ('prequel_map_return','prequel_story_done') else (state,))
    specs = [vision.spec['states'].get(name) for name in states]
    if any(spec is None for spec in specs):
        return recognize
    matches = {}
    def hit(name, source=None):
        # Missing/uninterpreted anchors cannot prove a negative.
        if name not in vision.spec['templates'] and name not in vision.spec.get('ocr', {}):
            return True
        if name not in matches:
            reader = vision.match_ocr if name in vision.spec.get('ocr', {}) else vision.match_template
            matches[name] = reader(name, frame, recognize)
        match = matches[name]
        if source is not None:
            return (match['source_matches'][source]['hit'] if source in match.get('source_matches', {})
                    else match.get('source_node') == source and match['hit'])
        return match['hit']
    def possible(variant):
        sources = variant.get('source_nodes', {})
        return (all(hit(name, sources.get(name)) for name in variant.get('all', []))
                and (not variant.get('any') or any(hit(name, sources.get(name)) for name in variant['any'])))
    # Exclusions and superseding panels remain in the complete classifier.
    if not any(possible(variant) for spec in specs for variant in spec.get('variants', [spec])):
        return None
    if params.get('auto_state') is False and state == 'battle_running':
        off_anchors = ('auto_hud_off','auto_manual_skills','auto_unlocked_off')
        if all(name in vision.spec['templates'] for name in off_anchors):
            # The canonical Auto reader requires one of these positive off
            # proofs. Absence cannot authorize toggling, nor require full OCR.
            off = hit('auto_hud_off') or (hit('auto_manual_skills') and hit('auto_unlocked_off'))
            if not off:
                return None
    if kind in ('story_hold', 'prequel_story_hold', 'story_skip', 'prequel_story_skip'):
        gray = ('path_story_skip_gray', 'path_story_history_gray')
        if all(name in vision.spec['templates'] for name in gray):
            hold = all(hit(name) for name in gray)
            if hold != (kind in ('story_hold', 'prequel_story_hold')):
                return None
    return recognize


def needs_story_text(params, state):
    """Return false solely for a candidate whose existing state guard fails.

    The positive path retains the complete OCR, overlay checks, tree and native
    target validation. This function never supplies a target or approves input.
    """
    kind = params.get('path', {}).get('kind')
    if kind in ('story_skip', 'story_hold', 'prequel_story_skip', 'prequel_story_hold'):
        return state == 'story'
    if params.get('state') == 'story_confirmation' and params.get('target') == 'story_confirm_button':
        return state == 'story_confirmation'
    return True
