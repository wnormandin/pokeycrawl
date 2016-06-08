from setuptools import setup

setup(
    name="pokeycrawl",
    version="1.0",
    install_requires=[
        'mechanize',
        'urlparse',
        'random',
        'signal',
        'socket',
        'time',
        'multiprocessing',
        'Queue',
        'argparse',
        'os','sys',
        'operator'
        ],
    author='Bill Normandin',
    author_email='bill@pokeybill.us',
    url='https://github.com/wnormandin/pokeycrawl',
    packages=['pokeycrawl'],
    license='MIT',
    description='A python webcrawler for load-testing and site indexing'
    )
