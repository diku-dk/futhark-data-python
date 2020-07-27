from setuptools import setup, find_packages

setup(name='futhark-data',
      version='1.0',
      url='https://github.com/diku-dk/futhark-data',
      license='ISC',
      author='Troels Henriksen',
      author_email='athas@sigkill.dk',
      description='Reading and writing Futhark data files',
      packages=find_packages(exclude=['tests']),
      long_description=open('README.md').read(),
      zip_safe=True)
