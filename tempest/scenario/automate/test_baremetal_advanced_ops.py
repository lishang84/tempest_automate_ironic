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


from tempest import test
import testscenarios
from tempest.scenario.automate import testplans
from tempest.scenario.automate import baremetal_advanced_utils
from oslo_log import log as logging
from tempest import config
import time
from tempest.scenario.manager import BaremetalPowerStates
from tempest.scenario.manager import BaremetalProvisionStates


CONF = config.CONF
LOG = logging.getLogger(__name__)

g_json_obj = testplans.load_json_file()

# TODO generate test report


class TestConfigDrive(testscenarios.TestWithScenarios,
                      baremetal_advanced_utils.BaremetalAdvancedUtils):
    scenarios = testplans.get_feature_scenarios(g_json_obj, "config_drive")

    def verify_config_drive_and_terminate(self):
        self.validate_ports()

        username = None
        if 0 <= self.user_image['image_files'][0]['name'].find("ubuntu"):
            username = "ubuntu"
        if 0 <= self.user_image['image_files'][0]['name'].find("fedora"):
            username = "fedora"

        vm_client = self.get_remote_client(self.instance, username=username)

        """
        To verify if config file realy exist on vm instance.
        """
        if 'fs' == self.user_image['type']:
            cmd_mount = 'sudo mount /dev/sda2 /mnt'
        else:
            cmd_mkdir = 'sudo mkdir -p /mnt/config'
            vm_client.exec_command(cmd_mkdir)
            cmd_mount = 'sudo mount /dev/disk/by-label/config-2 /mnt/config'

        try:
            vm_client.exec_command(cmd_mount)
        except:
            self.assertEqual("instance", "connectable")

        self.terminate_instance()

    @test.idempotent_id('549173a5-38ec-42bb-b0e2-c8b9f4a08943')
    @test.services('baremetal', 'compute', 'image', 'network')
    def test_baremetal_config_drive(self):
        self.common_operation()
        self.verify_and_terminate()
        #self.verify_config_drive_and_terminate()


class TestSecureBoot(testscenarios.TestWithScenarios,
                     baremetal_advanced_utils.BaremetalAdvancedUtils):
    scenarios = testplans.get_feature_scenarios(g_json_obj, "secure_boot")

    def change_conf_and_restart(self):
        # TODO check property in conf file and restart ironic-conductor service
        pass

    @test.idempotent_id('549173a5-38ec-42bb-b0e2-c8b9f4a08943')
    @test.services('baremetal', 'compute', 'image', 'network')
    def test_baremetal_secure_boot(self):
        if hasattr(self, 'secure_deploy_mode'):
            self.change_conf_and_restart()
        self.common_operation()
        self.verify_and_terminate()


class TestHardwareDiscovery(testscenarios.TestWithScenarios,
                            baremetal_advanced_utils.BaremetalAdvancedUtils):
    scenarios = testplans.get_feature_scenarios(g_json_obj, "hardware_discovery")

    @test.idempotent_id('549173a5-38ec-42bb-b0e2-c8b9f4a08943')
    @test.services('baremetal', 'compute', 'image', 'network')
    def test_baremetal_hardware_discovery(self):
        self.common_operation(inspect=True)
        self.verify_and_terminate()


class TestLocalBootForIscsi(testscenarios.TestWithScenarios,
                            baremetal_advanced_utils.BaremetalAdvancedUtils):
    scenarios = testplans.get_feature_scenarios(g_json_obj, "local_boot_for_iscsi")

    @test.idempotent_id('549173a5-38ec-42bb-b0e2-c8b9f4a08943')
    @test.services('baremetal', 'compute', 'image', 'network')
    def test_baremetal_local_boot_for_iscsi(self):
        self.common_operation()
        # check noode boots from disk or pxe(virtual media)
        self.verify_and_terminate()


class TestWholeDiskForIscsi(testscenarios.TestWithScenarios,
                            baremetal_advanced_utils.BaremetalAdvancedUtils):
    scenarios = testplans.get_feature_scenarios(g_json_obj, "whole_disk_for_iscsi")

    @test.idempotent_id('549173a5-38ec-42bb-b0e2-c8b9f4a08943')
    @test.services('baremetal', 'compute', 'image', 'network')
    def test_baremetal_whole_disk_for_iscsi(self):
        self.common_operation()
        # check noode boots from disk or pxe(virtual media)
        self.verify_and_terminate()


class TestAutomateBootForIscsi(testscenarios.TestWithScenarios,
                               baremetal_advanced_utils.BaremetalAdvancedUtils):
    scenarios = testplans.get_feature_scenarios(g_json_obj, "automate_boot_for_iscsi")

    @test.idempotent_id('549173a5-38ec-42bb-b0e2-c8b9f4a08943')
    @test.services('baremetal', 'compute', 'image', 'network')
    def test_baremetal_automate_boot_for_iscsi(self):
        self.common_operation()
        self.verify_and_terminate()


