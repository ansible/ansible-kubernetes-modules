#
#  Copyright 2018 Red Hat | Ansible
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

DOCUMENTATION = """
    lookup: k8s

    version_added: "2.5"

    short_description: Query the K8s API

    description:
      - Uses the OpenShift Python client to fetch a specific object by name, all matching objects within a
        namespace, or all matching objects for all namespaces.
      - Provides access the full range of K8s APIs.
      - Enables authentication via config file, certificates, password or token.

    options:
      api_version:
        description:
        - Use to specify the API version. If I(resource definition) is provided, the I(apiVersion) from the
          I(resource_definition) will override this option.
        default: v1
      kind:
        description:
        - Use to specify an object model. If I(resource definition) is provided, the I(kind) from a
          I(resource_definition) will override this option.
        required: true
      resource_name:
        description:
        - Fetch a specific object by name. If I(resource definition) is provided, the I(metadata.name) value
          from the I(resource_definition) will override this option.
      namespace:
        description:
        - Limit the objects returned to a specific namespace. If I(resource definition) is provided, the
          I(metadata.namespace) value from the I(resource_definition) will override this option.
      label_selector:
        description:
        - Additional labels to include in the query. Ignored when I(resource_name) is provided.
      field_selector:
        description:
        - Specific fields on which to query. Ignored when I(resource_name) is provided.
      resource_definition:
        description:
        - "Provide a YAML configuration for an object. NOTE: I(kind), I(api_version), I(resource_name),
          and I(namespace) will be overwritten by corresponding values found in the provided I(resource_definition)."
      src:
        description:
        - "Provide a path to a file containing a valid YAML definition of an object dated. Mutually
          exclusive with I(resource_definition). NOTE: I(kind), I(api_version), I(resource_name), and I(namespace)
          will be overwritten by corresponding values found in the configuration read in from the I(src) file."
        - Reads from the local file system. To read from the Ansible controller's file system, use the file lookup
          plugin or template lookup plugin, combined with the from_yaml filter, and pass the result to
          I(resource_definition). See Examples below.
      host:
        description:
        - Provide a URL for accessing the API. Can also be specified via K8S_AUTH_HOST environment variable.
      api_key:
        description:
        - Token used to authenticate with the API. Can also be specified via K8S_AUTH_API_KEY environment variable.
      kubeconfig:
        description:
        - Path to an existing Kubernetes config file. If not provided, and no other connection
          options are provided, the openshift client will attempt to load the default
          configuration file from I(~/.kube/config.json). Can also be specified via K8S_AUTH_KUBECONFIG environment
          variable.
      context:
        description:
        - The name of a context found in the config file. Can also be specified via K8S_AUTH_CONTEXT environment
          variable.
      username:
        description:
        - Provide a username for authenticating with the API. Can also be specified via K8S_AUTH_USERNAME environment
          variable.
      password:
        description:
        - Provide a password for authenticating with the API. Can also be specified via K8S_AUTH_PASSWORD environment
          variable.
      cert_file:
        description:
        - Path to a certificate used to authenticate with the API. Can also be specified via K8S_AUTH_CERT_FILE
          environment
          variable.
      key_file:
        description:
        - Path to a key file used to authenticate with the API. Can also be specified via K8S_AUTH_HOST environment
          variable.
      ssl_ca_cert:
        description:
        - Path to a CA certificate used to authenticate with the API. Can also be specified via K8S_AUTH_SSL_CA_CERT
          environment variable.
      verify_ssl:
        description:
        - Whether or not to verify the API server's SSL certificates. Can also be specified via K8S_AUTH_VERIFY_SSL
          environment variable.
        type: bool

    requirements:
      - "python >= 2.7"
      - "openshift >= 0.3"
      - "PyYAML >= 3.11"

    notes:
      - "The OpenShift Python client wraps the K8s Python client, providing full access to
        all of the APIS and models available on both platforms. For API version details and
        additional information visit https://github.com/openshift/openshift-restclient-python"
"""

EXAMPLES = """
- name: Fetch a list of namespaces
  set_fact:
    projects: "{{ lookup('k8s', api_version='v1', kind='Namespace') }}"

- name: Fetch all deployments
  set_fact:
    deployments: "{{ lookup('k8s', kind='Deployment', namespace='testing') }}"

- name: Fetch all deployments in a namespace
  set_fact:
    deployments: "{{ lookup('k8s', kind='Deployment', namespace='testing') }}"

- name: Fetch a specific deployment by name
  set_fact:
    deployments: "{{ lookup('k8s', kind='Deployment', namespace='testing', resource_name='elastic') }}"

- name: Fetch with label selector
  set_fact:
    service: "{{ lookup('k8s', kind='Service', label_selector='app=galaxy') }}"

# Use parameters from a YAML config

- name: Load config from the Ansible controller filesystem
  set_fact:
    config: "{{ lookup('file', 'service.yml') | from_yaml }}"

- name: Using the config (loaded from a file in prior task), fetch the latest version of the object
  set_fact:
    service: "{{ lookup('k8s', resource_definition=config) }}"

- name: Use a config from the local filesystem
  set_fact:
    service: "{{ lookup('k8s', src='service.yml') }}"
"""

