from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'requirements.txt')) as f:
    reqs = f.read().split()

with open(path.join(here, 'README.md')) as f:
    readme = f.read()

with open(path.join(here, 'cursewords', 'version')) as f:
    version = f.read().strip()

setup(
    name='cursewords',
    version=version,
    description='A terminal-based crossword puzzle solving interface',
    long_description=readme,
    long_description_content_type='text/markdown',
    url='https://github.com/thisisparker/cursewords',
    author='Parker Higgins',
    author_email='parker@parkerhiggins.net',
    classifiers=[
        'Environment :: Console :: Curses',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Programming Language :: Python :: 3',
        'Topic :: Games/Entertainment :: Puzzle Games',
    ],
    packages=find_packages(),
    python_requires='>=3.4',
    install_requires=reqs,
    package_data={
        'cursewords': ['version']
    },
    entry_points={
        'console_scripts': [
            'cursewords=cursewords:main',
        ],
    },
    keywords='puz crossword crosswords xword xwords puzzle acrosslite'
)
