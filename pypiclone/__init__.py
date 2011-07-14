import logging
import os
import xmlrpclib
from xml.etree.ElementTree import ElementTree

from pypiclone.repository import LocalPypiRepository, RemotePypiRepository


log = logging.getLogger(__name__)

class MirrorClient(object):

    def __init__(self, local_pypi_path, download_mirror="b.pypi.python.org",
                 user_agent="pypiclone/0.1", synchronize_delete=True):
        """
        ``local_pypi_path``
            The path to the local directory where the PyPi mirror will be stored.
        ``download_mirror``
            Use this host to download packages.
        ``user_agent``
            The user agent to use. :pep:`381` requires that a parsable user agent
            be defined, that specifies both the application and version.
        ``synchronize_delete``
            When True, this will delete local packages that have been deleted from
            the remote server.
        """
        self.synchronize_delete = synchronize_delete
        self.local_pypi_repo = LocalPypiRepository(local_pypi_path)
        self.remote_pypi_repo = RemotePypiRepository(
            download_mirror, user_agent)

    def synchronize(self):
        # Setup the xmlrpclib connection to the main PyPi server.
        pypi_rpc = xmlrpclib.ServerProxy( "http://pypi.python.org/pypi")

    def synchronize_archives(self, package):
        log.info("Synhronizing %s package", package)
        # Retrieve the simple page from the local directory.
        tree = ElementTree.fromstring(
            self.local_pypi_repo.load_simple_page(package))

        # Parse each of the anchor tags, looking for a reference to
        # `../../packages`.  This is required because pep381 currently makes no
        # assertion that the anchor tags have any specific attributes (i.e.,
        # "download").
        for anchor_tag in tree.iter(".//a"):
            href = anchor_tag.get('href')
            if not href.startswith("../../packages"):
                continue
            
            # If the local file already exists, skip it
            local_package_path = self.local_pypi_repo.resource_path(href)
            if os.path.exists(local_package_path):
                log.debug("%s already synchronized.", local_package_path)
                continue

            # Create the directory structure as well (i.e.,
            # /packages/source/2.6/w/whatever)
            basedir = os.path.basename(local_package_path)
            if not os.path.exists(basedir):
                os.makedirs(basedir)

            # Save the remote archive locally
            remote_package = self.remote_pypi_repo.load_archive(href)
            self.local_pypi_repo.write_archive(
                local_package_path, remote_package)

            log.info("Synchronized %s", local_package_path)

    def synchronize_simple_page(self, package):
        """
        Downloads the page at :path:`/simple/{package}`, which contains a list
        of the packages.

        ``package``
            Name of the package to synchronize.
        """
        remote_simple_page = self.remote_pypi_repo.load_simple_page(package)
        self.local_pypi_repo.write_simple_page(remote_simple_page)

    def synchronize_signature(self, package):
        """
        Downloads the signature at :path:`/signature/{package}`, which is used
        to verify the correctness of the downloads.
        """
        remote_signature = self.remote_pypi_repo.load_signature(package)
        self.local_pypi_repo.write_signature(remote_signature)