RETURN = """
  _list:
    description:
      - One ore more object definitions returned from the API.
    type: complex
    contains:
      api_version:
        description: The versioned schema of this representation of an object.
        returned: success
        type: str
      kind:
        description: Represents the REST resource this object represents.
        returned: success
        type: str
      metadata:
        description: Standard object metadata. Includes name, namespace, annotations, labels, etc.
        returned: success
        type: complex
      spec:
        description: Specific attributes of the object. Will vary based on the I(api_version) and I(kind).
        returned: success
        type: complex
      status:
        description: Current status details for the object.
        returned: success
        type: complex
"""

from ansible.plugins.lookup import LookupBase

import json
import os
import re
import base64
import copy
import re

from ansible.module_utils.six import iteritems, string_types
from ansible.module_utils.basic import AnsibleModule

from datetime import datetime
from keyword import kwlist

try:
    from openshift.helper import PRIMITIVES
    from openshift.helper.exceptions import KubernetesException
    from openshift.helper.kubernetes import KubernetesObjectHelper
    from openshift.helper.openshift import OpenShiftObjectHelper
    HAS_K8S_MODULE_HELPER = True
except ImportError as exc:
    class KubernetesObjectHelper(object):
        pass

    class OpenShiftObjectHelper(object):
        pass

    HAS_K8S_MODULE_HELPER = False

# TODO Remove string_utils dependency
try:
    import string_utils
    HAS_STRING_UTILS = True
except ImportError:
    HAS_STRING_UTILS = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

ARG_ATTRIBUTES_BLACKLIST = ('property_path',)
PYTHON_KEYWORD_MAPPING = dict(zip(['_{0}'.format(item) for item in kwlist], kwlist))
PYTHON_KEYWORD_MAPPING.update(dict([reversed(item) for item in iteritems(PYTHON_KEYWORD_MAPPING)]))

COMMON_ARG_SPEC = {
    'state': {
        'default': 'present',
        'choices': ['present', 'absent'],
    },
    'force': {
        'type': 'bool',
        'default': False,
    },
    'resource_definition': {
        'type': 'dict',
        'aliases': ['definition', 'inline']
    },
    'src': {
        'type': 'path',
    },
    'kind': {},
    'name': {},
    'namespace': {},
    'api_version': {
        'default': 'v1',
        'aliases': ['api', 'version'],
    },
}

AUTH_ARG_SPEC = {
    'kubeconfig': {
        'type': 'path',
    },
    'context': {},
    'host': {},
    'api_key': {
        'no_log': True,
    },
    'username': {},
    'password': {
        'no_log': True,
    },
    'verify_ssl': {
        'type': 'bool',
    },
    'ssl_ca_cert': {
        'type': 'path',
    },
    'cert_file': {
        'type': 'path',
    },
    'key_file': {
        'type': 'path',
    },
}

OPENSHIFT_ARG_SPEC = {
    'description': {},
    'display_name': {},
}


