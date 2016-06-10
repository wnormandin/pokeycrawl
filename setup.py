from setuptools import setup

setup(
    name="pokeycrawl",
    version="1.0.1a1",  # Alpha release
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
    packages=find_packages(exclude=['docs','tests']),
    license='MIT',
    description='A python webcrawler'
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers,Webmasters',
        'Topic :: Web Hosting :: Website Utilities',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7'
        ]
    keywords='spider crawler website indexing load-testing',
    )
