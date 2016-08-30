import os

from rosdistro import get_index
from rosdistro.distribution_cache_generator import generate_distribution_caches

from scripts import eol_distro_names

INDEX_YAML = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'index.yaml'))


def test_build_caches():
    print("""
Checking if the 'package.xml' files for all packages are fetchable.
If this fails you can run 'rosdistro_build_cache index.yaml' to perform the same check locally.
""")
    index = 'file://' + os.path.abspath(INDEX_YAML)
    index = get_index(index)
    dist_names = sorted(index.distributions.keys())
    dist_names = [n for n in dist_names if n not in eol_distro_names]
    generate_distribution_caches(INDEX_YAML, dist_names=dist_names)
