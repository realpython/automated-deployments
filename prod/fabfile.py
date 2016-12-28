# prod/fabfile.py


import os
from fabric.contrib.files import sed
from fabric.api import env, local, run
from fabric.api import env

# initialize the base directory
abs_dir_path = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))


# declare environment global variables

# root user
env.user = 'root'

# list of remote IP addresses
env.hosts = ['104.236.66.172']

# password for the remote server
env.password = 'herman1234'

# full name of the user
env.full_name_user = 'Michael Herman'

# user group
env.user_group = 'deployers'

# user for the above group
env.user_name = 'deployer'

# ssh key path
env.ssh_keys_dir = os.path.join(abs_dir_path, 'ssh-keys')


def start_provision():
    """
    Start server provisioning
    """
    # Create a new directory for a new remote server
    env.ssh_keys_name = os.path.join(
        env.ssh_keys_dir, env.host_string + '_prod_key')
    local('ssh-keygen -t rsa -b 2048 -f {0}'.format(env.ssh_keys_name))
    local('cp {0} {1}/authorized_keys'.format(
        env.ssh_keys_name + '.pub', env.ssh_keys_dir))
    # Prevent root SSHing into the remote server
    sed('/etc/ssh/sshd_config', '^UsePAM yes', 'UsePAM no')
    sed('/etc/ssh/sshd_config', '^PermitRootLogin yes',
        'PermitRootLogin no')
    sed('/etc/ssh/sshd_config', '^#PasswordAuthentication yes',
        'PasswordAuthentication no')

    install_ansible_dependencies()
    create_deployer_group()
    create_deployer_user()
    upload_keys()
    set_selinux_permissive()
    run('service sshd reload')
    upgrade_server()


def create_deployer_group():
    """
    Create a user group for all project developers
    """
    run('groupadd {}'.format(env.user_group))
    run('mv /etc/sudoers /etc/sudoers-backup')
    run('(cat /etc/sudoers-backup; echo "%' +
        env.user_group + ' ALL=(ALL) ALL") > /etc/sudoers')
    run('chmod 440 /etc/sudoers')


def create_deployer_user():
    """
    Create a user for the user group
    """
    run('adduser -c "{}" -m -g {} {}'.format(
        env.full_name_user, env.user_group, env.user_name))
    run('passwd {}'.format(env.user_name))
    run('usermod -a -G {} {}'.format(env.user_group, env.user_name))
    run('mkdir /home/{}/.ssh'.format(env.user_name))
    run('chown -R {} /home/{}/.ssh'.format(env.user_name, env.user_name))
    run('chgrp -R {} /home/{}/.ssh'.format(
        env.user_group, env.user_name))


def upload_keys():
    """
    Upload the SSH public/private keys to the remote server via scp
    """
    scp_command = 'scp {} {}/authorized_keys {}@{}:~/.ssh'.format(
        env.ssh_keys_name + '.pub',
        env.ssh_keys_dir,
        env.user_name,
        env.host_string
    )
    local(scp_command)


def install_ansible_dependencies():
    """
    Install the python-dnf module so that Ansible
    can communicate with Fedora's Package Manager
    """
    run('dnf install -y python-dnf')


def set_selinux_permissive():
    """
    Set SELinux to Permissive/Disabled Mode
    """
    # for permissive
    run('sudo setenforce 0')


def upgrade_server():
    """
    Upgrade the server as a root user
    """
    run('dnf upgrade -y')
    # optional command (necessary for Fedora 25)
    run('dnf install -y python')
    run('reboot')
