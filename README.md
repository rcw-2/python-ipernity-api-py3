# python-ipernity-api

Python wrapper for ipernity.com API, inspired by
[python-flickr-api](https://github.com/alexis-mignon/python-flickr-api).

Ported to Python3 by rcw-2. The original python-ipernity-api can be found
[on Github](https://github.com/oneyoung/python-ipernity-api).


## Main Features
* Object Oriented implementation
* Support full API on ipernity.com
* Support OAuth authentication (untested due to bug in Ipernity)
* Built-in document of Ipernity API
* Context sensitive objects, easy to use
* Simple GET request cache mechanism.
* Unittest to guarantee code quality


## Requirements
* Python 3
* [Requests](https://requests.readthedocs.io/)


## Installation

#### From source

```
git clone https://github.com/rcw-2/python-ipernity-api-py3.git
cd python-ipernity-api-py3
sudo python3 setup.py install  # for all user
python3 setup.py install --user # or for current user
```

#### From Pypi (not yet)

```
sudo pip install ipernity_api_py3  # for all user
pip install ipernity_api_py3 --user  # or for current user
```
See more info on [pypi page](https://pypi.python.org/pypi/ipernity_api_py3)

## Tutorial

Please see the
[tutorial of the original package](https://github.com/oneyoung/python-ipernity-api/wiki/Tutorial)
for a quick start.
