[![Build Status](https://travis-ci.org/ansible/ansible-kubernetes-modules.svg?branch=master)](https://travis-ci.org/ansible/ansible-kubernetes-modules)

# ansible-kubernetes-modules

Our approach to K8s modules is changing in [Ansible 2.5](http://docs.ansible.com/ansible/devel/roadmap/ROADMAP_2_5.html). The following summarizes the changes you can expect:

- We will still rely on the [OpenShift Python Client](https://github.com/openshift/openshift-restclient-python)
- Modules will no longer be generated, but will instead be part of the [Ansible project](https://github.com/ansible/ansible), and delivered with Ansible
- The shared Ansible module code, which is currently part of the `helper` found in the OpenShift Python Client, will move under `lib/ansible/module_utils` in the Ansible project. 
- A `k8s_raw` module, and an `openshift_raw` module for performing CRUD operations on objects. With a single module, you'll be able to pass an inline object config, or read an object config from the file system, and manage objects.   
- Shared code, built around the OpenShift Python Client, that makes it easy to develop new modules 

The goal is to make it easier for the Ansible community to find, adopt, and collaborate on the K8s modules. Hopefully, by removing the module generation process, the workflow for filing issues and collaborating on module development will be easier, and more clear for everyone. 

## Why use this role?

The purpose of copying the new Ansible K8s modules and plugins into this repository is to make it easier for anyone running an older release of Ansible to access and use the new modules. So, if you're running Ansible 2.5, which at the time of this writing is only available by running from source, or a version greater than 2.5, then you don't need to use this role. In that case, all the modules will be delivered when you install Ansible. However, for versions prior to 2.5, you'll want to use this role.

## What's included

- [modules](./library)
- [lookup plugin](./lookup_plugins)
- [connection plugin](./connection_plugins)
 
## How to use this role

Each module and plugin contains full documentation for parameters, any returned data structure, and examples.

If you find an issue with a particular module, or have suggestions, please file an issue at the [Ansible project](https://github.com/ansible/ansible).

## Requirements

- Ansible
- [OpenShift Rest Client](https://github.com/openshift/openshift-restclient-python) installed on the host where the modules will execute.
- If using the connection plugins, you'll need `kubectl` or `oc` installed 

## Installation and use

Use the Galaxy client to install the role. To access the new Ansible 2.5 version of the modules, you'll need to install the `ansible2.5` branch as follows:

```
$ ansible-galaxy install git+git@github.com:ansible/ansible-kubernetes-modules.git,ansible2.5
```

### Using the modules 

To use the modules, add it to a playbook like so:

```
---
- hosts: localhost
  remote_user: root
  roles:
    - role: ansible.kubernetes-modules
      install_python_requirements: no
  tasks:
    - name: Create a new project
      openshift_raw:
        state: present
        kind: Project
        description: My new project
        display_name: My Project  

    - name: Create a Service
      openshift_raw:
        state: present
        src: /my_project/service.yml
```

That's it. Just reference the role, and subsequent tasks and roles are able to call the modules.

View the `openshift_raw` and `k8s_raw` source for available parameters, and more examples.

### Using the connection plugin

Included in the role are the `kubectl` and `oc` connection plugins. To use them outside of the role, you'll need an `ansible.cfg` file similar to the following:

```
[defaults]
connection_plugins = ~/my-roles/ansible-kubernetes-modules/connection_plugins
remote_tmp = /tmp
```

Add the `connection_plugins` subdirectory found within this role to the `connections_plugins` path defined in `ansible.cfg`. This will make the connection plugin accessible externally in other playbooks and roles.

The above example also defines `remote_tmp`. Depending on the file system permissions inside the containers you're accessing, the working directory may or may not be writable. When Ansible connects to a remote host, in this case a running container, it copies module files and Ansible dependencies to the remote file system. If the workig directory is not writable, define `remote_tmp` to point to a path inside the container  that is writable. 

Here's a sample inventory showing the `ansible_connection` variable set to the `kubectl` connection plugin:

```
[pods]
galaxy-1-gp4kt

[pods:vars]
ansible_connection=kubectl
```

The `kubectl` connection plugin requires the `kubectl` binary installed on the Ansible control node. The plugin is a wrapper around the `kubectl exec` command. The same is true for the `oc` connection plugin, where you'll need to have the `oc` binary available on the control node. 

The plugins also support several variables for connecting to the API. View the source to see the available parameters. Parameters are passed by setting the prescribed variables in the inventory file, or by setting any associated environment variables.

## Using lookup plugins

Both `k8s` and `openshift` lookup plugins are available. They interact with the API directly, and do not rely on the CLI binaries. To use them, you'll need to add the `lookup_plugins` directory from the role to the `lookup_plugins` setting in your `ansibe.cfg` file. For example:

```
[defaults]
lookup_plugins = ~/my-roles/ansible-kubernetes-modules/lookup_plugins
```

Here's an example playbook that use the `openshift` lookup plugin to discover a project:

```
- name: Test roles
  hosts: localhost 
  connection: local
  gather_facts: no

  tasks:

  - set_fact:
      project: "{{ lookup('openshift', kind='Project', resource_name='testing2') }}"

  - debug:
      var: project
```

View the plugin source for a full description of the available parameters for each lookup plugin..

## Role Variables

install_python_requirements
> Set to true, if you want the OpenShift Rest Client installed. Defaults to false. Will install via `pip`.

virtualenv
> Provide the name of a virtualenv to use when installing `pip` packages.

## License

Apache V2