class AnsibleMixin(object):
    _argspec_cache = None

    @property
    def argspec(self):
        """
        Introspect the model properties, and return an Ansible module arg_spec dict.
        :return: dict
        """
        if self._argspec_cache:
            return self._argspec_cache
        argument_spec = copy.deepcopy(COMMON_ARG_SPEC)
        argument_spec.update(copy.deepcopy(AUTH_ARG_SPEC))
        argument_spec.update(copy.deepcopy(OPENSHIFT_ARG_SPEC))
        argument_spec.update(self.__transform_properties(self.properties))
        self._argspec_cache = argument_spec
        return self._argspec_cache

    def object_from_params(self, module_params, obj=None):
        """
        Update a model object with Ansible module param values. Optionally pass an object
        to update, otherwise a new object will be created.
        :param module_params: dict of key:value pairs
        :param obj: model object to update
        :return: updated model object
        """
        if not obj:
            obj = self.model()
            obj.kind = string_utils.snake_case_to_camel(self.kind, upper_case_first=False)
            obj.api_version = self.api_version.lower()
        for param_name, param_value in iteritems(module_params):
            spec = self.find_arg_spec(param_name)
            if param_value is not None and spec.get('property_path'):
                prop_path = copy.copy(spec['property_path'])
                self.__set_obj_attribute(obj, prop_path, param_value, param_name)

        if self.kind.lower() == 'project' and (module_params.get('display_name') or
                                               module_params.get('description')):
            if not obj.metadata.annotations:
                obj.metadata.annotations = {}
            if module_params.get('display_name'):
                obj.metadata.annotations['openshift.io/display-name'] = module_params['display_name']
            if module_params.get('description'):
                obj.metadata.annotations['openshift.io/description'] = module_params['description']
        elif (self.kind.lower() == 'secret' and getattr(obj, 'string_data', None)
                and hasattr(obj, 'data')):
            if obj.data is None:
                obj.data = {}

            # Do a base64 conversion of `string_data` and place it in
            # `data` so that later comparisons to existing objects
            # (if any) do not result in requiring an unnecessary change.
            for key, value in iteritems(obj.string_data):
                obj.data[key] = base64.b64encode(value)

            obj.string_data = None
        return obj

    def request_body_from_params(self, module_params):
        request = {
            'kind': self.base_model_name,
        }
        for param_name, param_value in iteritems(module_params):
            spec = self.find_arg_spec(param_name)
            if spec and spec.get('property_path') and param_value is not None:
                self.__add_path_to_dict(request, param_name, param_value, spec['property_path'])

        if self.kind.lower() == 'project' and (module_params.get('display_name') or
                                               module_params.get('description')):
            if not request.get('metadata'):
                request['metadata'] = {}
            if not request['metadata'].get('annotations'):
                request['metadata']['annotations'] = {}
            if module_params.get('display_name'):
                request['metadata']['annotations']['openshift.io/display-name'] = module_params['display_name']
            if module_params.get('description'):
                request['metadata']['annotations']['openshift.io/description'] = module_params['description']
        return request

    def find_arg_spec(self, module_param_name):
        """For testing, allow the param_name value to be an alias"""
        if module_param_name in self.argspec:
            return self.argspec[module_param_name]
        result = None
        for key, value in iteritems(self.argspec):
            if value.get('aliases'):
                for alias in value['aliases']:
                    if alias == module_param_name:
                        result = self.argspec[key]
                        break
                if result:
                    break
        if not result:
            raise KubernetesException(
                "Error: received unrecognized module parameter {0}".format(module_param_name)
            )
        return result

    @staticmethod
    def __convert_params_to_choices(properties):
        def snake_case(name):
            result = string_utils.snake_case_to_camel(name.replace('_params', ''), upper_case_first=True)
            return result[:1].upper() + result[1:]
        choices = {}
        for x in list(properties.keys()):
            if x.endswith('params'):
                choices[x] = snake_case(x)
        return choices

    def __add_path_to_dict(self, request_dict, param_name, param_value, path):
        local_path = copy.copy(path)
        spec = self.find_arg_spec(param_name)
        while len(local_path):
            p = string_utils.snake_case_to_camel(local_path.pop(0), upper_case_first=False)
            if len(local_path):
                if request_dict.get(p, None) is None:
                    request_dict[p] = {}
                self.__add_path_to_dict(request_dict[p], param_name, param_value, local_path)
                break
            else:
                param_type = spec.get('type', 'str')
                if param_type == 'dict':
                    request_dict[p] = self.__dict_keys_to_camel(param_name, param_value)
                elif param_type == 'list':
                    request_dict[p] = self.__list_keys_to_camel(param_name, param_value)
                else:
                    request_dict[p] = param_value

    def __dict_keys_to_camel(self, param_name, param_dict):
        result = {}
        for item, value in iteritems(param_dict):
            key_name = self.__property_name_to_camel(param_name, item)
            if value:
                if isinstance(value, list):
                    result[key_name] = self.__list_keys_to_camel(param_name, value)
                elif isinstance(value, dict):
                    result[key_name] = self.__dict_keys_to_camel(param_name, value)
                else:
                    result[key_name] = value
        return result

    @staticmethod
    def __property_name_to_camel(param_name, property_name):
        new_name = property_name
        if 'annotations' not in param_name and 'labels' not in param_name and 'selector' not in param_name:
            camel_name = string_utils.snake_case_to_camel(property_name, upper_case_first=False)
            new_name = camel_name[1:] if camel_name.startswith('_') else camel_name
        return new_name

    def __list_keys_to_camel(self, param_name, param_list):
        result = []
        if isinstance(param_list[0], dict):
            for item in param_list:
                result.append(self.__dict_keys_to_camel(param_name, item))
        else:
            result = param_list
        return result

    def __set_obj_attribute(self, obj, property_path, param_value, param_name):
        """
        Recursively set object properties
        :param obj: The object on which to set a property value.
        :param property_path: A list of property names in the form of strings.
        :param param_value: The value to set.
        :return: The original object.
        """
        while len(property_path) > 0:
            raw_prop_name = property_path.pop(0)
            prop_name = PYTHON_KEYWORD_MAPPING.get(raw_prop_name, raw_prop_name)
            prop_kind = obj.swagger_types[prop_name]
            if prop_kind in PRIMITIVES:
                try:
                    setattr(obj, prop_name, param_value)
                except ValueError as exc:
                    msg = str(exc)
                    if param_value is None and 'None' in msg:
                        pass
                    else:
                        raise KubernetesException(
                            "Error setting {0} to {1}: {2}".format(prop_name, param_value, msg)
                        )
            elif prop_kind.startswith('dict('):
                if not getattr(obj, prop_name):
                    setattr(obj, prop_name, param_value)
                else:
                    self.__compare_dict(getattr(obj, prop_name), param_value, param_name)
            elif prop_kind.startswith('list['):
                if getattr(obj, prop_name) is None:
                    setattr(obj, prop_name, [])
                obj_type = prop_kind.replace('list[', '').replace(']', '')
                if obj_type not in PRIMITIVES and obj_type not in ('list', 'dict'):
                    self.__compare_obj_list(getattr(obj, prop_name), param_value, obj_type, param_name)
                else:
                    self.__compare_list(getattr(obj, prop_name), param_value, param_name)
            else:
                # prop_kind is an object class
                sub_obj = getattr(obj, prop_name)
                if not sub_obj:
                    sub_obj = self.model_class_from_name(prop_kind)()
                setattr(obj, prop_name, self.__set_obj_attribute(sub_obj, property_path, param_value, param_name))
        return obj

    def __compare_list(self, src_values, request_values, param_name):
        """
        Compare src_values list with request_values list, and append any missing
        request_values to src_values.
        """
        if not request_values:
            return

        if not src_values:
            src_values += request_values

        if type(src_values[0]).__name__ in PRIMITIVES:
            if set(src_values) >= set(request_values):
                # src_value list includes request_value list
                return
            # append the missing elements from request value
            src_values += list(set(request_values) - set(src_values))
        elif type(src_values[0]).__name__ == 'dict':
            missing = []
            for request_dict in request_values:
                match = False
                for src_dict in src_values:
                    if '__cmp__' in dir(src_dict):
                        # python < 3
                        if src_dict >= request_dict:
                            match = True
                            break
                    elif iteritems(src_dict) == iteritems(request_dict):
                        # python >= 3
                        match = True
                        break
                if not match:
                    missing.append(request_dict)
            src_values += missing
        elif type(src_values[0]).__name__ == 'list':
            missing = []
            for request_list in request_values:
                match = False
                for src_list in src_values:
                    if set(request_list) >= set(src_list):
                        match = True
                        break
                if not match:
                    missing.append(request_list)
            src_values += missing
        else:
            raise KubernetesException(
                "Evaluating {0}: encountered unimplemented type {1} in "
                "__compare_list()".format(param_name, type(src_values[0]).__name__)
            )

    def __compare_dict(self, src_value, request_value, param_name):
        """
        Compare src_value dict with request_value dict, and update src_value with any differences.
        Does not remove items from src_value dict.
        """
        if not request_value:
            return
        for item, value in iteritems(request_value):
            if type(value).__name__ in ('str', 'int', 'bool'):
                src_value[item] = value
            elif type(value).__name__ == 'list':
                self.__compare_list(src_value[item], value, param_name)
            elif type(value).__name__ == 'dict':
                self.__compare_dict(src_value[item], value, param_name)
            else:
                raise KubernetesException(
                    "Evaluating {0}: encountered unimplemented type {1} in "
                    "__compare_dict()".format(param_name, type(value).__name__)
                )

    def __compare_obj_list(self, src_value, request_value, obj_class, param_name):
        """
        Compare a src_value (list of ojects) with a request_value (list of dicts), and update
        src_value with differences. Assumes each object and each dict has a 'name' attributes,
        which can be used for matching. Elements are not removed from the src_value list.
        """
        if not request_value:
            return

        sample_obj = self.model_class_from_name(obj_class)()

        # Try to determine the unique key for the array
        key_names = [
            'name',
            'type'
        ]
        key_name = None
        for key in key_names:
            if hasattr(sample_obj, key):
                key_name = key
                break

        if key_name:
            # If the key doesn't exist in the request values, then ignore it, rather than throwing an error
            for item in request_value:
                if not item.get(key_name):
                    key_name = None
                    break

        if key_name:
            # compare by key field
            for item in request_value:
                if not item.get(key_name):
                    # Prevent user from creating something that will be impossible to patch or update later
                    raise KubernetesException(
                        "Evaluating {0} - expecting parameter {1} to contain a `{2}` attribute "
                        "in __compare_obj_list().".format(param_name,
                                                          self.get_base_model_name_snake(obj_class),
                                                          key_name)
                    )
                found = False
                for obj in src_value:
                    if not obj:
                        continue
                    if getattr(obj, key_name) == item[key_name]:
                        # Assuming both the src_value and the request value include a name property
                        found = True
                        for key, value in iteritems(item):
                            snake_key = self.attribute_to_snake(key)
                            item_kind = sample_obj.swagger_types.get(snake_key)
                            if item_kind and item_kind in PRIMITIVES or type(value).__name__ in PRIMITIVES:
                                setattr(obj, snake_key, value)
                            elif item_kind and item_kind.startswith('list['):
                                obj_type = item_kind.replace('list[', '').replace(']', '')
                                if getattr(obj, snake_key) is None:
                                    setattr(obj, snake_key, [])
                                if obj_type not in ('str', 'int', 'bool'):
                                    self.__compare_obj_list(getattr(obj, snake_key), value, obj_type, param_name)
                                else:
                                    # Straight list comparison
                                    self.__compare_list(getattr(obj, snake_key), value, param_name)
                            elif item_kind and item_kind.startswith('dict('):
                                self.__compare_dict(getattr(obj, snake_key), value, param_name)
                            elif item_kind and type(value).__name__ == 'dict':
                                # object
                                param_obj = getattr(obj, snake_key)
                                if not param_obj:
                                    setattr(obj, snake_key, self.model_class_from_name(item_kind)())
                                    param_obj = getattr(obj, snake_key)
                                self.__update_object_properties(param_obj, value)
                            else:
                                if item_kind:
                                    raise KubernetesException(
                                        "Evaluating {0}: encountered unimplemented type {1} in "
                                        "__compare_obj_list() for model {2}".format(
                                            param_name,
                                            item_kind,
                                            self.get_base_model_name_snake(obj_class))
                                    )
                                else:
                                    raise KubernetesException(
                                        "Evaluating {0}: unable to get swagger_type for {1} in "
                                        "__compare_obj_list() for item {2} in model {3}".format(
                                            param_name,
                                            snake_key,
                                            str(item),
                                            self.get_base_model_name_snake(obj_class))
                                    )
                if not found:
                    # Requested item not found. Adding.
                    obj = self.__update_object_properties(self.model_class_from_name(obj_class)(), item)
                    src_value.append(obj)
        else:
            # There isn't a key, or we don't know what it is, so check for all properties to match
            for item in request_value:
                found = False
                for obj in src_value:
                    match = True
                    for item_key, item_value in iteritems(item):
                        # TODO: this should probably take the property type into account
                        snake_key = self.attribute_to_snake(item_key)
                        if getattr(obj, snake_key) != item_value:
                            match = False
                            break
                    if match:
                        found = True
                        break
                if not found:
                    obj = self.__update_object_properties(self.model_class_from_name(obj_class)(), item)
                    src_value.append(obj)

    def __update_object_properties(self, obj, item):
        """ Recursively update an object's properties. Returns a pointer to the object. """

        for key, value in iteritems(item):
            snake_key = self.attribute_to_snake(key)
            try:
                kind = obj.swagger_types[snake_key]
            except (AttributeError, KeyError):
                possible_matches = ', '.join(list(obj.swagger_types.keys()))
                class_snake_name = self.get_base_model_name_snake(type(obj).__name__)
                raise KubernetesException(
                    "Unable to find '{0}' in {1}. Valid property names include: {2}".format(snake_key,
                                                                                            class_snake_name,
                                                                                            possible_matches)
                )
            if kind in PRIMITIVES or kind.startswith('list[') or kind.startswith('dict('):
                self.__set_obj_attribute(obj, [snake_key], value, snake_key)
            else:
                # kind is an object, hopefully
                if not getattr(obj, snake_key):
                    setattr(obj, snake_key, self.model_class_from_name(kind)())
                self.__update_object_properties(getattr(obj, snake_key), value)

        return obj

    def __transform_properties(self, properties, prefix='', path=None, alternate_prefix=''):
        """
        Convert a list of properties to an argument_spec dictionary

        :param properties: List of properties from self.properties_from_model_obj()
        :param prefix: String to prefix to argument names.
        :param path: List of property names providing the recursive path through the model to the property
        :param alternate_prefix: a more minimal version of prefix
        :return: dict
        """
        primitive_types = list(PRIMITIVES) + ['list', 'dict']
        args = {}

        if path is None:
            path = []

        def add_meta(prop_name, prop_prefix, prop_alt_prefix):
            """ Adds metadata properties to the argspec """
            # if prop_alt_prefix != prop_prefix:
            #     if prop_alt_prefix:
            #         args[prop_prefix + prop_name]['aliases'] = [prop_alt_prefix + prop_name]
            #     elif prop_prefix:
            #         args[prop_prefix + prop_name]['aliases'] = [prop_name]
            prop_paths = copy.copy(path)  # copy path from outer scope
            prop_paths.append('metadata')
            prop_paths.append(prop_name)
            args[prop_prefix + prop_name]['property_path'] = prop_paths

        for raw_prop, prop_attributes in iteritems(properties):
            prop = PYTHON_KEYWORD_MAPPING.get(raw_prop, raw_prop)
            if prop in ('api_version', 'status', 'kind', 'items') and not prefix:
                # Don't expose these properties
                continue
            elif prop_attributes['immutable']:
                # Property cannot be set by the user
                continue
            elif prop == 'metadata' and prop_attributes['class'].__name__ == 'UnversionedListMeta':
                args['namespace'] = {}
            elif prop == 'metadata' and prop_attributes['class'].__name__ != 'UnversionedListMeta':
                meta_prefix = prefix + '_metadata_' if prefix else ''
                meta_alt_prefix = alternate_prefix + '_metadata_' if alternate_prefix else ''
                if meta_prefix and not meta_alt_prefix:
                    meta_alt_prefix = meta_prefix
                if 'labels' in dir(prop_attributes['class']):
                    args[meta_prefix + 'labels'] = {
                        'type': 'dict',
                    }
                    add_meta('labels', meta_prefix, meta_alt_prefix)
                if 'annotations' in dir(prop_attributes['class']):
                    args[meta_prefix + 'annotations'] = {
                        'type': 'dict',
                    }
                    add_meta('annotations', meta_prefix, meta_alt_prefix)
                if 'namespace' in dir(prop_attributes['class']):
                    args[meta_prefix + 'namespace'] = {}
                    add_meta('namespace', meta_prefix, meta_alt_prefix)
                if 'name' in dir(prop_attributes['class']):
                    args[meta_prefix + 'name'] = {}
                    add_meta('name', meta_prefix, meta_alt_prefix)
            elif prop_attributes['class'].__name__ not in primitive_types and not prop.endswith('params'):
                # Adds nested properties recursively

                label = prop

                # Provide a more human-friendly version of the prefix
                alternate_label = label\
                    .replace('spec', '')\
                    .replace('template', '')\
                    .replace('config', '')

                p = prefix
                p += '_' + label if p else label
                a = alternate_prefix
                paths = copy.copy(path)
                paths.append(prop)

                # if alternate_prefix:
                #     # Prevent the last prefix from repeating. In other words, avoid things like 'pod_pod'
                #     pieces = alternate_prefix.split('_')
                #     alternate_label = alternate_label.replace(pieces[len(pieces) - 1] + '_', '', 1)
                # if alternate_label != self.base_model_name and alternate_label not in a:
                #     a += '_' + alternate_label if a else alternate_label
                if prop.endswith('params') and 'type' in properties:
                    sub_props = dict()
                    sub_props[prop] = {
                        'class': dict,
                        'immutable': False
                    }
                    args.update(self.__transform_properties(sub_props, prefix=p, path=paths, alternate_prefix=a))
                else:
                    sub_props = self.properties_from_model_obj(prop_attributes['class']())
                    args.update(self.__transform_properties(sub_props, prefix=p, path=paths, alternate_prefix=a))
            else:
                # Adds a primitive property
                arg_prefix = prefix + '_' if prefix else ''
                arg_alt_prefix = alternate_prefix + '_' if alternate_prefix else ''
                paths = copy.copy(path)
                paths.append(prop)

                property_type = prop_attributes['class'].__name__
                if property_type == 'IntstrIntOrString':
                    property_type = 'str'

                args[arg_prefix + prop] = {
                    'required': False,
                    'type': property_type,
                    'property_path': paths
                }

                if prop.endswith('params') and 'type' in properties:
                    args[arg_prefix + prop]['type'] = 'dict'

                # Use the alternate prefix to construct a human-friendly alias
                if arg_alt_prefix and arg_prefix != arg_alt_prefix:
                    args[arg_prefix + prop]['aliases'] = [arg_alt_prefix + prop]
                elif arg_prefix:
                    args[arg_prefix + prop]['aliases'] = [prop]

                if prop == 'type':
                    choices = self.__convert_params_to_choices(properties)
                    if len(choices) > 0:
                        args[arg_prefix + prop]['choices'] = choices
        return args

