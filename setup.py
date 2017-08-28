#!/usr/bin/env python

"""Setup script."""

from setuptools import setup

from mcmp import __version__

setup(
    name='mcmp',
    version=__version__,
    description='Tool for downloading Curseforge Minecraft mods.',
    author='Alen Buhanec',
    author_email='alen.buhanec@gmail.com',
    url='http://github.com/buhanec/mcmp/',
    packages=['mcmp'],
    package_dir={
        'mcmp': 'mcmp'
    },
    entry_points={
        'console_scripts': [
            'mcmp = mcmp:main'
        ]
    }
)
