==================
rr.opt.mcts.simple
==================

.. image:: https://readthedocs.org/projects/rroptmctssimple/badge/?version=latest
    :target: http://rroptmctssimple.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

A pure-Python implementation of Monte Carlo tree search. This simple version can be used to get a basic understanding of the algorithm and do some small experiments. When you feel comfortable, you should check out the full-blown implementation ``rr.opt.mcts.full``, which has the same usage interface and provides several additional features.


Python compatibility
--------------------

Compatible with Python 2.7+ and 3.5+ (thanks to the ``future`` library). The code may or may not work under earlier versions of Python 3 (perhaps back to 3.3).


Installation
------------

.. code-block:: bash

    pip install git+https://github.com/2xR/rr.opt.mcts.simple.git


In order to avoid polluting your system's Python installation, we recommend creating and installing into a `virtualenv <https://virtualenv.pypa.io/en/stable/>`_ with the following steps:

.. code-block:: bash

    virtualenv venv
    source venv/bin/activate  # venv\Scripts\activate on Windows
    pip install git+https://github.com/2xR/rr.opt.mcts.simple.git


Contributing
------------

Contributions are welcome through github pull requests (tests would sure be nice to have... :P).
