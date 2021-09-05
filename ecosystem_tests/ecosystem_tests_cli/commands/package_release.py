########
# Copyright (c) 2014-2021 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from os import path, pardir

from ecosystem_cicd_tools.release import (
    plugin_release_with_latest, find_version)
from ...ecosystem_tests_cli import ecosystem_tests

setup_py = path.join(
    path.abspath(path.join(path.dirname(__file__), pardir)),
    'setup.py')


@ecosystem_tests.command(name='package-release',
                         short_help='package release.')
@ecosystem_tests.options.directory
@ecosystem_tests.options.name
def package_release(directory, name):
    setup_py = directory + 'seyup.py'
    plugin_release_with_latest(name, find_version(setup_py))
