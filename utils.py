from csv import reader as csv_reader, writer as csv_writer
from functools import reduce
from os import chdir, listdir, system
from os.path import abspath, curdir, isdir, isfile, join
from re import match as regex_match
from shutil import move, rmtree
from StringIO import StringIO
from unicodedata import normalize as unormalize


class CSV(object):
    @staticmethod
    def fields_in(csv_file):
        fields = None
        with open(csv_file, 'rb') as inf:
            fields = csv_reader(inf).next()
        return fields

    @staticmethod
    def get_entries_by_field(csv_file, field_names):
        fileFields = CSV.fields_in(csv_file)
        fKeys = map(lambda x: x.upper(), field_names)
        indices = {}
        for i in range(len(fileFields)):
            if fileFields[i].upper() in fKeys:
                indices[fileFields[i]] = i
        if len(indices.keys()) < len(field_names):
            return ['ERR'] + list(set(field_names)
                                  .difference(set(indices.keys())))
        acc = []
        with open(csv_file, 'rb') as inf:
            for line in csv_reader(inf):
                if line == fileFields:
                    continue
                acc.append(dict([(k, line[i])
                                 for k, i in indices.iteritems()]))
        return acc

    def __init__(self):
        pass


class DataTableFile(object):
    "A csv-file-like object"
    def __init__(self, delimiter=',', quotechar='"', contains_headers=True):
        self.file = StringIO()
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.containsHeaders = contains_headers

    def set_read_options(self, delimiter=',', quotechar='"',
                         contains_headers=True):
        "Configure parsing options CSV reader will use to extract data"
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.containsHeaders = contains_headers

    def write(self, *args):
        "File write method"
        return self.file.write(*args)

    def read(self, *args):
        "File read method"
        return self.file.read(*args)

    def readline(self, *args):
        "Read-line method, used by FTP storlines command"
        return self.file.readline(*args)

    def column(self, index):
        "Retrieve all entries in a given column by number or header name"
        idx = 0
        if type(index) == str:
            found = False
            for i, hdr in enumerate(self.headers):
                if index == hdr:
                    idx = i
                    found = True
            if not found:
                raise Exception('column', index, 'was not found')
        elif type(index) == int:
            idx = index
        acc = []
        for i, row in enumerate(self.rows):
            try:
                acc.append(row[idx])
            except IndexError as e:
                if i == (len(list(self.rows)) - 1):
                    pass  # forgive a blank last row
                else:
                    raise e
        return acc

    @property
    def headers(self):
        "Return or generate the list of table column headers"
        if not self.containsHeaders:
            return ['Column %d' % (i + 1)
                    for i in xrange(len(self.rows.next()))]
        else:
            return csv_reader(self.file.getvalue().split('\n'),
                              delimiter=self.delimiter,
                              quotechar=self.quotechar).next()

    @property
    def lines(self):
        "Iterator across raw lines of the table"
        for line in self.file.getvalue().split('\n'):
            yield line

    @property
    def rows(self):
        "Iterator across lines as list-rows of a csv-file"
        rdr = csv_reader(self.file.getvalue().split('\n'),
                         delimiter=self.delimiter,
                         quotechar=self.quotechar)
        if self.containsHeaders:
            rdr.next()  # discard headers
        for row in rdr:
            yield map(lambda x: x.strip() if (type(x) == str) else x, row)

    @classmethod
    def from_csv_file(cls, csv_filename, contains_headers=True):
        "Instantiate DataTableFile object from a standard csv-file"
        bufferObject = cls(contains_headers=contains_headers)
        with open(csv_filename, 'rb') as inf:
            rdr = csv_reader(inf)
            wri = csv_writer(bufferObject)
            for line in rdr:
                wri.writerow(line)
        return bufferObject


def included(list1, list2):
    "Whether all elements of list1 appear in list2"
    for elt in list1:
        if elt not in list2:
            return False
    return True


def ufix(s):
    """Strip non-ascii formatting from a string"""
    if type(s) == str:
        return s.strip()
    elif type(s) == unicode:
        return (unormalize('NFKD', s).encode('ascii', 'ignore')).strip()
    else:
        return str(s).strip()


def i10_from_string(s):
    "Take ISBN-10, ISBN-13, or Wholesale ISBN and return stripped ISBN-10"
    s = s.strip()
    for undesirableChar in ['-',  '"',  "'",  '_',  ',',  ';',  '.']:
        s = s.replace(undesirableChar, '')
    i10Match = regex_match(r'^[0-9]{9}[0-9xX]$', s)
    i13Match = regex_match(r'^978[0-9]{10}$', s)
    whlMatch = regex_match(r'^290[0-9]{10}$', s)
    if i13Match:
        return s[3:12] + i10_check(s[3:12])
    elif i10Match:
        return s
    elif whlMatch:
        return s[3:12] + i10_check(s[3:12])


