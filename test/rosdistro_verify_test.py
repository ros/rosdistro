import os

from rosdistro.verify import verify_files_identical

FILES_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def test_verify_files_identical():
    index_url = 'file://' + FILES_DIR + '/index.yaml'
    assert verify_files_identical(index_url)
