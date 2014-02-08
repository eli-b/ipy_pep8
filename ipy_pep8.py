"""
Helper utility to PEP8 check Python code in IPython notebooks.
"""
import json
import collections
import os
import pep8
import autopep8
from optparse import OptionParser


TEMPLATE_IPYTHON_PRELUDE = """import numpy as np
"""


def find_notebooks(start_directory, extension="ipynb"):
    """
    Finds all notebooks in the start directory.
    """
    notebooks = []
    for root, _, files in os.walk(start_directory):
        notebooks += [os.path.join(root, notebook) for notebook in files
                      if notebook.endswith(extension)]
    return notebooks


def read_notebook(notebook):
    """
    Read the source code in a IPython notebook.
    """
    with open(notebook, 'r') as handle:
        data = json.load(handle, object_pairs_hook=collections.OrderedDict)
        # The second parameter enables preserving the order of the JSON fields
        # to minimize changes in the file
    return data
    
def get_code_cells(notebook_data, notebook_name='This notebook'):
    try:
        return ((cell_num, cell['input']) for cell_num, cell
                in enumerate(notebook_data['worksheets'][0]['cells'])
                if cell['cell_type'] == u'code')
    except IndexError:
        print("%s is not a valid notebook." % (notebook, ))
        return []


def check_code(cells):
    """
    Check the code in the cells with pep8, returning True iff there are no errors.
    """
    style = pep8.StyleGuide(parse_argv=False, config_file=True)
    
    num_errors = 0

    for cell_num, cell_lines in cells:
        print('checking code cell %d' % (cell_num, ))
        #cell_lines = [TEMPLATE_IPYTHON_PRELUDE] + cell_lines + ["\n\n\n"]
        checker = pep8.Checker(lines=cell_lines, options=style.options)
        num_errors += checker.check_all()

    if num_errors == 0:
        return True
    else:
        return False


def fix_code(cells, options):
    """
    Returns code lines fixed with autopep8.
    """
    options = '- ' + options
    options, args = autopep8.parse_args(options.split())
    fixed_cells = []
    for cell_num, cell_lines in cells:
        fixed_code = autopep8.fix_lines(cell_lines, options)
        fixed_cells.append((cell_num, fixed_code.splitlines(True)))
    return fixed_cells


def update_code_cells(notebook_data, code_cells):
    for cell_num, cell_lines in code_cells:
        notebook_data['worksheets'][0]['cells'][cell_num]['input'] = cell_lines


def write_notebook(notebook, data):
    with open(notebook, 'w') as handle:
            data = json.dump(data, handle, indent=1, separators=(',', ': '))


def process_files(start_directory, options):
    """
    Checks all files under start directory.
    """
    failfast = options.failfast

    results = []
    
    notebooks = find_notebooks(start_directory)
    for notebook in notebooks:
        print('Processing notebook %s' % (notebook,))
        notebook_data = read_notebook(notebook)
        code_cells = get_code_cells(notebook_data)
        if not options.autopep8:
            result = check_code(code_cells)
        else:
            fixed_code_cells = fix_code(code_cells, options.autopep8_args)
            update_code_cells(notebook_data, fixed_code_cells)
            write_notebook(notebook, notebook_data)
            result = True # Everything's fixed automatically
        results.append(result)
        if failfast and not result:
            break
    return results

if __name__ == "__main__":
    PARSER = OptionParser()
    PARSER.add_option("-a", "--autopep8", action="store_true",
                      help="fix notebooks in-place with autopep8")
    PARSER.add_option("-f", "--fail-fast", dest="failfast", action="store_true",
                      help="fail when the first notebook with an error is"
                           "encountered")
    PARSER.add_option('--autopep8-args', dest='autopep8_args', action='store',
                      type='string', default='--ignore=E501',
                      help="(in quotes) passed to autopep8. "
                           "pep8 arguments can be passed via its config file.")
    (OPTIONS, ARGS) = PARSER.parse_args()

    if len(ARGS) == 0:
        SUCCESSES = process_files(".", OPTIONS)
    else:
        SUCCESSES = sum((process_files(arg, OPTIONS) for arg in ARGS), [])
    if all(SUCCESSES):
        exit(0)
    else:
        exit(1)