def remove_secret_data(obj_dict):
    """ Remove any sensitive data from a K8s dict"""
    if obj_dict.get('data'):
        # Secret data
        obj_dict.pop('data')
    if obj_dict.get('string_data'):
        # The API should not return sting_data in Secrets, but just in case
        obj_dict.pop('string_data')
    if obj_dict['metadata'].get('annotations'):
        # Remove things like 'openshift.io/token-secret' from metadata
        for key in [k for k in obj_dict['metadata']['annotations'] if 'secret' in k]:
            obj_dict['metadata']['annotations'].pop(key)


def to_snake(name):
    """ Convert a string from camel to snake """
    if not name:
        return name

    def _replace(m):
        m = m.group(0)
        return m[0] + '_' + m[1:]

    p = r'[a-z][A-Z]|' \
        r'[A-Z]{2}[a-z]'
    return re.sub(p, _replace, name).lower()


class DateTimeEncoder(json.JSONEncoder):
    # When using json.dumps() with K8s object, pass cls=DateTimeEncoder to handle any datetime objects
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)


class KubernetesAnsibleModuleHelper(AnsibleMixin, KubernetesObjectHelper):
    pass


class KubernetesAnsibleModule(AnsibleModule):
    resource_definition = None
    api_version = None
    kind = None
    helper = None

    def __init__(self, *args, **kwargs):

        if not HAS_K8S_MODULE_HELPER:
            raise Exception(
                "This module requires the OpenShift Python client. Try `pip install openshift`"
            )

        if not HAS_YAML:
            raise Exception(
                "This module requires PyYAML. Try `pip install PyYAML`"
            )

        if not HAS_STRING_UTILS:
            raise Exception(
                "This module requires Python string utils. Try `pip install python-string-utils`"
            )

        kwargs['argument_spec'] = self.argspec
        AnsibleModule.__init__(self, *args, **kwargs)

    @property
    def argspec(self):
        raise NotImplementedError()

    def get_helper(self, api_version, kind):
        try:
            helper = KubernetesAnsibleModuleHelper(api_version=api_version, kind=kind, debug=False)
            helper.get_model(api_version, kind)
            return helper
        except KubernetesException as exc:
            self.fail_json(msg="Error initializing module helper: {0}".format(exc.message))

    def execute_module(self):
        raise NotImplementedError()

    def exit_json(self, **return_attributes):
        """ Filter any sensitive data that we don't want logged """
        if return_attributes.get('result') and \
           return_attributes['result'].get('kind') in ('Secret', 'SecretList'):
            if return_attributes['result'].get('data'):
                remove_secret_data(return_attributes['result'])
            elif return_attributes['result'].get('items'):
                for item in return_attributes['result']['items']:
                    remove_secret_data(item)
        super(KubernetesAnsibleModule, self).exit_json(**return_attributes)

    def authenticate(self):
        try:
            auth_options = {}
            auth_args = ('host', 'api_key', 'kubeconfig', 'context', 'username', 'password',
                         'cert_file', 'key_file', 'ssl_ca_cert', 'verify_ssl')
            for key, value in iteritems(self.params):
                if key in auth_args and value is not None:
                    auth_options[key] = value
            self.helper.set_client_config(**auth_options)
        except KubernetesException as e:
            self.fail_json(msg='Error loading config', error=str(e))

    def remove_aliases(self):
        """
        The helper doesn't know what to do with aliased keys
        """
        for k, v in iteritems(self.argspec):
            if 'aliases' in v:
                for alias in v['aliases']:
                    if alias in self.params:
                        self.params.pop(alias)

    def load_resource_definition(self, src):
        """ Load the requested src path """
        result = None
        path = os.path.normpath(src)
        if not os.path.exists(path):
            self.fail_json(msg="Error accessing {0}. Does the file exist?".format(path))
        try:
            result = yaml.safe_load(open(path, 'r'))
        except (IOError, yaml.YAMLError) as exc:
            self.fail_json(msg="Error loading resource_definition: {0}".format(exc))
        return result

    def resource_to_parameters(self, resource):
        """ Converts a resource definition to module parameters """
        parameters = {}
        for key, value in iteritems(resource):
            if key in ('apiVersion', 'kind', 'status'):
                continue
            elif key == 'metadata' and isinstance(value, dict):
                for meta_key, meta_value in iteritems(value):
                    if meta_key in ('name', 'namespace', 'labels', 'annotations'):
                        parameters[meta_key] = meta_value
            elif key in self.helper.argspec and value is not None:
                parameters[key] = value
            elif isinstance(value, dict):
                self._add_parameter(value, [key], parameters)
        return parameters

    def _add_parameter(self, request, path, parameters):
        for key, value in iteritems(request):
            if path:
                param_name = '_'.join(path + [to_snake(key)])
            else:
                param_name = self.helper.attribute_to_snake(key)
            if param_name in self.helper.argspec and value is not None:
                parameters[param_name] = value
            elif isinstance(value, dict):
                continue_path = copy.copy(path) if path else []
                continue_path.append(self.helper.attribute_to_snake(key))
                self._add_parameter(value, continue_path, parameters)
            else:
                self.fail_json(
                    msg=("Error parsing resource definition. Encountered {0}, which does not map to a parameter "
                         "expected by the OpenShift Python module.".format(param_name))
                )


