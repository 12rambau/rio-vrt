
rio VRT
=======

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg?logo=opensourceinitiative&logoColor=white
    :target: LICENSE
    :alt: License: MIT

.. image:: https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg?logo=git&logoColor=white
   :target: https://conventionalcommits.org
   :alt: conventional commit

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
   :alt: Black badge

.. image:: https://img.shields.io/badge/code_style-prettier-ff69b4.svg?logo=prettier&logoColor=white
   :target: https://github.com/prettier/prettier
   :alt: prettier badge

.. image:: https://img.shields.io/badge/pre--commit-active-yellow?logo=pre-commit&logoColor=white
    :target: https://pre-commit.com/
    :alt: pre-commit

.. image:: https://img.shields.io/pypi/v/rio-vrt?color=blue&logo=pypi&logoColor=white
    :target: https://pypi.org/project/rio-vrt/
    :alt: PyPI version

.. image:: https://img.shields.io/github/actions/workflow/status/12rambau/rio-vrt/unit.yaml?logo=github&logoColor=white
    :target: https://github.com/12rambau/rio-vrt/actions/workflows/unit.yaml
    :alt: build

.. image:: https://img.shields.io/codecov/c/github/12rambau/rio-vrt?logo=codecov&logoColor=white
    :target: https://codecov.io/gh/12rambau/rio-vrt
    :alt: Test Coverage

.. image:: https://img.shields.io/readthedocs/rio-vrt?logo=readthedocs&logoColor=white
    :target: https://rio-vrt.readthedocs.io/en/latest/
    :alt: Documentation Status

.. image:: https://img.shields.io/badge/all_contributors-0-orange.svg
    :alt: All contributors
    :target: AUTHORS.rst

Overview
--------

A simple librairy to build a vrt from multiple raster source relying only on rasterio.

.. code-block:: python

    from rio_vrt import build_vrt

    raster_files = ["example.tif", "example2.tif", "...", "examplen.tif"]
    vrt_file = build_vrt("example.vrt", raster_files)

Credits
-------

This package was created with `Cookiecutter <https://github.com/cookiecutter/cookiecutter>`__ and the `12rambau/pypackage <https://github.com/12rambau/pypackage>` project template.
