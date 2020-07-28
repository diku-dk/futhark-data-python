from setuptools import setup, find_packages

setup(name='futhark-data',
      version='1.0',
      url='https://github.com/diku-dk/python-futhark-data',
      license='ISC',
      author='Troels Henriksen',
      author_email='athas@sigkill.dk',
      description='Reading and writing Futhark data files',
      packages=['futhark_data'],
      long_description=open('README.md').read(),
      long_description_content_type="text/markdown",
      classifiers=[
          "Programming Language :: Python :: 3",
          "License :: OSI Approved :: ISC License (ISCL)",
          "Operating System :: OS Independent",
      ],
      python_requires='>=3.6',
      zip_safe=True)
