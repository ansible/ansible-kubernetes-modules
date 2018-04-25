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

from __future__ import absolute_import, division, print_function

import copy

from ansible.module_utils.k8s.helper import COMMON_ARG_SPEC, AUTH_ARG_SPEC, OPENSHIFT_ARG_SPEC
from ansible.module_utils.k8s.common import KubernetesAnsibleModule, OpenShiftAnsibleModuleMixin, to_snake

try:
    from openshift.helper.exceptions import KubernetesException
except ImportError:
    # Exception handled in common
    pass


class KubernetesRawModule(KubernetesAnsibleModule):

    def __init__(self, *args, **kwargs):
        mutually_exclusive = [
            ('resource_definition', 'src'),
        ]

        KubernetesAnsibleModule.__init__(self, *args,
                                         mutually_exclusive=mutually_exclusive,
                                         supports_check_mode=True,
                                         **kwargs)

        self.kind = self.params.pop('kind')
        self.api_version = self.params.pop('api_version')
        self.resource_definition = self.params.pop('resource_definition')
        self.src = self.params.pop('src')
        if self.src:
            self.resource_definition = self.load_resource_definition(self.src)

        if self.resource_definition:
            self.api_version = self.resource_definition.get('apiVersion')
            self.kind = self.resource_definition.get('kind')

        if not self.api_version:
            self.fail_json(
                msg=("Error: no api_version specified. Use the api_version parameter, or provide it as part of a ",
                     "resource_definition.")
            )
        if not self.kind:
            self.fail_json(
                msg="Error: no kind specified. Use the kind parameter, or provide it as part of a resource_definition"
            )

    @property
    def argspec(self):
        argspec = copy.deepcopy(COMMON_ARG_SPEC)
        argspec.update(copy.deepcopy(AUTH_ARG_SPEC))
        return argspec

    def get_api_client(self):
        auth_args = ('host', 'api_key', 'kubeconfig', 'context', 'username', 'password',
                        'cert_file', 'key_file', 'ssl_ca_cert', 'verify_ssl')

        configuration = kubernetes.client.Configuration()

        for key, value in iteritems(self.params):
            if key in auth_args and value is not None:
                if key == 'api_key':
                    setattr(configuration, key, {'authorization': "Bearer {}".format(value)})
                else:
                    setattr(configuration, key, value)
            elif key in auth_args and value is None:
                env_value = os.getenv('K8S_AUTH_{}'.format(key.upper()), None)
                if env_value is not None:
                    setattr(configuration, key, env_value)

        kubernetes.client.Configuration.set_default(configuration)

        if params.get('username') and params.get('password') and params.get('host'):
            auth_method = 'params'
        elif params.get('api_key') and params.get('host'):
            auth_method = 'params'
        elif params.get('kubeconfig') or params.get('context'):
            auth_method = 'file'
        else:
            auth_method = 'default'

        # First try to do incluster config, then kubeconig
        if auth_method == 'default':
            try:
                kubernetes.config.load_incluster_config()
                return kubernetes.client.ApiClient()
            except kubernetes.config.ConfigException:
                return self.client_from_kubeconfig(params.get('kubeconfig'), params.get('context'))

        if auth_method == 'file':
            return self.client_from_kubeconfig(params.get('kubeconfig'), params.get('context'))

        if auth_method == 'params':
            return kubernetes.client.ApiClient(configuration)


    def client_from_kubeconfig(self):
        try:
            return kubernetes.config.new_client_from_config(config_file, context)
        except (IOError, kubernetes.config.ConfigException):
            # If we failed to load the default config file then we'll return
            # an empty configuration
            # If one was specified, we will crash
            if not config_file:
                return ApiClient()
            raise

    def exact_match(self, resource):
        kind = self.resource_definition['kind']
        if kind.lower().endswith('list'):
            kind = self.resource_definition['kind'][:-4]
        return (
            kind == resource.kind and
            self.resource_definition['apiVersion'] == '/'.join([resource.group, resource.apiversion])
        )

    def execute_module(self):

        self.client = openshift.dynamic.DynamicClient(self.get_api_client())

        state = self.params.pop('state', None)
        force = self.params.pop('force', False)
        name = self.params.get('name')
        namespace = self.params.get('namespace')
        existing = None

        self.remove_aliases()

        return_attributes = dict(changed=False, result=dict())

        if self.helper.base_model_name_snake.endswith('list'):
            k8s_obj = self._read(name, namespace)
            return_attributes['result'] = k8s_obj.to_dict()
            self.exit_json(**return_attributes)

        try:
            existing = self.helper.get_object(name, namespace)
        except KubernetesException as exc:
            self.fail_json(msg='Failed to retrieve requested object: {0}'.format(exc.message),
                           error=exc.value.get('status'))

        if state == 'absent':
            if not existing:
                # The object already does not exist
                self.exit_json(**return_attributes)
            else:
                # Delete the object
                if not self.check_mode:
                    try:
                        self.helper.delete_object(name, namespace)
                    except KubernetesException as exc:
                        self.fail_json(msg="Failed to delete object: {0}".format(exc.message),
                                       error=exc.value.get('status'))
                return_attributes['changed'] = True
                self.exit_json(**return_attributes)
        else:
            if not existing:
                k8s_obj = self._create(namespace)
                return_attributes['result'] = k8s_obj.to_dict()
                return_attributes['changed'] = True
                self.exit_json(**return_attributes)

            if existing and force:
                k8s_obj = None
                request_body = self.helper.request_body_from_params(self.params)
                if not self.check_mode:
                    try:
                        k8s_obj = self.helper.replace_object(name, namespace, body=request_body)
                    except KubernetesException as exc:
                        self.fail_json(msg="Failed to replace object: {0}".format(exc.message),
                                       error=exc.value.get('status'))
                return_attributes['result'] = k8s_obj.to_dict()
                return_attributes['changed'] = True
                self.exit_json(**return_attributes)

            # Check if existing object should be patched
            k8s_obj = copy.deepcopy(existing)
            try:
                self.helper.object_from_params(self.params, obj=k8s_obj)
            except KubernetesException as exc:
                self.fail_json(msg="Failed to patch object: {0}".format(exc.message))
            match, diff = self.helper.objects_match(self.helper.fix_serialization(existing), k8s_obj)
            if match:
                return_attributes['result'] = existing.to_dict()
                self.exit_json(**return_attributes)
            # Differences exist between the existing obj and requested params
            if not self.check_mode:
                try:
                    k8s_obj = self.helper.patch_object(name, namespace, k8s_obj)
                except KubernetesException as exc:
                    self.fail_json(msg="Failed to patch object: {0}".format(exc.message))
            return_attributes['result'] = k8s_obj.to_dict()
            return_attributes['changed'] = True
            self.exit_json(**return_attributes)

    def _create(self, namespace):
        request_body = None
        k8s_obj = None
        try:
            request_body = self.helper.request_body_from_params(self.params)
        except KubernetesException as exc:
            self.fail_json(msg="Failed to create object: {0}".format(exc.message))
        if not self.check_mode:
            try:
                k8s_obj = self.helper.create_object(namespace, body=request_body)
            except KubernetesException as exc:
                self.fail_json(msg="Failed to create object: {0}".format(exc.message),
                               error=exc.value.get('status'))
        return k8s_obj

    def _read(self, name, namespace):
        k8s_obj = None
        try:
            k8s_obj = self.helper.get_object(name, namespace)
        except KubernetesException as exc:
            self.fail_json(msg='Failed to retrieve requested object',
                           error=exc.value.get('status'))
        return k8s_obj
