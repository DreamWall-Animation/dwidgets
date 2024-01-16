

def sort_elements(schema, elements):
    result = [str(e) for e in schema if e in elements]
    result += sorted([str(e) for e in elements if e not in schema])
    return result


def sort_nodes(_, context, nodes):
    if not nodes:
        return nodes
    schema = context.sorting_settings['value', list(nodes)[0].key]
    nodes = list(nodes)
    result = []
    keys = sort_elements(schema, [n.value for n in nodes])
    for key in keys:
        for node in nodes[:]:
            if node.value == key:
                result.append(node)
                nodes.remove(node)
    result.extend(nodes)
    return result


def get_total(model, _, nodes):
    result = []
    for node in nodes:
        output = node.outputs()[0]
        entries = [
            model.entries[i]
            for indexes in output.content.values()
            for i in indexes]
        result.append((sum(e.weight for e in entries), node))
    return [r[1] for r in sorted(result, reverse=True, key=lambda r: r[0])]


def alphabetical(_, __, nodes):
    return sorted(nodes, key=lambda x: x.value)


TREE_SORTERS = {
    'Alphabetical': alphabetical,
    'Defined sorter': sort_nodes,
    'By total': get_total}
