import os

from rosdistro.distribution_cache_generator import generate_distribution_caches

INDEX_YAML = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'index.yaml'))


def test_build_caches():
    print("""
Checking if the package.xml files for all packages are fetchable.
If this fails you can run 'rosdistro_build_cache index.yaml' to perform the same check locally.
""")

    generate_distribution_caches(INDEX_YAML)
