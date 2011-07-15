import logging
import os
import shutil
import urllib2
import urlparse


XMLRPC_HOST = "pypi.python.org"

log = logging.getLogger(__name__)


__all__ = ['PypiRepository', 'LocalPypiRepository', 'RemotePypiRepository']


class PypiRepository(object):

    def __init__(self, base_path):
        self.base_path = base_path

        # :pep:`381` states that a last_modified file MUST exist in the root of
        # the PyPi mirror.
        self.last_modified_path = self.build_resource("last_modified")

    def build_resource(self, *parts):
        raise NotImplementedError()

    def read_resource(self, resource_path):
        raise NotImplementedError()

    def save_resource(self, source, destination):
        raise NotImplementedError()

    def archive_path(self, uri):
        return self.build_resource(uri)

    def signature_path(self, package):
        return self.build_resource("serversig", package)

    def simple_path(self, package):
        return self.build_resource(
            self.base_path, "simple", package, "index.html")

    def read_archive(self, source):
        return self.read_resource(source)

    def read_signature(self, package):
        return self.read_resource(self.signature_path(package))

    def read_simple_path(self, package):
        return self.read_resource(self.simple_page_path(package))

    def write_archive(self, source, destination):
        self.save_resource(source, destination)

    def write_signature(self, package, source):
        self.save_resource(source, self.signature_path(package))

    def write_simple_page(self, package, source):
        self.save_resource(source, self.simple_page_path(package))


class LocalPypiRepository(PypiRepository):

    def __init__(self, *args, **kwargs):
        super(LocalPypiRepository, self).__init__(*args, **kwargs)

        # Create the local PyPi destination
        # TODO Only create parent dirs if specified
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)

    def build_resource_path(self, *parts):
        return os.path.join(*parts)

    def load_resource(self, resource, mode="r"):
        if hasattr(resource, "read"):
            return resource
        return open(self.build_resource_path(resource), mode)

    def read_resource(self, resource):
        return self.load_resource(resource).read()

    def save_resource(self, source, destination):
        with open(destination, "w+") as destination_fd:
            if hasattr(source, "read"):
                shutil.copyfileobj(source, destination_fd)
            else:
                destination_fd.write(source)


class RemotePypiRepository(PypiRepository):

    def __init__(self, *args, **kwargs):
        super(RemotePypiRepository, self).__init__(*args, **kwargs)

        url_parts = urlparse.urlsplit(self.base_path)

        # If there's no scheme, assume HTTP
        if not url_parts.scheme:
            url_parts.scheme = "http"

        # Make sure we actually have a hostname of some sort.
        if not url_parts.netloc or not url_parts.path:
            raise TypeError("URL does not include a hostname or a path.")

        self.base_path = urlparse.urlunsplit(url_parts)

    def build_resource_path(self, *parts):
        return urllib2.urljoin(self.base_url, *parts)

    def load_resource(self, resource):
        return urllib2.urlopen(self.build_resource_path(resource))

    def read_resource(self, resource):
        return self.load_resource(resource).read()

    def save_resource(self, source, destination):
        raise Exception("Cannot write to this Remote Repo.")