def flatten(seq):
    """Official Python recursive flattening function"""
    l = []
    for elt in seq:
        t = type(elt)
        if t is tuple or t is list:
            for elt2 in flatten(elt):
                l.append(elt2)
        else:
            l.append(elt)
    return l


def add_to_clipboard(text):
    command = 'echo ' + text.strip() + '| clip'
    system(command)


def bring_files_up(in_path):
    """Eliminates a level of subdirectories, moving contents up"""
    chdir(in_path)
    for folder in [f for f in listdir(curdir) if isdir(f)]:
        for fname in listdir(folder):
            move(join(folder, fname), fname)


def flatten_dir_tree(directory):
    """
    Take a directory tree and flatten it, placing all terminal nodes in parent.
    """
    files = listdir(directory)
    dirs = []
    for f in files:
        if isdir(join(directory, f)):
            dirs.append(f)
    for d in dirs:
        dpath = join(abspath(directory), d)
        flatten_dir_tree(dpath)
        subfiles = listdir(dpath)
        for f in subfiles:
            if isfile(join(dpath, f)):
                move(join(dpath, f), join(abspath(directory), f))
            elif isdir(join(dpath, f)):
                rmtree(join(dpath, f))
        rmtree(join(directory, d))


def mapnull(fn, *args_list):
    "Map and silently discard the results of a function."
    for args in zip(*args_list):
        fn(*args)


def euclidean_distance(vecX, vecY):
    "Pythagorean calculation of distance in n-dimensional Euclidean space."
    return sum(map(lambda x, y: (x - y) ** 2.0, vecX, vecY)) ** 0.5


def choose(n, from_list, randint_fn=None):
    "Randomly select  n  elements of  from_list  [with optional  randint_fn ]."
    randint = None
    if not randint_fn:
        from random import randint
    else:
        randint = randint_fn
    llen = len(from_list)
    indices = [randint(0, llen - 1) for i in xrange(n)]
    checked = [indices[0]]
    for i, index in enumerate(indices[1:]):
        while index in checked:
            index = randint(0, llen - 1)
        checked.append(index)
        indices[i+1] = index
    return tuple([from_list[i] for i in tuple(indices)])


def pixel_color(pixel, format_spec="RGB"):
    "Convert a float-valued  pixel  of  format_spec  to HTML color string."
    cells = {}
    for i, letter in enumerate(format_spec):
        cells[letter] = pixel[i]
    cstr = "#"
    hexvals = "0123456789ABCDEF"
    for letter in "R", "G", "B":
        value = int(256 * cells[letter])
        cstr += hexvals[value / 16] + hexvals[value % 16]
    return cstr


def price2int(price_str):
    """Convert price string to integer (cents)"""
    price_str = str(price_str)
    flip = 1 if float(price_str) > 0 else -1
    if flip < 0:
        price_str = price_str.replace('-', '')
    try:
        halves = price_str.strip().split('.')
        if len(halves[1]) == 1:
            halves[1] = halves[1] + '0'
        elif len(halves[1]) > 2:
            halves[1] = halves[1][:2]
        return flip * 100 * int(halves[0]) + flip * int(halves[1])
    except:
        return flip * 100*int(price_str)


def int2price(price_int):
    """Convert integer price (cents) to dollars.cents string"""
    dollars = int(price_int / 100)
    cents = str(price_int % 100)
    while len(cents) < 2:
        cents = '0' + cents
    return str(dollars) + '.' + cents


def upc_check(upc_11):
    _result = 0
    for i, c in enumerate(str(upc_11)):
        _result += (2 * ((i+1) % 2) + 1) * int(c)
    return str((10 - (_result % 10)) % 10)


def i13_check(text_12):
    """ISBN-13 check-digit calculation"""
    _sum = 0
    for _i in range(0, 12):
        if _i % 2 == 0:
            _sum = _sum + int(text_12[_i])
        else:
            _sum = _sum + 3 * int(text_12[_i])
    return str((10 - (_sum % 10)) % 10)


def i10_check(text_9):
    """ISBN-10 check-digit calculation"""
    _sum = 0
    for _i in range(0, 9):
        _sum = _sum + int(text_9[_i]) * (10 - _i)
    _rv = (11 - (_sum % 11)) % 11
    if _rv == 10:
        _rv = 'X'
    return str(_rv)


def tk_center(win, ht=None, offset=(0, 0)):
    """Centers a Tkinter window, with virtual-height and x,y-offset"""
    win.update_idletasks()
    width = win.winfo_width()
    frmWidth = win.winfo_rootx() - win.winfo_x()
    height = win.winfo_height() if not ht else ht
    winWidth = width + (2 * frmWidth)
    titlebarHeight = win.winfo_rooty() - win.winfo_y()
    winHeight = height + titlebarHeight + frmWidth
    x = int(win.winfo_screenwidth() / 2) - int(winWidth / 2)
    y = int(win.winfo_screenheight() / 2) - int(winHeight / 2)
    win.geometry('{}x{}+{}+{}'.format(width, height,
                                      x + offset[0], y + offset[1]))
    win.deiconify()
    return ((x, y), offset)