class TestUefiForAgent(testscenarios.TestWithScenarios,
                       baremetal_advanced_utils.BaremetalAdvancedUtils):
    scenarios = testplans.get_feature_scenarios(g_json_obj, "uefi_for_agent")

    @test.idempotent_id('549173a5-38ec-42bb-b0e2-c8b9f4a08943')
    @test.services('baremetal', 'compute', 'image', 'network')
    def test_baremetal_uefi_for_agent(self):
        self.common_operation()
        self.verify_and_terminate()


class TestTearDown(testscenarios.TestWithScenarios,
                   baremetal_advanced_utils.BaremetalAdvancedUtils):
    scenarios = testplans.get_feature_scenarios(g_json_obj, "tear_down")

    def verify_state_and_terminate(self):
        if self.driver == 'iscsi_ilo' or self.driver == 'agent_ilo':
            self.validate_ports()
            self.verify_connectivity()

            # ironic node-set-provision-state <UUID> deleted
            # deleted-->cleaning-->clean wait-->available
            self.baremetal_client.set_node_provision_state(self.node['uuid'], 'deleted')
            self.wait_power_state(self.node['uuid'], BaremetalPowerStates.POWER_OFF)
            self.wait_provisioning_state(self.node['uuid'],
                                         BaremetalProvisionStates.CLEANING,
                                         timeout=CONF.baremetal.active_timeout)
            self.wait_provisioning_state(self.node['uuid'],
                                         BaremetalProvisionStates.CLEANWAIT,
                                         timeout=CONF.baremetal.active_timeout)
            self.wait_provisioning_state(self.node['uuid'],
                                         BaremetalProvisionStates.AVAILABLE,
                                         timeout=CONF.baremetal.active_timeout)
            self.terminate_instance()
        else:
            self.baremetal_client.set_node_provision_state(self.node['uuid'], 'manage')
            self.baremetal_client.set_node_provision_state(self.node['uuid'], 'provide')
            self.wait_provisioning_state(self.node['uuid'],
                                         BaremetalProvisionStates.CLEANING,
                                         timeout=CONF.baremetal.active_timeout)
            self.wait_provisioning_state(self.node['uuid'],
                                         BaremetalProvisionStates.CLEANWAIT,
                                         timeout=CONF.baremetal.active_timeout)
            self.wait_provisioning_state(self.node['uuid'],
                                         BaremetalProvisionStates.AVAILABLE,
                                         timeout=CONF.baremetal.active_timeout)

    @test.idempotent_id('549173a5-38ec-42bb-b0e2-c8b9f4a08943')
    @test.services('baremetal', 'compute', 'image', 'network')
    def test_baremetal_tear_down(self):
        if self.driver == 'iscsi_ilo' or self.driver == 'agent_ilo':
            self.common_operation()
        else:
            self.cleanup_all()
            self.deploy_image_create()
            self.ironic_node_create()
            # wait ironic node to sync power state
            wait_sec = 60
            LOG.info("sleep %s seconds" % wait_sec)
            time.sleep(wait_sec)
        self.verify_state_and_terminate()


class TestStandalone(testscenarios.TestWithScenarios,
                     baremetal_advanced_utils.BaremetalAdvancedUtils):
    scenarios = testplans.get_feature_scenarios(g_json_obj, "stand_alone")

    @test.idempotent_id('549173a5-38ec-42bb-b0e2-c8b9f4a08943')
    @test.services('baremetal', 'compute', 'image', 'network')
    def test_baremetal_stand_alone(self):
        # TODO
        pass


class TestConductorFailover(testscenarios.TestWithScenarios,
                            baremetal_advanced_utils.BaremetalAdvancedUtils):
    scenarios = testplans.get_feature_scenarios(g_json_obj, "conductor_failover")

    @test.idempotent_id('549173a5-38ec-42bb-b0e2-c8b9f4a08943')
    @test.services('baremetal', 'compute', 'image', 'network')
    def test_baremetal_conductor_failover(self):
        # TODO
        pass


class TestIpxeForPxe(testscenarios.TestWithScenarios,
                     baremetal_advanced_utils.BaremetalAdvancedUtils):
    scenarios = testplans.get_feature_scenarios(g_json_obj, "ipxe_for_pxe")

    @test.idempotent_id('549173a5-38ec-42bb-b0e2-c8b9f4a08943')
    @test.services('baremetal', 'compute', 'image', 'network')
    def test_baremetal_ipxe_for_pxe(self):
        # TODO handle the ipxe file, property 'ipxe_boot_file'
        # self.ipxe_boot_file
        pass

# TODO cleaning secure firmware update
#

# TODO cleaning iLO license install
#