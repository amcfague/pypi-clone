import os
import urlparse
import xmlrpclib
from httplib import HTTPConnection
import time
import shutil

import lockfile


# XXX Replace this with the actual version!
USER_AGENT = "pypiclone/0.1"
DEFAULT_XMLRPC_HOST = "pypi.python.org"
DEFAULT_PACKAGE_HOST = "b.pypi.python.org"


class RemoteException(Exception): pass
class LocalException(Exception): pass

class MirrorNotFound(RemoteException): pass

class PypiSource(object):
    """
    Wraps calls to PyPi, usually in the form of XMLRPC requests.

    ``local_pypi_destination``
        The location to store the mirrored PyPi installation.  This will raise
        an IOError if the location cannot be written to.
    ``host``
        PyPi host to use; this should be the hostname only--and the host should
        implement the /simple URL.  Leave default to use one of the default
        PyPi mirrors.

        You can also use the bundled `netselect-pypi` to find the fastest PyPi
        mirror; however, it is not recommended that you run this often--once
        you have a close server, please continue to use it.
    """

    def __init__(self, local_pypi_destination, mirror=DEFAULT_PACKAGE_HOST):
        # Use the DEFAULT_PYPI_HOSTNAME if no host is passed.
        self.mirror_host = mirror

        # XXX Assert that this exists and is writable!
        self.local_pypi_destination = local_pypi_destination
        self.last_synchronized_filename = os.path.join(
            local_pypi_destination, "last-synchronized")

        # Establish a shared connection the XMLRPC server on PyPi.  This must
        # *always* use the XMLRPC server hosted on `pypi.python.org`.
        self._xmlrpc_conn = xmlrpclib.ServerProxy(
            "http://%s/pypi" % DEFAULT_XMLRPC_HOST)

        # According to :pep:`381`, this client should to authorize itself via
        # the User Agent string.
        self._xmlrpc_conn.useragent = USER_AGENT

        # Prepare the lockfile; we can't have multiple processes on the same
        # location calling this script.
        lockfile_location = os.path.join(local_pypi_destination, ".pypi.lock")
        self.__lockfile = lockfile.FileLock(lockfile_location)

        self._create_directory_structure()

    def _create_directory_structure(self):
        try:
            os.makedirs(self.local_pypi_destination)
        except:
            pass

    @property
    def last_synchronized(self):
        """
        :pep:`381` defines the `changelog` XMLRPC command, which takes a single
        timestamp, so that it can return only the changed packages.  This will
        return `None` if it has never been run, or the last_synchronized file
        is empty, or the timestamp that this mirror was last synchronized.

        Note that reading this without first acquiring the lock may result in
        this file changing when not expected.  Thus, if modifying the
        last_synchronized time, make sure to always acquire the lock first.
        """
        try:
            content = open(self.last_synchronized_filename, "r").read().strip()
            if not content:
                # The file was empty!  Assume this is a fresh run.
                return 0
        except IOError:
            # The file didn't exist; thus, this is our first time.
            return 0

    def update_last_synchronized(self, timestamp):
        """
        (Re)sets the timestamp in the local PyPi location.  Be careful when
        running this; if the run is NOT successful and you update this
        timestamp, you WILL miss out on packages!

        ``timestamp``
            Unix timestamp representing the time this was last sync'd.  This
            should be the time the package listing was retrieved from the
            server, NOT when this client finished retrieving the packages.
        """
        try:
            fd = open(self.last_synchronized_filename, "w+")
            fd.write("%d" % timestamp)
            fd.close()
        except IOError:
            raise Exception(
                "Could not write timestamp `{timestamp}` to `{filename}`! "
                "Please update this manually, or your mirror may be out of "
                "date!" % (timestamp, self.last_synchronized_filename))

    def synchronize(self):
        """
        Synchronizes the current PyPi mirror with this one.  If this is a new
        mirror, it will start fresh.  This will always acquire the lock.
        """
        http_conn = HTTPConnection(self.mirror_host)
        request_headers = {"User-Agent": USER_AGENT}

        def get_path_from_url(url_path):
            return urlparse.urlsplit(url_path)[2]

        def calculate_local_path(package_name, package_version, package_type,
                                 package_filename, python_version):
            return os.path.join(self.local_pypi_destination, "packages",
                                python_version, package_name[0], package_name,
                                package_filename)

        def retrieve_package(package_name, package_version):
            print "Retrieving", package_name, package_version
            all_package_urls = self._xmlrpc_conn.release_urls(package_name, package_version)
            for package_env in all_package_urls:
                package_filename = package_env['filename']
                python_version = package_env['python_version']
                package_type = package_env['packagetype']
                package_path = get_path_from_url(package_env['url'])
                print package_path

                local_file = calculate_local_path(
                    package_name, package_version, package_type,
                    package_filename, python_version)
                http_conn.request('GET', package_path, headers=request_headers)
                resp = http_conn.getresponse()
                try:
                    os.makedirs(os.path.dirname(local_file))
                except OSError:
                    pass
                shutil.copyfileobj(resp, open(local_file, "w+"))

        print "Preparing to lock..."
        with self.__lockfile:
            print "checking updated packages"
            # Call the updated_releases command to get a list of changed
            # objects; these are all lists of `[name, version]`.
            #updated_packages = self._xmlrpc_conn.updated_releases(
            #    self.last_synchronized)
            updated_packages = self._xmlrpc_conn.updated_releases(
                int(time.time()) - 30000)
            for package in updated_packages:
                retrieve_package(*package)
                return

        print "DONE"

        # Lastly, write the last-synchronized file
        self.update_last_synchronized(time.time())

if __name__ == "__main__":
    PypiSource("tmp_pypi_src").synchronize()
