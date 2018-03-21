try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
import subprocess
import unidiff

DIFF_TARGET = 'origin/master'

def compute_unified_diff(target):
    cmd = ('git diff --unified=0 %s' % target).split()
    return subprocess.check_output(cmd)


def detect_lines(diffstr):
    """Take a diff string and return a dict of
    files with line numbers changed"""
    resultant_lines = {}
    # diffstr is already utf-8 encoded
    io = StringIO(diffstr)
    # Force utf-8 re: https://github.com/ros/rosdistro/issues/6637
    encoding = 'utf-8'
    udiff = unidiff.PatchSet(io, encoding)
    for filename in udiff:
        target_lines = []
        # if filename.path in TARGET_FILES:
        for hunk in filename:
            target_lines += range(hunk.target_start,
                                  hunk.target_start + hunk.target_length)
        resultant_lines[filename.path] = target_lines
    return resultant_lines
