:html_theme.sidebar_secondary.remove:


rio VRT
=======

**rio vrt** has been build to allow users in pure Python to build a vrt without installing GDAL in their environment.
This lib is only relying on `rasterio <https://rasterio.readthedocs.io/en/stable/>`__.

As a start it supports files:
- with same projection
- with same number of bands
- does not support colortable

Other functionalities from the original `buildvrt GDAL <https://gdal.org/programs/gdalbuildvrt.html>`__ method will be added upon request.

.. toctree::
   :hidden:

   usage
   contribute
   API <api/modules>

Documentation contents
----------------------

The documentation contains 3 main sections:

.. grid:: 1 2 3 3

   .. grid-item::

      .. card:: Usage
         :link: usage.html

         Usage and installation

   .. grid-item::

      .. card:: Contribute
         :link: contribute.html

         Help us improve the lib.

   .. grid-item::

      .. card:: API
         :link: api/modules.html

         Discover the lib API.
