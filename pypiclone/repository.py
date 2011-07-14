import logging
import os
import shutil
import urllib2
import urlparse

from pypiclone import exceptions


XMLRPC_HOST = "pypi.python.org"

log = logging.getLogger(__name__)


__all__ = ['LocalPypiRepository', 'RemotePypiRepository']

def create_directory_structure(path, create_parents=False):
    """
    Creates the hierarchy, including parent directories if needed.

    ``path``
        The full (or relative, but this can be unsafe) path to create the
        directory hierarchy for.
    ``create_parents``
        If `True`, creates all parent directories as well as the directory
        specified by `path`.

    Returns `True` if directories were created, or `False` if no new
    directories were created.
    """
    if os.path.exists(path):
        return False

    if create_parents:
        os.makedirs(path)
    else:
        os.mkdir(path)

    return True


def normalize_url(url):
    url_parts = urlparse.urlsplit(url)
    
    # If there's no scheme, assume HTTP
    if not url_parts.scheme:
        url_parts.scheme = "http"

    if not url_parts.netloc or not url_parts.path:
        raise TypeError("URL does not include a hostname or a path.")

    return urlparse.urlunsplit(url_parts)


def delete_file(filename):
    os.remove(filename)


def read_file(filename):
    with open(filename, "w+") as fd:
        return fd.read()


def write_file(source, destination):
    with open(destination, "w+") as fd:
        if hasattr(source, "read"):
            shutil.copyfileobj(source, fd)
        else:
            fd.write(source)


class PypiRepository(object):

    def __init__(self, base_path):
        self.base_path = base_path

    def build_resource(self, *args):
        raise NotImplementedError()

    def load_resource(self, uri):
        raise NotImplementedError()

    def save_resource(self, uri):
        raise NotImplementedError()

    def signature_path(self, package):
        return self.build_resource(self.base_path, "serversig", package)

    def simple_path(self, package):




    def join_base_path(self, *args):
        return self.join(self.path, *args)

    def archive_path(self, uri):
        return self.join_base_path(uri)

    def signature_path(self, package):
        return self.join(self.path, "serversig", package)

    def simple_page_path(self, package):
        return os.path.join(self.path, "simple", package, "index.html")

    def load_archive(self, uri):
        raise NotImplementedError()

    def load_simple_page(self, package):
        raise NotImplementedError()

    def load_signature(self, package):
        raise NotImplementedError()

    def write_archive(self, uri, source):
        raise NotImplementedError()

    def write_simple_page(self, package, source):
        raise NotImplementedError()

    def write_signature(self, package, source):
        raise NotImplementedError()


class LocalPypiRepository(PypiRepository):

    def __init__(self, path):
        self.path = path
        self.last_modified_path = os.path.join(self.path, "last-modified")

        # Create the local PyPi destination
        create_directory_structure(path)

    @property
    def last_modified(self):
        try:
            return open(self.last_modified_path, "r").read()
        except IOError:
            return 0

    @last_modified.setter
    def last_modified(self, unix_timestamp):
        return open(self.last_modified_path, "w+").write(str(unix_timestamp))

    def archive_path(self, uri):
        return os.path.abspath(os.path.join(self.path, uri))

    def signature_path(self, package):
        return os.path.join(self.path, "serversig", package)

    def simple_page_path(self, package):
        return os.path.join(self.path, "simple", package, "index.html")

    def load_archive(self, uri):
        return open(self.archive_path(uri), "r")

    def load_signature(self, package):
        return open(self.signature_path, "r")

    def load_simple_page(self, package):
        return open(self.simple_page_path(package), "r")

    def write_archive(self, uri, source):
        write_file(source, self.archive_path(uri))

    def write_signature(self, package, source):
        write_file(source, self.signature_path(package))

    def write_simple_page(self, package, source):
        write_file(source, self.simple_page_path(package))


class RemotePypiRepository(PypiRepository):

    def __init__(self, base_url):
        self.base_url = normalize_url(base_url)

    def archive_path(self, uri):
        return urllib2.urljoin(self.base_url, uri)

    def signature_path(self, package):
        return urllib2.urljoin(self.base_url, "serversig", package)

    def simple_page_path(self, package):
        return urllib2.urljoin(self.base_url, "simple", package, "index.html")

    def load_archive(self, uri):
        return urllib2.urlopen(self.archive_path(uri))

    def load_signature(self, package):
        return urllib2.urlopen(self.signature_path(package))

    def load_simple_page(self, package):
        return urllib2.urlopen(self.simple_page_path(package))

    def write_archive(self, uri, source):
        raise exceptions.RemoteException(
            "Cannot write packages to a remote PyPi instance.")

    def write_signature(self, package, contents):
        raise exceptions.RemoteException(
            "Cannot write signature page to a remote PyPi instance.")

    def write_simple_page(self, package, contents):
        raise exceptions.RemoteException(
            "Cannot write simple page to a remote PyPi instance.")


#class PypiPackage(object):
#
#    def __init__(self, name, repository):
#        self.name = name
#        self.repo = repository
#
#    @property
#    def signature(self):
#        return read_file(self.repo.signature_path(self.name))
#
#    @signature.setter
#    def signature(self, source):
#        write_file(source, self.repo.signature_path(self.name))
#
#    @signature.deleter
#    def signature(self):
#        delete_file(self.repo.signature_path(self.name))
#
#    @property
#    def simple_page(self):
#        return read_file(self.repo.simple_page_path(self.name))
#
#    @simple_page.setter
#    def simple_page(self, source):
#        write_file(source, self.repo.simple_page_path(self.name))
#
#    @simple_page.deleter
#    def simple_page(self):
#        delete_file(self.repo.simple_page_path(self.name))
