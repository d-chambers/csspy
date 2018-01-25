import sys
from pathlib import Path
from os.path import join, dirname, abspath

import pytest


# --------- Add key paths to pytest namespace


TEST_PATH = abspath(dirname(__file__))
PKG_PATH = dirname(TEST_PATH)
TEST_DATA_PATH = join(TEST_PATH, 'test_data')
ANF_DIR = join(TEST_DATA_PATH, 'events_usarray_2007_08')
sys.path.insert(0, PKG_PATH)  # make package importable


class CSS:
    """ A class for holding a reference to css files """
    def __init__(self, dir):
        path = Path(dir)
        assert path.exists()
        self.extentions = {}

        for file in path.rglob('*'):
            if '.' in file.name:
                self.extentions[file.name.split('.')[-1]] = file
            else:
                self.extentions[None] = file

    def __getattr__(self, item):
        try:
            return self.extentions[item]
        except KeyError:
            return getattr(self.extentions, item)

    def __getitem__(self, item):
        return self.extentions[item]


anf_test = CSS(ANF_DIR)


@pytest.fixture(scope='session')
def anf():
    return anf_test


def append_func_name(list_like):
    """ decorator to append function to list """

    def _decor(func):
        list_like.append(func.__name__)
        return func

    return _decor


def pytest_namespace():
    """ add the expected files to the py.test namespace """
    odict = {'test_data_path': TEST_DATA_PATH,
             'test_path': TEST_PATH,
             'package_path': PKG_PATH,
             'append_func_name': append_func_name,
             'anf': anf_test,
             'anf_dir': ANF_DIR,
             }
    return odict
