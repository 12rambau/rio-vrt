Usage
=====

This section contains information about **rio vrt** to get you started.

Installation
------------

Use pip to install **rio vrt** in your environment:

.. code-block:: console

    pip install rio-vrt

Usage
-----

As straight forward as it should be: list all the file you want to gather and call the ``build_vrt`` method.

.. code-block:: python

    from rio_vrt import build_vrt

    raster_files = ["example.tif", "example2.tif", "...", "examplen.tif"]
    vrt_file = build_vrt("example.vrt", raster_files)
