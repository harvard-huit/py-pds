"""PDS Package Setup"""

import textwrap
from pathlib import Path

from setuptools import setup

here = Path(__file__).parent

about = {}
exec((here / 'pds' / '__version__.py').read_text(), about)

setup(
    name=about['__title__'],
    version=about['__version__'],
    author=about['__author__'],
    author_email=about['__author_email__'],
    maintainer=about['__maintainer__'],
    maintainer_email=about['__maintainer_email__'],
    packages=['pds', ],
    url=about['__url__'],
    license=about['__license__'],
    description=about['__description__'],
    long_description='',
    long_description_content_type='text/x-rst',
    # package_data={},
    install_requires = [
        'requests>=2.31.0',
        'dotmap>=1.3.30'
        ],
    tests_require = [],
    # test_suite = 'pds.tests',
    keywords = about['__keywords__'],
    classifiers = []
)