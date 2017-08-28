import os

next_block_id = 1


class Fold(object):

    def __init__(self):
        global next_block_id
        self.block_id = next_block_id
        next_block_id += 1

    def get_message(self, msg=''):
        if os.environ.get('TRAVIS') == 'true':
            if msg:
                msg += ', '
            msg += "see folded block '%s' for details" % self.get_block_name()
        return msg

    def get_block_name(self):
        return 'block%d' % self.block_id

    def __enter__(self):
        if os.environ.get('TRAVIS') == 'true':
            print('travis_fold:start:%s' % self.get_block_name())
        return self

    def __exit__(self, type, value, traceback):
        if os.environ.get('TRAVIS') == 'true':
            print('travis_fold:end:%s' % self.get_block_name())
