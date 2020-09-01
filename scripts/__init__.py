import os

from rosdistro import get_index

INDEX_V4_YAML = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'index-v4.yaml'))

index_v4 = get_index('file://' + os.path.abspath(INDEX_V4_YAML))
dist_names_v4 = list(sorted(index_v4.distributions.keys()))
eol_distro_names = [
    dist_name for dist_name in dist_names_v4 if index_v4.distributions[dist_name]['distribution_status'] == 'end-of-life']
