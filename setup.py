from setuptools import setup, find_packages
import lazynlp

setup(
    name='lazynlp',
    version=str(lazynlp.__VERSION__),
    packages=['lazynlp'],
    # packages=find_packages(),
    description='scrape and clean web data',
    long_description=str(
        'Library to scrape and clean webpages to create massive monolingual datasets'),
    url='https://huyenchip.com',
    license="Apache License, Version 2.0",
    install_requires=[],
    include_package_data=True,
)
