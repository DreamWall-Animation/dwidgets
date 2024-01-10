
import uuid
from collections import defaultdict


class ChartEntry:
    def __init__(self, data, weight):
        self.data = data
        self.weight = weight


class ChartModel:
    """
    This is the chart view data model, this is managing the tree generation
    and the entries sorting. It basicalic combining chart entries and and
    column nesting schema to build a tree and navigate though it"""

    def __init__(self):
        self.schema = None
        self.tree = None
        self.all_entries = None
        self.entries = None
        self.deph = 0
        self.nodes = []
        self.outputs = {}
        self.filters = []

    def is_empty(self):
        return not bool(self.tree) or not bool(self.tree.children())

    def values_for_key(self, key):
        return sorted({str(e.data.get(key)) for e in self.entries})

    def list_common_keys(self):
        if not self.entries:
            return []
        if len(self.entries) == 1:
            return self.entires[0].data.keys()
        return sorted(set(
            self.entries[0].data.keys()).intersection(
                *[e.data.keys() for e in self.entries[1:]]))

    def list_schema_keys(self):
        if not self.schema:
            return None
        return all_schema_keys(self.schema)

    def reevaluate_weights(self, function):
        for entry in self.all_entries:
            entry.weight = function(entry)

    def build_tree(self, collapsed=False):
        self.tree, self.deph, self.nodes, self.outputs = hierarchize(
            self.entries, self.schema, collapsed=collapsed)

    def set_schema(self, schema, collapsed=False):
        self.schema = schema
        if self.entries is not None:
            self.build_tree(collapsed)

    def filtered_entries(self):
        if self.filters:
            return [
                e for e in self.all_entries
                if all(f.filter(e) for f in self.filters)]
        return self.all_entries[:]

    def set_entries(self, entries=None):
        self.all_entries = entries or self.all_entries
        if not self.all_entries:
            return False
        self.entries = self.filtered_entries()
        try:
            if self.schema is not None:
                self.build_tree()
                return True
        except KeyError:
            return False
        return True

    def list_branches(self):
        return sorted({o.branch() for o in self.outputs.values()})

    def get_branch(self, path):
        node = self.tree
        keys = path.split('|')
        for key in keys:
            node = node[key]
        return node

    def expand_level(self, level, state):
        for node in self.nodes.values():
            if node.level == level:
                node.expanded = state

    def expand_hierarchy(self, node, state):
        for node in node.flat():
            node.expanded = state

    def maximum(self):
        return max((
            sum(self.entries[i].weight for i in o.all_indexes())
            for o in self.outputs.values()), default=0)

    def total(self):
        return sum(e.weight for e in self.entries)

    def current_deph(self):
        return max(
            output.parent.level for output in self.outputs.values()
            if output.is_expanded())

    def add_filter(self, filter):
        self.filters.append(filter)
        self.set_entries()

    def remove_filter(self, index):
        del self.filters[index]
        self.set_entries()

    def replace_filter(self, index, filter):
        self.filters[index] = filter
        self.set_entries()

    def clear_filters(self):
        self.filters = []
        self.set_entries()


class ChartOutput:
    """
    This the tree ouput node
    """
    def __init__(self, key, parent):
        self.index = uuid.uuid1()
        self.parent = parent
        self.key = key
        self.content = defaultdict(list)

    def __repr__(self):
        return '-' * self.parent.level + f'--> {self.key}'

    def is_expanded(self):
        return all(n.expanded for n in self.parents()[:-1])

    def append(self, value, index):
        self.content[value].append(index)

    def row(self):
        if not self.parent:
            return 0
        return sorted(
            self.parent.outputs(),
            key=lambda x: str(x.key)).index(self)

    def row_count(self):
        if not self.parent:
            return 1
        return len(self.parent.children()) + len(self.parent.outputs())

    def branch(self):
        try:
            return '|'.join(self.parent.branch) + f'|{self.key}'
        except TypeError:
            print(self.parent.branch, self.key)
            raise

    def all_indexes(self):
        return [v for values in self.content.values() for v in values]

    def parents(self):
        node = self
        parents = []
        while node.parent:
            parents.append(node.parent)
            node = node.parent
        return sorted(parents, key=lambda n: n.level)


