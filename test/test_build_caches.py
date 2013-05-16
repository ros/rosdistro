import os

from rosdistro.release_cache_generator import generate_release_caches

INDEX_YAML = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'index.yaml'))


def test_build_caches():
    generate_release_caches(INDEX_YAML)
