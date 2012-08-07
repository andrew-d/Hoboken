import os
import re
import platform

from fabric.api import *
from fabric.colors import red, yellow, green

env.hoboken_init = os.path.join('hoboken', '__init__.py')
env.version_regex = r'((?:\d+)\.(?:\d+)\.(?:\d+))'

version_re = re.compile(env.version_regex)


def split_version(ver_str):
    return [int(x) for x in ver_str.split('.')]


def join_version(split_ver):
    return '.'.join(str(x) for x in split_ver)


def read_version():
    with open(env.hoboken_init, 'rb') as f:
        file_data = f.read().replace('\r\n', '\n')

    m = version_re.search(file_data)
    if m is None:
        abort(red("Could not find version in '{0}'!".format(env.hoboken_init)))

    return m.group(0)


def write_version(v):
    with open(env.hoboken_init, 'rb') as f:
        file_data = f.read().replace('\r\n', '\n')

    m = version_re.search(file_data)
    if m is None:
        abort(red("Could not find version in '{0}'!".format(env.hoboken_init)))

    before = file_data[0:m.start(0)]
    after  = file_data[m.end(0):]

    new_data = before + v + after

    with open(env.hoboken_init, 'wb') as f:
        f.write(new_data)


def increment_version(version_index):
    curr_ver = read_version()
    spl = split_version(curr_ver)
    spl[version_index] += 1

    # When we increment a version, we set the numbers 'below' it to 0.
    for x in range(version_index + 1, len(spl)):
        spl[x] = 0
    new_ver = join_version(spl)

    puts("Bumping from " + green(curr_ver) + " to " + green(new_ver))
    write_version(new_ver)


def get_current_tag():
    with hide('running'):
        res = local('git tag')
    return res.strip()

@task
def get_version():
    """Get the current package version."""
    puts("The current version is: " + green(read_version()))

@task
def incr_patch_ver():
    """Increment the patch version (i.e. Z in X.Y.Z)."""
    increment_version(2)

@task
def incr_minor_ver():
    """Increment the minor version (i.e. Y in X.Y.Z)."""
    increment_version(1)

@task
def incr_major_ver():
    """Increment the major version (i.e. X in X.Y.Z)."""
    increment_version(0)

@task
def set_version(new_version):
    """Set the version to something new."""
    puts("Setting version to: " + green(new_version))
    write_version(new_version)

@task
def commit_and_tag_version():
    """Add, commit and tag the current package version."""
    curr_ver = read_version()
    curr_tag = get_current_tag()
    if curr_ver != curr_tag:
        local('git add {0}'.format(env.hoboken_init))
        local('git commit -m "Set package version to {0}"'.format(curr_ver))
        local('git tag {0}'.format(curr_ver))
    else:
        puts("Already at tag: {0}".format(curr_tag))

@task
def get_tagged_version():
    """Get the current tagged version."""
    tag = get_current_tag()
    if tag == '':
        puts(yellow("No tagged version!"))
    else:
        puts("Most recent tagged version is: " + green(tag))

@task
def test():
    """Run tests on the package.  Will abort() if they fail."""
    with settings(
        hide('warnings', 'running'),
        warn_only=True
    ):
        results = local('tox')

    if results.failed:
        # lines = results.stderr.replace("\r\n", "\n").split("\n")

        # puts(red(lines[-1]))
        abort(red("The tests failed!"))
    else:
        puts(green("Tests succeeded"))

@task
def upload_to_pypi():
    """Upload the package to PyPI."""
    local('python setup.py sdist upload')

@task
def upload_all():
    """Push changes to GitHub and upload to PyPI."""
    local('git push')
    execute(upload_to_pypi)

@task
def deploy():
    """Test, and if they pass, commit/tag/push/upload the package."""
    execute(test)
    execute(commit_and_tag_version)
    execute(upload_all)

