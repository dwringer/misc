from __future__ import print_function

from utils import mapnull, euclidean_distance, pixel_color

from dill import dump as dill_dump, load as dill_load

from math import exp
from random import shuffle
from sys import setrecursionlimit


DIRECTION_SYMBOLS = {'up': '^',
                     'left': '<',
                     'right': '>',
                     'down': 'v'}


def image_to_color_graph(filename_in, filename_out, width, height,
                         return_colors=False):
    from PIL import Image
    _img = Image.open(filename_in)
    _pixels = _img.load()
    _pixelArray = [_pixels[i, j]
                   for i in xrange(_img.width)
                   for j in xrange(_img.height)]
    shuffle(_pixelArray)
    _sample = map(list, _pixelArray[:min(len(_pixelArray), 10000)])
    _som = SOM(WrappedGrid(width, height))
    _som.fill_nodes(_sample)
    _som.train(_sample, 8)
    _som2 = SOM(WrappedGrid(width, height))
    for i, n in enumerate(_som.nodes):
        _som2.nodes[i].value = map(lambda x: x/256., n.value)
    _ng = NodeGraph(_som2.nodes)
    _ng.graphviz(filename_out)
    if return_colors:
        return _som, map(pixel_color, map(lambda x: x.value, _som.nodes))
    else:
        return _som


def image_filter(filename, output_file, output_size, som):
    from PIL import Image
    _img = Image.open(filename)
    _img = _img.resize(output_size)
    _pixels = _img.load()
    for i in xrange(_img.width):
        for j in xrange(_img.height):
            _pixels[i, j] = tuple(
                map(int, som.best_matching_unit(_pixels[i, j]).value))
    _img.save(output_file)


class Cell(object):
    id = 0

    def __init__(self):
        self.id = Cell.id
        Cell.id += 1


class WrappedGrid(object):
    def __init__(self, width, height):
        _nodeArray = []
        for i in xrange(width):
            _nodeArray.append([Cell() for j in xrange(height)])
        for j in xrange(height):
            for i in xrange(width):
                setattr(_nodeArray[i][j], 'right',
                        _nodeArray[(i+1) if (i < (width - 1)) else 0][j])
                setattr(_nodeArray[i][j], 'left',
                        _nodeArray[(i-1) if (i > 0) else (width - 1)][j])
                setattr(_nodeArray[i][j], 'up',
                        _nodeArray[i][(j-1) if (j > 0) else (height - 1)])
                setattr(_nodeArray[i][j], 'down',
                        _nodeArray[i][(j+1) if (j < (height - 1)) else 0])
                setattr(_nodeArray[i][j], 'dirs',
                        ['right', 'left', 'up', 'down'])
        self.nodes = []
        for row in _nodeArray:
            self.nodes.extend(row)
        self.sides = self.nodes


class SOMCell(object):
    "A single cell of a [Kohonen] Self-Organizing Map."
    def __init__(self, node_implementation):
        "Create the cell using a specified topological node implementation."
        self.value = None
        self.node = node_implementation
        self.dirs = []

    @property
    def distances(self):
        measures = {}
        for direction in self.dirs:
            measures[direction] = euclidean_distance(
                getattr(self, direction).value,
                self.value)
        return measures.iteritems()


class NodeGraph(object):
    "A graph of connected SOM nodes."
    def __init__(self, nodes):
        "Create the node graph given a set of  nodes ."
        self.nodes = nodes

    def color_view(self, pixel_format='RGB'):
        "Show the color of each node and neighbors, indexed as  format_spec ."
        print('--------')
        for node in self.nodes:
            print(pixel_color(node.value, pixel_format))
            for direction in node.node.dirs:
                print(DIRECTION_SYMBOLS[direction],
                      pixel_color(
                          getattr(node, direction).value,
                          pixel_format))

    def graphviz(self, svg_filename, pixel_format='RGB'):
        from os import system
        self.to_dot_file('tmp.dot', pixel_format)
        system('dot -Tsvg tmp.dot > %s' % svg_filename)
        return svg_filename

    def to_dot_file(self, filename, color_format='RGB'):
        linksRepresented = []
        fileBody = "graph nodegraph {\n"
        for node in self.nodes:
            fileBody += ('\t' + '"' + pixel_color(node.value,
                                                  color_format) + '" ' +
                         '[style = "filled"];\n')
            fileBody += ('\t' + '"' + pixel_color(node.value,
                                                  color_format) + '" ' +
                         '[fillcolor = "' +
                         pixel_color(node.value, color_format).lower() +
                         '"];\n')
        for node in self.nodes:
            for otherNode in self.nodes:
                for direction in node.dirs:
                    if getattr(node, direction) == otherNode:
                        if (node, otherNode) not in linksRepresented:
                            linksRepresented.append((node, otherNode))
                            linksRepresented.append((otherNode, node))
                            fileBody += ('\t' +
                                         '"' +
                                         pixel_color(node.value) +
                                         '" -- "' +
                                         pixel_color(otherNode.value) +
                                         '";\n')
        fileBody += '}\n'
        with open(filename, 'wb') as outf:
            outf.write(fileBody)

    @property
    def error(self):
        "Average euclidean distance per graph edge."
        if len(self.nodes) == 1:
            return 0
        err = 0
        links = 0
        for node in self.nodes:
            for direction in node.node.dirs:
                err += euclidean_distance(node.value,
                                          getattr(node, direction).value)
                links += 1
        return err / links


