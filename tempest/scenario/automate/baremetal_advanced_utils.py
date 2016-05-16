#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import time
import os
from time import gmtime, strftime
from oslo_log import log as logging
from tempest import config
import testscenarios
import tempest.test
from tempest import exceptions
from tempest_lib.common.utils import data_utils
from tempest_lib import exceptions as lib_exc
from tempest import clients
from tempest.common import fixed_network
from tempest.scenario import manager
from tempest.scenario.manager import BaremetalPowerStates
from tempest.scenario.manager import BaremetalProvisionStates


CONF = config.CONF
LOG = logging.getLogger(__name__)


def log_to_file(string):
    with open("/tmp/log.txt", "a") as f:
        time = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        f.write(time + ":" + string + "\n")
        f.flush()


class BaremetalAdvancedUtils(manager.ScenarioTest):
    @classmethod
    def skip_checks(cls):
        super(BaremetalAdvancedUtils, cls).skip_checks()
        if (not CONF.service_available.ironic or
           not CONF.baremetal.driver_enabled):
            msg = 'Ironic not available or Ironic compute driver not enabled'
            raise cls.skipException(msg)

    @classmethod
    def setup_credentials(cls):
        super(BaremetalAdvancedUtils, cls).setup_credentials()

        # use an admin client manager for baremetal client
        manager = clients.Manager(
            credentials=cls.admin_credentials()
        )
        cls.baremetal_client = manager.baremetal_client

    @classmethod
    def resource_setup(cls):
        super(BaremetalAdvancedUtils, cls).resource_setup()
        # allow any issues obtaining the node list to raise early
        cls.baremetal_client.list_nodes()

    def _node_state_timeout(self, node_id, state_attr,
                            target_states, timeout=10, interval=1):
        if not isinstance(target_states, list):
            target_states = [target_states]

        def check_state():
            node = self.get_node(node_id=node_id)
            log_to_file("Got %(state)s, looking for %(target_states)s" %
                        {'state': node.get(state_attr),
                         'target_states': target_states})
            if node.get(state_attr) in target_states:
                return True
            return False

        if not tempest.test.call_until_true(
            check_state, timeout, interval):
            msg = ("Timed out waiting for node %s to reach %s state(s) %s" %
                   (node_id, state_attr, target_states))
            raise exceptions.TimeoutException(msg)

    def wait_provisioning_state(self, node_id, state, timeout):
        self._node_state_timeout(
            node_id=node_id, state_attr='provision_state',
            target_states=state, timeout=timeout)

    def wait_power_state(self, node_id, state):
        self._node_state_timeout(
            node_id=node_id, state_attr='power_state',
            target_states=state, timeout=CONF.baremetal.power_timeout)

    def wait_node(self, instance_id):
        """Waits for a node to be associated with instance_id."""

        def _get_node():
            node = None
            try:
                node = self.get_node(instance_id=instance_id)
            except lib_exc.NotFound:
                pass
            return node is not None

        if not tempest.test.call_until_true(
            _get_node, CONF.baremetal.association_timeout, 1):
            msg = ('Timed out waiting to get Ironic node by instance id %s'
                   % instance_id)
            raise exceptions.TimeoutException(msg)

    def get_node(self, node_id=None, instance_id=None):
        if node_id:
            _, body = self.baremetal_client.show_node(node_id)
            return body
        elif instance_id:
            _, body = self.baremetal_client.show_node_by_instance_uuid(
                instance_id)
            if body['nodes']:
                return body['nodes'][0]

    def get_ports(self, node_uuid):
        ports = []
        _, body = self.baremetal_client.list_node_ports(node_uuid)
        for port in body['ports']:
            _, p = self.baremetal_client.show_port(port['uuid'])
            ports.append(p)
        return ports

    def verify_connectivity(self, ping=True):
        if ping:
            addr = self.instance['addresses'][CONF.compute.network_for_ssh][0]['addr']
            for i in range(0, 3):
                response = os.system("ping -c 1 " + addr)
                if response == 0:
                    break
                elif i != 2:
                    LOG.info("sleep 100 seconds")
                    time.sleep(120)
            self.assertEqual(response, 0)
        else:
            username = None
            if 0 <= self.user_image['image_files'][0]['name'].find("ubuntu"):
                username = "ubuntu"
            if 0 <= self.user_image['image_files'][0]['name'].find("fedora"):
                username = "fedora"
            dest = self.get_remote_client(self.instance, username=username)
            dest.validate_authentication()

    def get_keypair(self):
        name = data_utils.rand_name(self.__class__.__name__)
        with open("/etc/tempest/id_rsa.pub") as data_file:
            pub_key = unicode(str(data_file.read()))
        self.keypair = self.keypairs_client.create_keypair(name, pub_key=pub_key)
        with open("/etc/tempest/id_rsa") as data_file:
            private_key = unicode(str(data_file.read()))
        self.keypair['private_key'] = private_key
        self.addCleanup(self.keypairs_client.delete_keypair, name)

    def validate_ports(self):
        for port in self.get_ports(self.node['uuid']):
            n_port_id = port['extra']['vif_port_id']
            body = self.network_client.show_port(n_port_id)
            n_port = body['port']
            self.assertEqual(n_port['device_id'], self.instance['id'])
            self.assertEqual(n_port['mac_address'], port['address'])

    def terminate_instance(self):
        self.servers_client.delete_server(self.instance['id'])
        self.wait_power_state(self.node['uuid'],
                              BaremetalPowerStates.POWER_OFF)
        self.wait_provisioning_state(
            self.node['uuid'],
            BaremetalProvisionStates.NOSTATE,
            timeout=CONF.baremetal.unprovision_timeout)

    def cleanup_all(self):
        # list image and clear all
        image_list = self.image_client.image_list()
        for image_item in image_list:
            image_id = image_item['id']
            self.image_client.delete_image(image_id)
        # list flavor and clear all
        flavor_list = self.flavors_client.list_flavors()
        for flavor_item in flavor_list:
            flavor_id = flavor_item['id']
            self.flavors_client.delete_flavor(flavor_id)
        # list instance and clear all
        server_list = self.servers_client.list_servers()
        for server_item in server_list['servers']:
            server_id = server_item['id']
            self.servers_client.delete_server(server_id)
        # list ironic node and clear all
        _, node_list = self.baremetal_client.list_nodes()
        for node_item in node_list['nodes']:
            node_uuid = node_item['uuid']
            self.baremetal_client.delete_node(node_uuid)

    def _common_image_create(self, image_info, properties=None):
        if properties is None:
            properties = {}
        image_file = open(image_info['file_path'], 'rb')
        self.addCleanup(image_file.close)

        params = {
            'name': image_info['name'],
            'container_format': image_info['container_format'],
            'disk_format': image_info['disk_format'],
            'is_public': 'True'
        }

        params['properties'] = properties
        image = self.image_client.create_image(**params)
        self.addCleanup(self.image_client.delete_image, image['id'])
        self.assertEqual("queued", image['status'])
        self.image_client.update_image(image['id'], data=image_file)

        LOG.debug("paths: img: %s, container_fomat: %s, disk_format: %s, "
              "properties: %s" % (image_info['file_path'],
                                  image_info['container_format'],
                                  image_info['disk_format'],
                                  properties))
        return image['id']

    def deploy_image_create(self):
        res_image_ids = {}
        for image in self.deploy_image['image_files']:
            res_image_id = self._common_image_create(image)
            res_image_ids[image['disk_format']] = res_image_id
        # driver_info/deploy_kernel
        # driver_info/deploy_ramdisk
        # {"aki":"UUID","ari":"UUID"}
        # driver_info/ilo_deploy_iso
        # {"iso":"UUID"}
        self.obj_deploy_image = res_image_ids

    def user_image_create(self):
        type = self.user_image['type']
        kernel_id = None
        ramdisk_id = None
        iso_id = None
        qcow2_image = None
        for image in self.user_image['image_files']:
            if type == 'fs' and image['disk_format'] == 'aki':
                kernel_id = self._common_image_create(image)
            elif type == 'fs' and image['disk_format'] == 'ari':
                ramdisk_id = self._common_image_create(image)
            elif type == 'fs' and image['disk_format'] == 'iso':
                iso_id = self._common_image_create(image)
            else:
                qcow2_image = image

        properties = {}
        if kernel_id is not None and ramdisk_id is not None:
            properties = {'kernel_id': kernel_id, 'ramdisk_id': ramdisk_id}
        if iso_id is not None:
            properties['boot_iso'] = iso_id
        res_image_id = self._common_image_create(qcow2_image, properties=properties)
        # --image = UUID
        self.obj_user_image = res_image_id

    def flavor_create(self):
        kwargs = self.flavor['extra_specs']
        new_flavor = self.flavors_client.create_flavor(
                                                name=self.flavor['name'],
                                                ram=self.flavor['ram'],
                                                vcpus=self.flavor['vcpus'],
                                                disk=self.flavor['disk'],
                                                flavor_id=None,
                                                **kwargs)
        self.assertEqual(new_flavor['name'], self.flavor['name'])
        self.assertEqual(new_flavor['ram'], self.flavor['ram'])
        self.assertEqual(new_flavor['disk'], self.flavor['disk'])
        self.assertEqual(new_flavor['vcpus'], self.flavor['vcpus'])
        self.addCleanup(self.flavors_client.delete_flavor, new_flavor['id'])

        self._flavor_update(new_flavor['id'])
        self.obj_flavor = new_flavor

    def _flavor_update(self, id):
        # check boot_mode and secure_boot
        # 'capabilities:boot_mode':'uefi'
        if hasattr(self, 'boot_mode') and (self.boot_mode == 'uefi' or self.boot_mode == 'bios'):
            dict_pair = {'capabilities:boot_mode': self.boot_mode}
            update_body = self.flavors_client.update_flavor_extra_spec(
                id, 'capabilities:boot_mode', **dict_pair)
            self.assertEqual(dict_pair, update_body)

        if hasattr(self, 'secure_boot') and self.secure_boot == 'true':
            dict_pair = {'capabilities:secure_boot': 'true'}
            update_body = self.flavors_client.update_flavor_extra_spec(
                id, 'capabilities:secure_boot', **dict_pair)
            self.assertEqual(dict_pair, update_body)

        if hasattr(self, 'boot_option') and (self.boot_option == 'netboot' or self.boot_option == 'local'):
            dict_pair = {'capabilities:boot_option': self.boot_option}
            update_body = self.flavors_client.update_flavor_extra_spec(
                id, 'capabilities:boot_option', **dict_pair)
            self.assertEqual(dict_pair, update_body)

    def _generate_node_properties(self):
        # check boot_mode and secure_boot
        # properties/capabilities='boot_mode:uefi,secure_boot:true'
        # TODO if properties has extra info

        properties = self.properties.copy()
        prop_list = []
        if hasattr(self, 'boot_mode') and (self.boot_mode == 'uefi' or self.boot_mode == 'bios'):
            prop_list.append("boot_mode:" + self.boot_mode)
        if hasattr(self, 'secure_boot') and self.secure_boot == 'true':
            prop_list.append("secure_boot:" + self.secure_boot)
        if hasattr(self, 'boot_option') and (self.boot_option == 'netboot' or self.boot_option == 'local'):
            prop_list.append("boot_option:" + self.boot_option)

        properties['capabilities'] = ",".join(prop_list)
        return properties

    def ironic_node_create(self):
        # params that "ironic node-create" needed
        # driver: -d
        # driver_info: -i
        # properties: -p
        if self.obj_deploy_image.get('iso') is not None:
            self.driver_info['ilo_deploy_iso'] = self.obj_deploy_image['iso']
        else:
            self.driver_info['deploy_kernel'] = self.obj_deploy_image['aki']
            self.driver_info['deploy_ramdisk'] = self.obj_deploy_image['ari']
        kwargs = {}
        _, ironic_node = self.baremetal_client.create_node_advanced(
                            self.driver,
                            self._generate_node_properties(),
                            self.driver_info,
                            **kwargs)
        self.addCleanup(self.baremetal_client.delete_node, ironic_node['uuid'])
        self.wait_power_state(ironic_node['uuid'], BaremetalPowerStates.POWER_OFF)
        self.obj_ironic_node = ironic_node

    def ironic_node_inpect(self):
        # manage-->managable
        self.baremetal_client.set_node_provision_state(self.obj_ironic_node['uuid'], 'manage')
        self.wait_provisioning_state(self.obj_ironic_node['uuid'],
                                     BaremetalProvisionStates.MANAGEABLE,
                                     timeout=CONF.baremetal.active_timeout)
        # inspect-->inspecting-->manageable
        self.baremetal_client.set_node_provision_state(self.obj_ironic_node['uuid'], 'inspect')
        self.wait_provisioning_state(self.obj_ironic_node['uuid'],
                                     BaremetalProvisionStates.MANAGEABLE,
                                     timeout=CONF.baremetal.active_timeout)
        # provide-->available
        self.baremetal_client.set_node_provision_state(self.obj_ironic_node['uuid'], 'provide')
        self.wait_provisioning_state(self.obj_ironic_node['uuid'],
                                     BaremetalProvisionStates.AVAILABLE,
                                     timeout=CONF.baremetal.active_timeout)

    def ironic_port_create(self):
        _, ironic_port = self.baremetal_client.create_port_advanced(
                                            node_id=self.obj_ironic_node['uuid'],
                                            address=self.port,
                                            extra={},
                                            uuid=None)
        self.addCleanup(self.baremetal_client.delete_port, ironic_port['uuid'])
        self.obj_ironic_port = ironic_port

    def boot_instance(self):
        create_kwargs = {
            'key_name': self.keypair['name']
        }

        # create server start
        network = self.get_tenant_network()
        create_kwargs = fixed_network.set_networks_kwarg(network,
                                                         create_kwargs)
        if hasattr(self, 'config_drive'):
            create_kwargs['config_drive'] = self.config_drive
        LOG.debug("Creating a server (name: %s, image: %s, flavor: %s)",
                  self.instance_name, self.obj_user_image, self.obj_flavor['id'])
        self.instance = self.servers_client.create_server(
                            self.instance_name,
                            self.obj_user_image,
                            self.obj_flavor['id'],
                            **create_kwargs)
        # self.addCleanup(self.servers_client.wait_for_server_termination, self.instance['id'])
        self.addCleanup_with_wait(
            waiter_callable=self.servers_client.wait_for_server_termination,
            thing_id=self.instance['id'], thing_id_param='server_id',
            cleanup_callable=self.delete_wrapper,
            cleanup_args=[self.servers_client.delete_server, self.instance['id']])
        # create server end

        self.wait_node(self.instance['id'])
        self.node = self.get_node(instance_id=self.instance['id'])

        self.wait_power_state(self.node['uuid'], BaremetalPowerStates.POWER_ON)

        self.wait_provisioning_state(
            self.node['uuid'],
            [BaremetalProvisionStates.DEPLOYWAIT,
             BaremetalProvisionStates.ACTIVE],
            timeout=300)

        self.wait_provisioning_state(self.node['uuid'],
                                     BaremetalProvisionStates.ACTIVE,
                                     timeout=CONF.baremetal.active_timeout)

        self.servers_client.wait_for_server_status(self.instance['id'],
                                                   'ACTIVE')
        self.node = self.get_node(instance_id=self.instance['id'])
        self.instance = self.servers_client.get_server(self.instance['id'])
        self.assertEqual(self.instance['name'], self.instance_name)

    def common_operation(self, inspect=False):
        self.cleanup_all()
        # make sure that network and keypair have been created
        self.deploy_image_create()
        self.user_image_create()
        self.flavor_create()
        self.ironic_node_create()
        if inspect:
            self.ironic_node_inpect()
        else:
            self.ironic_port_create()

        # wait to avoid "no valid host" error
        wait_sec = 60
        LOG.info("sleep %s seconds" % wait_sec)
        time.sleep(wait_sec)

        self.get_keypair()
        self.boot_instance()

    def _wait_instance_boot(self):
        addr = self.instance['addresses'][CONF.compute.network_for_ssh][0]['addr']

        def _ping_server():
            response = os.system("ping -c 1 " + addr)
            if response == 0:
                return True
            else:
                return False

        if not tempest.test.call_until_true(_ping_server, CONF.baremetal.power_timeout, 20):
            msg = ('Timed out waiting to ping server by instance address %s' % addr)
            raise exceptions.TimeoutException(msg)

    def verify_and_terminate(self):
        self._wait_instance_boot()
        self.validate_ports()
        # self.verify_connectivity()
        self.terminate_instance()
