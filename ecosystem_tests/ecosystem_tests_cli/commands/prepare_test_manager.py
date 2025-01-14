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
import base64
from boto3 import client
from cloudify import ctx

from ..utilities import prepare_test_env
from ...dorkl.runners import prepare_test_dev
from ...ecosystem_tests_cli import ecosystem_tests
from ..secrets import prepare_secrets_dict_for_prepare_test
from ...dorkl.constansts import (
    LICENSE_ENVAR_NAME,
    MANAGER_CONTAINER_ENVAR_NAME
)


@ecosystem_tests.command(name='prepare-test-manager',
                         short_help='Prepare test manager(licence, '
                                    'secrets, etc.)')
@prepare_test_env
@ecosystem_tests.options.license
@ecosystem_tests.options.secret
@ecosystem_tests.options.file_secret
@ecosystem_tests.options.encoded_secrets
@ecosystem_tests.options.plugin
@ecosystem_tests.options.plugins_bundle
@ecosystem_tests.options.skip_bundle_upload
@ecosystem_tests.options.container_name
@ecosystem_tests.options.yum_packages
@ecosystem_tests.options.generate_new_aws_token
@ecosystem_tests.options.timeout
def prepare_test_manager(license,
                         secret,
                         file_secret,
                         encoded_secret,
                         plugin,
                         bundle_path,
                         skip_bundle_upload,
                         container_name,
                         yum_package,
                         generate_new_aws_token,
                         timeout):
    """
    This command responsible for prepare test manager.
    """

    if LICENSE_ENVAR_NAME not in os.environ or \
            os.environ[LICENSE_ENVAR_NAME] != license:
        os.environ[LICENSE_ENVAR_NAME] = license

    if MANAGER_CONTAINER_ENVAR_NAME not in os.environ or \
            os.environ[MANAGER_CONTAINER_ENVAR_NAME] != container_name:
        os.environ[MANAGER_CONTAINER_ENVAR_NAME] = container_name

    if generate_new_aws_token:
        aws_access_key_id, aws_secret_access_key, aws_session = \
            generate_new_credentials(timeout)

        encoded_secret.update({'aws_access_key_id': aws_access_key_id})
        encoded_secret.update({'aws_secret_access_key': aws_secret_access_key})
        encoded_secret.update({'aws_session_token': aws_session})

    secrets_dict = prepare_secrets_dict_for_prepare_test(secret,
                                                         file_secret,
                                                         encoded_secret)

    prepare_test_dev(plugins=plugin,
                     secrets=secrets_dict,
                     execute_bundle_upload=not skip_bundle_upload,
                     bundle_path=bundle_path,
                     yum_packages=yum_package)


def generate_new_credentials(timeout):
    if timeout < 1200:
        timeout = 1200
        ctx.logger.info('Minimum timeout 900, setting to 900')

    if 'aws_access_key_id' in os.environ:
        os.environ['aws_access_key_id'.upper()] = str(base64.b64decode(
            os.environ['aws_access_key_id']), 'utf-8').strip('\n')
    if 'aws_secret_access_key' in os.environ:
        os.environ['aws_secret_access_key'.upper()] = str(base64.b64decode(
            os.environ['aws_secret_access_key']), 'utf-8').strip('\n')

    sts = client('sts')
    response = sts.get_session_token(DurationSeconds=timeout)

    os.environ['aws_access_key_id'] = base64.b64encode(
        response['Credentials']['AccessKeyId'].encode('utf-8')).decode()
    os.environ['aws_secret_access_key'] = base64.b64encode(
        response['Credentials']['SecretAccessKey'].encode('utf-8')).decode()
    os.environ['aws_session_token'] = base64.b64encode(
        response['Credentials']['SessionToken'].encode('utf-8')).decode()

    return \
        os.environ['aws_access_key_id'], \
        os.environ['aws_secret_access_key'], \
        os.environ['aws_session_token']
