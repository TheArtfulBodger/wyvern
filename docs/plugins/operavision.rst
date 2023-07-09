Operavision Downloader
======================

Factory
-------

.. list-table::

 * - **Name**
   - Operavision Downloader
 * - **Description**
   - Download performances from operavision.eu
 * - **Key**
   - operavision
 * - **Required Configurations**
   - None
 * - **Optional Configurations**
   - None
 * - **Required Secrets**
   - None
 * - **Optional Secrets**
   - None

How It Works
------------

 #. Loads ``operavision.eu/performances``
 #. Iterates over elements matching ``.newsItem``

    #. Add `Youtube job <yt_dlp.html>`_ from ``a.youtube``'s ``data-video-id``
       element

    #. Add NFO job based off of performance URL