import os

from rosdistro.verify import verify_files_identical

from .fold_block import Fold

FILES_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def test_verify_files_identical():
    with Fold() as fold:
        print("""Checking if index.yaml and all referenced files comply to the formatting rules.
If this fails you can run 'rosdistro_reformat index.yaml' to help cleanup.
'rosdistro_reformat' shows the diff between the current files and their expected formatting.
""")

        index_url = 'file://' + FILES_DIR + '/index.yaml'
        assert verify_files_identical(index_url), fold.get_message()
