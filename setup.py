#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
from os.path import join, abspath, dirname, isdir, exists
from setuptools import setup

here = dirname(abspath(__file__))

with open(join(here, 'csspy', 'version.py'), 'r') as fi:
    content = fi.read().split('=')[-1].strip()
    __version__ = content.replace('"', '').replace("'", '')

with open('README.md') as readme_file:
    readme = readme_file.read()


# --- get sub-packages
def find_packages(base_dir='.'):
    """ setuptools.find_packages wasn't working so I rolled this """
    out = []
    for fi in glob.iglob(join(base_dir, '**', '*'), recursive=True):
        if isdir(fi) and exists(join(fi, '__init__.py')):
            out.append(fi)
    out.append(base_dir)
    return out


requirements = [
    'obspy',
    'pandas',
    'numpy',
]

extra_require = dict()

test_requirements = [
    'pytest'
]

setup_requirements = [
    'pytest-runner',
    'nbsphinx',
    'numpydoc'
]

setup(
    name='csspy',
    version=__version__,
    description="read support for center for seismic study 3.0 event format",
    long_description=readme,
    author="Derrick Chambers",
    author_email='djachambeador@gmail.com',
    url='https://github.com/d-chambers/csspy',
    packages=find_packages('csspy'),
    package_dir={'csspy': 'csspy'},
    include_package_data=True,
    install_requires=requirements,
    extra_require=extra_require,
    license="BSD",
    zip_safe=False,
    keywords='csspy',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3.6',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    setup_requires=setup_requirements,
)