class ChartFilter:
    def __init__(self, key, operator, values):
        self.key = key
        self.operator = operator
        self.values = values

    @staticmethod
    def deserialize(data):
        return ChartFilter(data['key'], data['operator'], data['values'])

    def serialize(self):
        return {
            'key': self.key, 'operator': self.operator, 'values': self.values}

    def filter(self, chart):
        if self.operator == 'in':
            return chart.data[self.key] in self.values
        if self.operator == 'not in':
            return chart.data[self.key] not in self.values


class ChartNode:
    def __init__(
            self, key=None, value=None, branch=None,
            path=None, parent=None, level=0):
        self.index = uuid.uuid1()
        self.parent = parent
        self.key = key
        self.expanded = True
        self.level = level
        self.value = value
        self.branch = branch
        self.path = path
        self._children = {}
        self._outputs = {}

    def __repr__(self):
        return '-' * self.level + f' {self.key}: {self.value}'

    def is_expanded(self):
        return all(n.expanded for n in self.parents())

    def delete_child(self, child):
        del self._children[child.key]

    def delete_output(self, output):
        del self._outputs[output.key]

    def parents(self):
        node = self
        parents = []
        while node.parent:
            parents.append(node.parent)
            node = node.parent
        return sorted(parents, key=lambda n: n.level)

    def is_fork(self):
        return bool(self._children) and bool(self._outputs)

    def row(self):
        if not self.parent:
            return 0
        children = self.parent.children()
        return children.index(self) + len(self.parent.outputs())

    def outputs(self):
        return sorted(list(self._outputs.values()), key=lambda x: str(x.key))

    def row_count(self):
        if not self.parent:
            return 1
        return len(self.parent.children()) + len(self.parent.outputs())

    def append(self, key, value, index):
        output = self._outputs.setdefault(key, ChartOutput(key, self))
        output.append(value, index)
        return output

    def child(self, child, key, branch, path):
        node = self._children.setdefault(
            child, ChartNode(
                key=key,
                value=child,
                branch=branch,
                path=path,
                parent=self,
                level=self.level + 1))
        return node

    def children(self):
        return sorted(
            list(self._children.values()), key=lambda x: str(x.value))

    def flat(self):
        nodes = [self]
        for child in self.children():
            nodes.extend(child.flat())
        return nodes

    def all_outputs(self):
        outputs = list(self.outputs())
        for child in self.flat():
            outputs.extend(child.outputs())
        return outputs


def all_schema_keys(schema):
    flatten = flatten_schema(schema)
    return sorted({key for path in flatten for key in path})


def list_available_keys(data):
    return set(data[0].keys()).intersection(*[d.keys() for d in data[1:]])


def flatten_schema(schema, current_path=None):
    if current_path is None:
        current_path = []
    result = []
    for key, value in schema.items():
        new_path = current_path + [key]
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    result.append(tuple(new_path + [item]))
                elif isinstance(item, dict):
                    result.extend(flatten_schema(item, new_path))
    return result


def schema_to_tree(schema):
    root = ChartNode()
    branches = flatten_schema(schema)
    nodes = {}
    outputs = {}
    for branch in branches:
        node = root
        for key in branch[:-1]:
            node = node.child(key, key, branch[:-1], path=branch)
            nodes[node.index] = node
        output = node.append(branch[-1], branch[-1], None)
        outputs[output.index] = output
    return root, nodes, outputs


def tree_to_schema(root):
    outputs = root.all_outputs()
    schema = {}
    for output in outputs:
        root, *path, output = output.branch().split('|')
        main = schema.setdefault(root, [])
        if not path:
            main.append(output)
            continue
        parent = main
        for key in path:
            child = next((e for e in parent if isinstance(e, dict)), None)
            if child is None:
                child = {}
                parent.append(child)
            parent = child.setdefault(key, [])
        parent.append(output)
    return schema


def hierarchize(entries, schema, collapsed=False):
    """
    This is the function building the tree from entries and schema.
    """
    root = ChartNode()
    branches = flatten_schema(schema)
    deph = 0
    nodes = {}
    outputs = {}
    for index, entry in enumerate(entries):
        for branch in branches:
            targets = [entry.data[value] for value in branch]
            node = root
            for target, key in zip(targets[:-1], branch[:-1]):
                node = node.child(target, key, branch[:-1], path=targets)
                nodes[node.index] = node
                node.expanded = not collapsed
            output = node.append(branch[-1], targets[-1], index)
            outputs[output.index] = output
            deph = max((deph, node.level))

    return root, deph, nodes, outputs
