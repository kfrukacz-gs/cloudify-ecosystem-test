########
# Copyright (c) 2014-2022 Cloudify Platform Ltd. All rights reserved
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

import os

from testtools import TestCase

from ...ecosystem_tests_cli import utilities
from ..exceptions import EcosystemTestCliException


class UtilitiesTest(TestCase):

    def setUp(self):
        super(UtilitiesTest, self).setUp()
        self.blueprints = ['/fake/path/one', '/fake/path/two']
        self.test_id = 'test'

    def test_validate_and_generate_test_ids_success(self):
        result = utilities.validate_and_generate_test_ids(
            blueprint_path=self.blueprints, test_id=None)
        self.assertEqual(len(result), len(self.blueprints))
        self.assertEqual(result[0][0], self.blueprints[0])
        self.assertEqual(len(result[0][1]), 11)
        self.assertEqual(result[1][0], self.blueprints[1])

    def test_validate_and_generate_test_ids_multiple_bps_one_test_id(self):
        with self.assertRaisesRegexp(EcosystemTestCliException,
                                     'Please do not provide test-id with '
                                     'multiple blueprints to test.'):
            utilities.validate_and_generate_test_ids(self.blueprints,
                                                     self.test_id)