def mean(vec):
    "Return the mean of a vector[/list/...]."
    return sum(vec) / float(len(vec))


def vce(vec):
    "Calculate the variance of a vector[/list/...]."
    return sum([(vi - mean(vec)) ** 2 for vi in vec]) / float(len(vec) - 1)


def sd(vec):
    "Return the standard deviation of a vector[/list/...]."
    return (vce(vec)) ** 0.5


def ctr(vec):
    "Center the values of a vector[/list/...] by returning diffs. from mean."
    return [(vi - mean(vec)) for vi in vec]


def scl(vec):
    "Scale the values of a vector[/list/...] by dividing each val. by the s.d."
    return [(vi / sd(vec)) for vi in vec]


def skew(vec):
    "Calculate the skewness statistic of a vector[/list/...]."
    return (sum([(vi - mean(vec)) ** 3 for vi in vec]) /
            (float(len(vec) - 1) * vce(vec) ** (1.5)))


def bct(vec, lambda_value=None, epsilon=1e-5, lambda_min=-5, lambda_max=5):
    "Perform a Box-Cox transformation of a vector[/list/...]."
    if lambda_value is None:
        return bct(vec,
                   de_minimize(lambda x: skew(bct(vec, x)),
                               0, [lambda_min], [lambda_max], 42, epsilon)[0])
    elif lambda_value == 0:
        from math import log
        return [log(v) for v in vec]
    else:
        return [(v ** lambda_value - 1) / lambda_value for v in vec]


def de_minimize(fn, tgt, mins, maxs, pop_size, epsilon=.001, max_gens=10000):
    "Good old fashioned single-objective Differential Evolution."
    from random import random

    def spawn(n):
        pop = []
        for i in range(n):
            vec = []
            for j, val in enumerate(mins):
                vec.append(mins[j] + (random() * (maxs[j] - mins[j])))
            pop.append(vec)
        return pop

    def eval_pop(pop):
        scores = []
        for p in pop:
            scores.append(fn(*p) - tgt)
        return scores

    def breed(pop, cx=.5, mf=.5):
        scores = eval_pop(pop)
        newpop = []
        for i, p in enumerate(pop):
            choices = list(choose(3, pop))
            while p in choices:
                choices.remove(p)
                choices.extend(list(choose(1, pop)))
            candidate = []
            for j, v in enumerate(p):
                if random() > mf:
                    newVal = (choices[0][j] +
                              cx * (choices[1][j] - choices[2][j]))
                    if newVal > maxs[j]:
                        newVal -= 2 * (newVal - maxs[j])
                    elif newVal < mins[j]:
                        newVal += 2 * (mins[j] - newVal)
                    candidate.append(newVal)
                else:
                    candidate.append(v)
            trial = fn(*candidate) - tgt
            if abs(trial) < abs(scores[i]):
                newpop.append(candidate)
            else:
                newpop.append(p)
        return newpop

    pop = spawn(pop_size)
    genCt = 1
    while genCt <= max_gens:
        pop = breed(pop)
        scores = eval_pop(pop)
        for i, p in enumerate(pop):
            if abs(scores[i]) < epsilon:
                return p
        genCt += 1


def nrm(vec, gt_zero=False):
    "Normalize a vector[/list/...] from 0..1 based on its max/min values."
    if gt_zero is True:
        gt_zero = .0001
    minval = min(vec) if not gt_zero else (min(vec) - gt_zero)
    return [(v - minval) / float(max(vec) - minval) for v in vec]


def underscores_to_camelCase(string):
    _new = ''
    _i = 0
    while _i < len(string):
        _nextLetter = string[_i]
        if _nextLetter != '_':
            _new += _nextLetter
        else:
            _i += 1
            try:
                _subsequentLetter = string[_i]
            except IndexError:
                _new += '_'
                continue
            if _subsequentLetter == '_':
                _new += '__'
            else:
                _new += _subsequentLetter.upper()
        _i += 1
    return _new


def assign_arguments_to_attributes(obj, attr_dict):
    """Sets object camelCase attributes by argument_names dict"""
    for arg_name, arg_value in attr_dict.iteritems():
        setattr(obj,
                underscores_to_camelCase(arg_name),
                arg_value)


def extract_attribute(obj, attr_string):
    "Like getattr, but supports nested value"
    attrs = attr_string.split('.')
    _obj = obj
    for i in xrange(len(attrs)):
        _obj = getattr(_obj, attrs[i])
    return _obj


def extattr(obj, attr_chain):
    "Like getattr, but supports nested value"
    return reduce(lambda x: getattr(obj, x), attr_chain.split('.'))