class OpenShiftAnsibleModuleHelper(AnsibleMixin, OpenShiftObjectHelper):
    pass


class OpenShiftAnsibleModuleMixin(object):

    def get_helper(self, api_version, kind):
        try:
            helper = OpenShiftAnsibleModuleHelper(api_version=api_version, kind=kind, debug=False)
            helper.get_model(api_version, kind)
            return helper
        except KubernetesException as exc:
            self.fail_json(msg="Error initializing module helper: {0}".format(exc.message))


class KubernetesLookup(object):

    def __init__(self):

        if not HAS_K8S_MODULE_HELPER:
            raise Exception(
                "Requires the OpenShift Python client. Try `pip install openshift`"
            )

        if not HAS_YAML:
            raise Exception(
                "Requires PyYAML. Try `pip install PyYAML`"
            )

        self.kind = None
        self.name = None
        self.namespace = None
        self.api_version = None
        self.label_selector = None
        self.field_selector = None
        self.include_uninitialized = None
        self.resource_definition = None
        self.helper = None
        self.connection = {}

    def run(self, terms, variables=None, **kwargs):
        self.mylog('Here!')
        self.kind = kwargs.get('kind')
        self.name = kwargs.get('resource_name')
        self.namespace = kwargs.get('namespace')
        self.api_version = kwargs.get('api_version', 'v1')
        self.label_selector = kwargs.get('label_selector')
        self.field_selector = kwargs.get('field_selector')
        self.include_uninitialized = kwargs.get('include_uninitialized', False)

        resource_definition = kwargs.get('resource_definition')
        src = kwargs.get('src')
        if src:
            resource_definition = self.load_resource_definition(src)
        if resource_definition:
            self.params_from_resource_definition(resource_definition)

        if not self.kind:
            raise Exception(
                "Error: no Kind specified. Use the 'kind' parameter, or provide an object YAML configuration "
                "using the 'resource_definition' parameter."
            )

        self.kind = to_snake(self.kind)
        self.helper = self.get_helper(self.api_version, self.kind)

        for arg in AUTH_ARG_SPEC:
            self.connection[arg] = kwargs.get(arg)

        try:
            self.helper.set_client_config(**self.connection)
        except Exception as exc:
            raise Exception(
                "Client authentication failed: {0}".format(exc.message)
            )

        if self.name:
            self.mylog("Calling get_object()")
            return self.get_object()

        return self.list_objects()

    def mylog(self, msg):
        with open('loggit.txt', 'a') as f:
            f.write(msg + '\n')

    def get_helper(self, api_version, kind):
        try:
            helper = KubernetesObjectHelper(api_version=api_version, kind=kind, debug=False)
            helper.get_model(api_version, kind)
            return helper
        except KubernetesException as exc:
            raise Exception("Error initializing helper: {0}".format(exc.message))

    def load_resource_definition(self, src):
        """ Load the requested src path """
        path = os.path.normpath(src)
        if not os.path.exists(path):
            raise Exception("Error accessing {0}. Does the file exist?".format(path))
        try:
            result = yaml.safe_load(open(path, 'r'))
        except (IOError, yaml.YAMLError) as exc:
            raise Exception("Error loading resource_definition: {0}".format(exc))
        return result

    def params_from_resource_definition(self, defn):
        if defn.get('apiVersion'):
            self.api_version = defn['apiVersion']
        if defn.get('kind'):
            self.kind = defn['kind']
        if defn.get('metadata', {}).get('name'):
            self.name = defn['metadata']['name']
        if defn.get('metadata', {}).get('namespace'):
            self.namespace = defn['metadata']['namespace']

    def get_object(self):
        """ Fetch a named object """
        try:
            result = self.helper.get_object(self.name, self.namespace)
        except KubernetesException as exc:
            raise Exception('Failed to retrieve requested object: {0}'.format(exc.message))
        self.mylog("Got restult")
        response = []
        if result is not None:
            # Convert Datetime objects to ISO format
            result_json = json.loads(json.dumps(result.to_dict(), cls=DateTimeEncoder))
            if self.kind == 'secret':
                remove_secret_data(result_json)
            response.append(result_json)

        return response

    def list_objects(self):
        """ Query for a set of objects """
        if self.namespace:
            method_name = 'list_namespaced_{0}'.format(self.kind)
            try:
                method = self.helper.lookup_method(method_name=method_name)
            except KubernetesException:
                raise Exception(
                    "Failed to find method {0} for API {1}".format(method_name, self.api_version)
                )
        else:
            method_name = 'list_{0}_for_all_namespaces'.format(self.kind)
            try:
                method = self.helper.lookup_method(method_name=method_name)
            except KubernetesException:
                method_name = 'list_{0}'.format(self.kind)
                try:
                    method = self.helper.lookup_method(method_name=method_name)
                except KubernetesException:
                    raise Exception(
                        "Failed to find method for API {0} and Kind {1}".format(self.api_version, self.kind)
                    )

        params = {}
        if self.field_selector:
            params['field_selector'] = self.field_selector
        if self.label_selector:
            params['label_selector'] = self.label_selector
        params['include_uninitialized'] = self.include_uninitialized

        if self.namespace:
            try:
                result = method(self.namespace, **params)
            except KubernetesException as exc:
                raise Exception(exc.message)
        else:
            try:
                result = method(**params)
            except KubernetesException as exc:
                raise Exception(exc.message)

        response = []
        if result is not None:
            # Convert Datetime objects to ISO format
            result_json = json.loads(json.dumps(result.to_dict(), cls=DateTimeEncoder))
            response = result_json.get('items', [])
            if self.kind == 'secret':
                for item in response:
                    remove_secret_data(item)
        return response


class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):
        return KubernetesLookup().run(terms, variables=variables, **kwargs)
