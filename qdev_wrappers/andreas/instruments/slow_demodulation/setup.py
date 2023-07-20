from setuptools import setup, find_packages

setup(
    name='slow_demodulation',
    version='0.1',
    description=(
        'experimental package fro slow demodulation of signals '
        'provided through QCoDeS'),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Topic :: Scientific/Engineering'
    ],
    packages=find_packages(),
    install_requires=[
        'qcodes>=0.7',
    ],
    python_requires='>=3'
)
