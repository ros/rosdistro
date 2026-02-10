# Copyright 2025 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys


def _ensure_solib_in_ld_library_path():
    """
    Ensure that the _solib_k8 directory is in LD_LIBRARY_PATH.

    Bazel places shared library dependencies in _solib_k8/ under the runfiles
    root. The .so files have RUNPATH entries using $ORIGIN-relative paths that
    resolve correctly from the build output tree, but not from the runfiles
    tree when files are copied (e.g., Docker sandbox execution).

    Since glibc caches LD_LIBRARY_PATH at process startup, we must re-exec the
    Python process with the updated LD_LIBRARY_PATH if it's not already set.
    """
    runfiles_dir = os.environ.get('RUNFILES_DIR', '')
    if not runfiles_dir:
        return

    solib_dir = os.path.join(runfiles_dir, '_main', '_solib_k8')
    if not os.path.isdir(solib_dir):
        return

    ld_path = os.environ.get('LD_LIBRARY_PATH', '')
    if solib_dir in ld_path:
        return  # Already set, no need to re-exec.

    # Update LD_LIBRARY_PATH and re-exec to ensure glibc sees it at startup.
    os.environ['LD_LIBRARY_PATH'] = solib_dir + (':' + ld_path if ld_path else '')
    os.execv(sys.executable, [sys.executable] + sys.argv)


if __name__ == "__main__":
    _ensure_solib_in_ld_library_path()

    import pytest
    sys.exit(pytest.main(sys.argv[1:]))