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

import sys
import pytest

# The rosidl_generator_py sitecustomize.py installs an InterceptingFinder
# that remaps PEP 420 namespace package imports (e.g., `from std_msgs.msg
# import String` → `from std_msgs.msg._string import String`). Python only
# auto-loads sitecustomize.py from sys.path during site.py initialization,
# but rules_python's bootstrap adds import paths after that point. We must
# explicitly import it to ensure the meta path hook is installed.
try:
    import sitecustomize  # noqa: F401
except:
    pass

if __name__ == "__main__":
    sys.exit(pytest.main(sys.argv[1:]))