class SOM(object):
    "Self-Organizing Map [Kohonen Map] utilizing a provided topology."
    def __init__(self, substrate, verbose=False, alt_graph=None):
        "Create an SOM with the given topological  substrate ."
        self.verbose = verbose if verbose is not True else 1
        if alt_graph:
            self.nodes = alt_graph.nodes
        else:
            self.nodes = []
        self.distanceCache = {}
        self.expFnCache = {}
        self.substrate = substrate
        self.printf("Assigning node data structures to faces")
        if not alt_graph:
            for node in self.substrate.sides:
                self.nodes.append(SOMCell(node))
        self.printf("Detecting node topology")
        self.learn_neighbors()

    def printf(self, *args):
        "Switchable diagnostic print function."
        if self.verbose:
            for i in xrange(self.verbose - 1):
                print('... ', end='')
            print(*args)

    @classmethod
    def thaw(cls, filename):
        "Reinstantiate SOM from dill-pickled file  filename ."
        itm = None
        with open(filename, 'rb') as inf:
            itm = dill_load(inf)
        return itm

    def fill_nodes(self, from_matrix):
        "Randomly assign values of  from_matrix  to nodes of the SOM."
        data = list(from_matrix)
        shuffle(data)
        shuffledData = data[:len(self.nodes)]
        for i, node in enumerate(self.nodes):
            node.value = shuffledData[i % len(shuffledData)]

    def best_matching_unit(self, value):
        "Return the node valued nearest [in euclidean distance] to  value ."
        bmu = None
        best = None

        for n in self.nodes:
            dist = euclidean_distance(value, n.value)
            if (bmu is None) or (dist < best):
                bmu = n
                best = dist
        return bmu

    def train(self, learning_matrix, step_count, step_fraction=1.0):
        "Train the SOM from  learning_matrix  over  step_count  iterations."
        data = learning_matrix
        for step in xrange(step_count):
            self.printf("Training step", step)
            self.printf("Shuffling pixels")
            shuffle(data)
            self.printf("Truncating pixels and training")
            for d in data[:int(step_fraction * len(data))]:
                self.update(d, step, max_step=step_count)

    def update(self, value, step, **kwargs):
        "Apply weights to SOM nodes from  value , by iteration  step ."
        bmu = self.best_matching_unit(value)
        for n in self.nodes:
            theta = self.neighborhood(bmu, n, step, **kwargs)
            for i, elt in enumerate(n.value):
                n.value[i] = n.value[i] + theta * (value[i] - n.value[i])

    def learn_neighbors(self):
        "Infer node topology from underlying implementation."
        self.distanceCache = {}
        for n in self.nodes:
            for direction in n.dirs:
                delattr(n, direction)
            n.dirs = n.node.dirs
            for node in self.nodes:
                for direction in n.node.dirs:
                    if node.node.id == getattr(n.node, direction).id:
                        setattr(n, direction, node)
                        break

    def neighborhood(self, nodeU, nodeV, step,
                     max_step=100, max_width=5):
        "A parametric exponential neighborhood function for weighting."
        if step >= max_step:
            raise Exception('Step out of range')
        elif max_width < 2:
            raise Exception('Width must be >1')
        width = max_width - (max_width * (float(step) / max_step))
        return self.exp_fn(self.distance(nodeU, nodeV), width)

    def exp_fn(self, distance, width):
        "Memoized version of exponential component to neighborhood function."
        if distance is None:
            return 0
        if (distance, width) in self.expFnCache:
            return self.expFnCache[distance, width]
        result = exp((-1 * distance ** 2) / (2 * width ** 2))
        self.expFnCache[distance, width] = result
        return result

    def compute_distances(self):
        "Precompute distances between all nodes in the SOM."
        us = []
        vs = []
        for i in xrange(len(self.nodes)):
            us.extend([self.nodes[i] for j in xrange(len(self.nodes))])
            vs.extend([n for n in self.nodes])
        mapnull(self.distance, us, vs)

    def distance(self, nodeU, nodeV):
        "Return the topological distance between  nodeU  and  nodeV ."
        if nodeU == nodeV:
            return 0
        elif (nodeU, nodeV) in self.distanceCache:
            return self.distanceCache[nodeU, nodeV]
        distance = 0

        def neighbors(n):
            ns = []
            for direction in n.node.dirs:
                ns.append(getattr(n, direction))
            return set(ns)

        def set_neighbors(node_set):
            result = []
            for n in node_set:
                result.extend(neighbors(n))
            return set(result) - node_set
        testSet = set([nodeU])
        while True:
            distance += 1
            if distance >= len(self.nodes):
                distance = None
                break
            extendedSet = set_neighbors(testSet)
            if nodeV in extendedSet:
                break
            else:
                testSet = testSet.union(extendedSet)
        self.distanceCache[nodeU, nodeV] = distance
        self.distanceCache[nodeV, nodeU] = distance
        return distance

    def crystallize(self, filename):
        "Save the entire SOM to a dill-pickled file  filename ."
        setrecursionlimit(10000)
        with open(filename, 'wb') as outf:
            dill_dump(self, outf)

    def describe(self):
        "Display information about connected nodes."
        for n in self.nodes:
            print(n.node.id)
            print('---')
            for nn in self.nodes:
                print(n.node.id, '=>', nn.node.id, '::',
                      self.distance(n, nn))
