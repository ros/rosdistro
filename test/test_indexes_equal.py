import os

from rosdistro import get_index

from .fold_block import Fold

INDEX_V3_YAML = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'index.yaml'))
INDEX_V4_YAML = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'index-v4.yaml'))


def test_build_caches():
    with Fold():
        print('Checking that the index.yaml and index-v4.yaml files contain '
              'the same information expect additional metadata in the v4.')
        index_v3 = get_index('file://' + os.path.abspath(INDEX_V3_YAML))
        index_v4 = get_index('file://' + os.path.abspath(INDEX_V4_YAML))

        dist_names_v3 = list(sorted(index_v3.distributions.keys()))
        dist_names_v4 = list(sorted(index_v4.distributions.keys()))
        assert dist_names_v3 == dist_names_v4, \
            'Different set of distribution names'

        for dist_name in dist_names_v3:
            dist_v3_data = index_v3.distributions[dist_name]
            dist_v4_data = index_v4.distributions[dist_name]

            for key, value in dist_v3_data.items():
                assert key in dist_v4_data, \
                    "For distribution '%s' index.yaml contains the key '%s' " \
                    "but v4 doesn't contain it" % (dist_name, key)
                assert dist_v4_data[key] == value, \
                    "For distribution '%s' both yaml files contains the key " \
                    "'%s' but with different values" % (dist_name, key)
