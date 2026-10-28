"""Copy and close the Maa graph forms used by this repository.

This is a compiler helper, not a workflow interpreter. Unsupported reference
forms fail explicitly before posting a task; Maa still owns next and retries.
"""
from copy import deepcopy


EDGES = ('next', 'on_error')


def references(node):
    for field in EDGES:
        values = node.get(field, [])
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, list):
            raise ValueError('Referência Maa não suportada: '+field)
        for value in values:
            if not isinstance(value, str) or '[' in value or ']' in value:
                raise ValueError('NodeAttr/anchor ainda não suportado pelo compositor local.')
            yield field, value
    if node.get('anchor') or node.get('interrupt') or node.get('is_sub'):
        raise ValueError('Anchors/interrupções legadas não suportadas pelo compositor local.')


def append_fragment(graph, fragment, prefix):
    source = {k:v for k,v in fragment.items() if not k.startswith('$')}
    names = {name:prefix+name for name in source}
    if set(graph) & set(names.values()):
        raise ValueError('Colisão de identidade na composição Maa.')
    copied = {}
    for name, original in source.items():
        node = deepcopy(original)
        for field, target in references(node):
            if target not in names:
                raise ValueError('Referência fora do fragmento: '+target)
        for field in EDGES:
            if field in node:
                values = node[field]
                node[field] = names[values] if isinstance(values,str) else [names[n] for n in values]
        # These fields can refer to a previous node's geometry in Maa. Custom
        # recognition parameters are semantic game targets and stay untouched.
        for field in ('target','roi','begin','end'):
            value = node.get(field)
            if isinstance(value,str):
                if value not in names:
                    raise ValueError('Referência geométrica fora do fragmento: '+value)
                node[field] = names[value]
        copied[names[name]] = node
    graph.update(copied)
    return names


def validate_graph(graph, entry, terminals=(), *, resume=False):
    if entry not in graph or any(n not in graph for n in terminals):
        raise ValueError('Entrada/terminal ausente do grafo Maa.')
    if graph[entry].get('action','DoNothing') != 'DoNothing':
        raise ValueError('Entrada Maa precisa ser sem ação de interface.')
    for name, node in graph.items():
        for _, target in references(node):
            if target not in graph:
                raise ValueError('Aresta Maa sem destino: '+name+' → '+target)
        action = node.get('action','DoNothing')
        if node.get('timeout',6000) < 0:
            raise ValueError('Timeout Maa ilimitado: '+name)
        if action != 'DoNothing':
            if node.get('recognition','DirectHit') == 'DirectHit' or not node.get('max_hit'):
                raise ValueError('Ação Maa sem reconhecimento/limite: '+name)
        params = node.get('custom_recognition_param',{})
        if resume and (params.get('path',{}).get('consuming') or params.get('target') == 'stage_start'):
            raise ValueError('Retomada contém ação consumidora: '+name)
    return graph
