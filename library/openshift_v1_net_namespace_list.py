#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.module_utils.openshift_common import OpenShiftAnsibleModule, OpenShiftAnsibleException

DOCUMENTATION = '''
module: openshift_v1_net_namespace_list
short_description: OpenShift NetNamespaceList
description:
- Retrieve a list of net_namespaces. List operations provide a snapshot read of the
  underlying objects, returning a resource_version representing a consistent version
  of the listed objects.
version_added: 2.3.0
author: OpenShift (@openshift)
options:
  api_key:
    description:
    - Token used to connect to the API.
  cert_file:
    description:
    - Path to a certificate used to authenticate with the API.
    type: path
  context:
    description:
    - The name of a context found in the Kubernetes config file.
  debug:
    description:
    - Enable debug output from the OpenShift helper. Logging info is written to KubeObjHelper.log
    default: false
    type: bool
  force:
    description:
    - If set to C(True), and I(state) is C(present), an existing object will updated,
      and lists will be replaced, rather than merged.
    default: false
    type: bool
  host:
    description:
    - Provide a URL for acessing the Kubernetes API.
  key_file:
    description:
    - Path to a key file used to authenticate with the API.
    type: path
  kubeconfig:
    description:
    - Path to an existing Kubernetes config file. If not provided, and no other connection
      options are provided, the openshift client will attempt to load the default
      configuration file from I(~/.kube/config.json).
    type: path
  password:
    description:
    - Provide a password for connecting to the API. Use in conjunction with I(username).
  resource_definition:
    description:
    - Provide the YAML definition for the object, bypassing any modules parameters
      intended to define object attributes.
    type: dict
  src:
    description:
    - Provide a path to a file containing the YAML definition of the object. Mutually
      exclusive with I(resource_definition).
    type: path
  ssl_ca_cert:
    description:
    - Path to a CA certificate used to authenticate with the API.
    type: path
  state:
    description:
    - Determines if an object should be created, patched, or deleted. When set to
      C(present), the object will be created, if it does not exist, or patched, if
      parameter values differ from the existing object's attributes, and deleted,
      if set to C(absent). A patch operation results in merging lists and updating
      dictionaries, with lists being merged into a unique set of values. If a list
      contains a dictionary with a I(name) or I(type) attribute, a strategic merge
      is performed, where individual elements with a matching I(name_) or I(type)
      are merged. To force the replacement of lists, set the I(force) option to C(True).
    default: present
    choices:
    - present
    - absent
  username:
    description:
    - Provide a username for connecting to the API.
  verify_ssl:
    description:
    - Whether or not to verify the API server's SSL certificates.
    type: bool
requirements:
- openshift == 0.4.0.a1
'''

EXAMPLES = '''
'''

RETURN = '''
api_version:
  description: Requested API version
  type: string
net_namespace_list:
  type: complex
  returned: when I(state) = C(present)
  contains:
    api_version:
      description:
      - APIVersion defines the versioned schema of this representation of an object.
        Servers should convert recognized schemas to the latest internal value, and
        may reject unrecognized values.
      type: str
    items:
      description:
      - Items is the list of net namespaces
      type: list
      contains:
        api_version:
          description:
          - APIVersion defines the versioned schema of this representation of an object.
            Servers should convert recognized schemas to the latest internal value,
            and may reject unrecognized values.
          type: str
        egress_i_ps:
          description:
          - EgressIPs is a list of reserved IPs that will be used as the source for
            external traffic coming from pods in this namespace. (If empty, external
            traffic will be masqueraded to Node IPs.)
          type: list
          contains: str
        kind:
          description:
          - Kind is a string value representing the REST resource this object represents.
            Servers may infer this from the endpoint the client submits requests to.
            Cannot be updated. In CamelCase.
          type: str
        metadata:
          description:
          - Standard object's metadata.
          type: complex
        netid:
          description:
          - NetID is the network identifier of the network namespace assigned to each
            overlay network packet. This can be manipulated with the "oc adm pod-network"
            commands.
          type: int
        netname:
          description:
          - NetName is the name of the network namespace. (This is the same as the
            object's name, but both fields must be set.)
          type: str
    kind:
      description:
      - Kind is a string value representing the REST resource this object represents.
        Servers may infer this from the endpoint the client submits requests to. Cannot
        be updated. In CamelCase.
      type: str
    metadata:
      description:
      - Standard object's metadata.
      type: complex
'''


def main():
    try:
        module = OpenShiftAnsibleModule('net_namespace_list', 'v1')
    except OpenShiftAnsibleException as exc:
        # The helper failed to init, so there is no module object. All we can do is raise the error.
        raise Exception(exc.message)

    try:
        module.execute_module()
    except OpenShiftAnsibleException as exc:
        module.fail_json(msg="Module failed!", error=str(exc))


if __name__ == '__main__':
    main()
