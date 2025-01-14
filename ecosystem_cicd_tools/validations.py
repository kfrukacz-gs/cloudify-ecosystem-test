import os
import sys
import logging
import subprocess
from re import match, compile
from yaml import safe_load
from yaml.parser import ParserError
from ecosystem_cicd_tools.github_stuff import get_client

try:
    from packaging.version import parse as parse_version
except ImportError:
    from distutils.version import LooseVersion as parse_version

from .github_stuff import (
    raise_if_unmergeable,
    get_pull_request_jira_ids,
    get_repository,
    get_pull_requests,
    find_pull_request_numbers,
    check_if_label_in_pr_labels)

VERSION_EXAMPLE = """
version_file = open(os.path.join(package_root_dir, 'VERSION'))
version = version_file.read().strip()"""

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def does_protected_branch_have_build_source(pull_request):
    string_pattern = '[0-9.]*-build'
    pattern = compile(string_pattern)
    if pull_request.base.ref in ['main', 'master'] \
        and not pattern.match(pull_request.title):
        logging.error(
            'Protected branches "main" and "master" require build branch. '
            'Branch name is {}'.format(pull_request.title))
        sys.exit(1)


def validate_pulls(repo_name, branch_name):
    client = get_client()
    repo = client.get_repo(repo_name)
    pulls = repo.get_pulls()
    for pull in pulls:
        if pull.head.ref == branch_name:
            does_protected_branch_have_build_source(pull)


def get_plugin_version(file_path=None):
    """

    :param file_path: Should be something like `cloudify-aws-plugin/VERSION`.
    :return: version
    """
    file_path = file_path or os.path.join(
        os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                os.pardir
            )
        ),
        'VERSION')
    if not os.path.exists(file_path):
        logging.error(
            'Plugins must store version in a VERSION file in your plugin. '
            'That file should be read into setup.py like this: ' +
            VERSION_EXAMPLE)
        raise Exception('Invalid plugin version storage.')
    with open(file_path) as infile:
        version = infile.read().strip()
        if not bool(match('([\d.]+)[\d$]', version)):
            raise Exception(
                'Version {version} is not a legal version.'.format(
                    version=version))


def read_yaml_file(file_path):
    with open(file_path, 'r') as stream:
        try:
            return safe_load(stream)
        except ParserError:
            logging.error('{path} is not in YAML format.'.format(
                path=file_path))
            raise


def check_changelog_version(version, file_path):
    logging.info('Version {version} is in CHANGELOG.'.format(version=version))
    if not check_is_latest_version(version, file_path):
        raise Exception('Version {version} not in {path}.'.format(
            version=version, path=file_path))


def check_is_latest_version(version, file_path):
    dict_file = read_yaml_file(file_path)
    list_of_versions = []
    for i in dict_file:
        list_of_versions.append(str(i))

    sorted_l = sorted(list_of_versions, key=parse_version)
    return version == sorted_l.pop()


def check_setuppy_version(version, plugin_directory):
    command = '{exec_path} {path} --version'.format(
        exec_path=sys.executable,
        path=os.path.join(plugin_directory, 'setup.py'))
    output = subprocess.check_output(command, shell=True)
    output = output.decode("utf-8")
    if version.strip() != output.strip():
        raise Exception('Plugin YAML {version} does not match '
                        'setup.py {output}.'.format(version=version.strip(),
                                                    output=output.strip()))
    logging.info('Version {version} matches {output}.'.format(
        version=version, output=output))


def read_plugins(file_path):
    plugin_yaml = read_yaml_file(file_path)
    return plugin_yaml['plugins']


def get_plugin_yaml_version(file_path):
    """

    :param file_path:
    :return:
    """

    logging.debug(
        'Checking plugin YAML version with {file_path}'.format(
            file_path=file_path))

    plugins_section = read_plugins(file_path)

    package_version = None
    for _, v in plugins_section.items():

        if package_version and v['package_version'] != package_version:
            raise Exception('More than one plugin version is defined.')

        package_version = v['package_version']
        package_source = v.get('source')

        logging.debug('Package version {package_version}'.format(
            package_version=package_version))
        logging.debug('Package source {package_source}'.format(
            package_source=package_source))

        if not package_version:
            raise Exception('Version not specified in plugin YAML.')

        if package_source and package_version not in package_source:
            raise Exception('Version {version} '
                            'does not match {package_source}.'.format(
                                version=package_version,
                                package_source=package_source))
    return package_version


def validate_plugin_version(plugin_directory=None,
                            plugin_yaml='plugin.yaml',
                            changelog='CHANGELOG.txt'):
    """
    Validate plugin version.

    :param plugin_directory: The script should send the absolute path.
    :param plugin_yaml: The name of the plugin YAML file.
    :param changelog: The name of the CHANGELOG.txt.
    :return:
    """

    plugin_directory = plugin_directory or os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
    version = get_plugin_yaml_version(
        os.path.join(plugin_directory, plugin_yaml))
    check_changelog_version(version, os.path.join(plugin_directory, changelog))
    check_setuppy_version(version, plugin_directory)
    return version


def _validate_documenation_pulls(docs_repo, jira_ids):
    merges = 0
    pulls = docs_repo.get_pulls(state='open')
    logging.info('validate documentation pulls jira_ids = {}'.format(jira_ids))
    for jira_id in jira_ids:
        for pull in pulls:
            if jira_id in pull.head.label:
                raise_if_unmergeable(pull)
                merges += 1
    if not merges:
        raise Exception(
            'No documentation PRs were found in {}. '
            'If your PR includes the label "enhancement", '
            'then you are expected to submit docs PRs. '.format(
                docs_repo.name))


def validate_documentation_pulls(repo=None, docs_repo=None, branch=None):
    """
    Check that we are providing documentation.
    :param repo: The current repo (a plugin for example).
    :param docs_repo: The repo to check for Docs PRs.
    :param branch: The current branch. 
    :return:
    """

    logging.info('Validating documentation pull requests are ready.')
    repo = repo or get_repository()
    docs_repo = docs_repo or get_repository(
        org='cloudify-cosmo', repo_name='docs.getcloudify.org')

    branch = branch or os.environ.get('CIRCLE_BRANCH')
    logging.info('Checking pull requests for {branch}'.format(branch=branch))

    pr_numbers = find_pull_request_numbers(branch, repo)
    if not pr_numbers and branch not in ['master', 'main', '2.X-master']:
        logging.info('A PR has not yet been opened.')
        return
    logging.info('Found these PR numbers: {}'.format(pr_numbers))

    pull_requests = get_pull_requests(pr_numbers)
    logging.info('Found these PRs: {}'.format(pull_requests))
    jira_ids = get_pull_request_jira_ids(pulls=pull_requests)

    if not check_if_label_in_pr_labels(pr_numbers):
        return
    _validate_documenation_pulls(docs_repo, jira_ids)
