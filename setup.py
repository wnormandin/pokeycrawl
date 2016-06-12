from setuptools import setup,find_packages

setup(
    name="pokeycrawl",
    version="0.1.1a1",  # Alpha release
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
    url='https://github.com/wnormandin/pokeycrawl/releases/tag/0.1.1a1',
    packages=find_packages(exclude=['docs','tests']),
    license='MIT',
    description='A python webcrawler',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP :: Indexing/Search',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7'
        ],
    keywords='spider crawler website indexing load-testing',
    )
