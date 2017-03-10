import os

next_block_id = 1


class Fold(object):

    def __init__(self):
        global next_block_id
        self.block_id = next_block_id
        next_block_id += 1

    def __enter__(self):
        if os.environ.get('TRAVIS') == 'true':
            print('travis_fold:start:block%d' % self.block_id)

    def __exit__(self, type, value, traceback):
        if os.environ.get('TRAVIS') == 'true':
            print('travis_fold:end:block%d' % self.block_id)
