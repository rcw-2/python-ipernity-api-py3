from distutils.core import setup

with open('README.txt') as f:
    long_description = f.read()

setup(name='ipernity_api_py3',
      version='0.14',
      description='Python Ipernity API',
      long_description=long_description,
      author='rcw-2',
      author_email='github@rcw-2.de',
      url='https://github.com/rcw-2/python-ipernity-api-py3',
      license='Apache 2.0',
      packages=['ipernity_api'],
      platforms=['any'],
      classifiers=[
          'Development Status :: 3 - Alpha',
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python :: 3 :: Only',
          'Topic :: Utilities',
      ],
      python_requires = '>=3.8',
      install_requires = ['requests'])
