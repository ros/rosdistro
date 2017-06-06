from collections import OrderedDict
import httplib
import os
from urlparse import urlparse

from catkin_pkg.package import parse_package_string
from ros_buildfarm.common import topological_order_packages
from rosdistro import get_index
from rosdistro.distribution_cache_generator import generate_distribution_cache

from scripts import eol_distro_names

from .fold_block import Fold

INDEX_YAML = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'index.yaml'))


def exists_webpage(pkg_name, pkgweb_root='http://wiki.ros.org/'):
    '''
    @summary: Returns false if a wiki page of the given package does not exist.
    @type pkg_name: str
    @rtype: bool
    @raise RuntimeError: When the webpage not existent.
    '''
    url = pkgweb_root + pkg_name
    p = urlparse(url)
    conn = httplib.HTTPConnection(p.netloc)
    conn.request('HEAD', p.path)
    resp = conn.getresponse()
    print('[DEBUG] {}: http response: {}'.format(pkg_name, resp.status))
    if 200 < resp.status:
        raise RuntimeError('{}: pkg does not exist. Open the URL, create one now.'.format(url))
    return True


def test_build_caches():
    with Fold():
        print("""Checking if the 'package.xml' files for all packages are fetchable.
If this fails you can run 'rosdistro_build_cache index.yaml' to perform the same check locally.
""")
        index = 'file://' + os.path.abspath(INDEX_YAML)
        index = get_index(index)
        dist_names = sorted(index.distributions.keys())
        dist_names = [n for n in dist_names if n not in eol_distro_names]

        errors = []
        caches = OrderedDict()
        for dist_name in dist_names:
            with Fold():
                try:
                    cache = generate_distribution_cache(index, dist_name)
                except RuntimeError as e:
                    errors.append(str(e))
                else:
                    caches[dist_name] = cache

                #for pkg_name, pkg_xml in cache.release_package_xmls.items():
                #    try:
                #        exists_webpage(pkg_name)
                #    except RuntimeError as e:
                #        errors.append('%s' % (e))

        # also check topological order to prevent circular dependencies
        for dist_name, cache in caches.items():
            pkgs = {}
            print("Parsing manifest files for '%s'" % dist_name)
            for pkg_name, pkg_xml in cache.release_package_xmls.items():
                pkgs[pkg_name] = parse_package_string(pkg_xml)
            print("Order all packages in '%s' topologically" % dist_name)
            try:
                topological_order_packages(pkgs)
            except RuntimeError as e:
                errors.append('%s: %s' % (dist_name, e))

        if errors:
            raise RuntimeError('\n'.join(errors))
