.. _scenario_automate_field_guide:

Tempest Field Guide to Bare Metal Scenario Automated Tests
==========================================================


What are these tests?
---------------------

Bare metal scenario automated tests are specialized scenario tests for ironic features with
real http request to openstack service instead of fake request.

In 'Ironman Test Plan' (an test plan excel file written by Testing Engineer and Developer),
we have several features, and each feature contains an indefinite number of drivers: pxe_ilo,
agent_ilo and iscsi_ilo.
Each driver should be tested on gen8 and gen9, with option boot_mode, secure_boot or boot_option
specified, and we also need to filter some the cases.


How to config testplans.json?
-----------------------------
'testplans.json' is based on 'Ironman Test Plan' , and 'testplans.py' used to generate
test cases with the json file.

Details about json format in 'testplans.json.example'.

Root json object has several items:
"deploy_images": format:{"key1":{},"key2":{}}, 2 types: image, iso
"user_images": format:{"key1":{},"key2":{}}, 2 types: fs, disk
"driver_infos": format:{"key1":{},"key2":{}}
"ports": format:{"key1":"val1","key2":"val2"} key names must be the same as key names in 'driver_infos'
"properties": format:{"key1":{},"key2":{}}
"flavors": format:{"key1":{},"key2":{}} key names must be the same as key names in 'properties'
"tasks": format:{"feature_name1":[],"feature_name2":[]}

Each feature is an array, at most 3 items for 3 drivers in the array:
{
    "testcases":{
        "driver_name":"",
        ...
    },
    "filters":[
        {
            "option_name":"option_value",
            ...
        }
    ]
}


'testcases' object in json file:
"instance_name": required, name of instance, string
"driver": required, driver of instance, ['pxe_ilo', 'iscsi_ilo', 'agent_ilo'], string
"deploy_image": required, the object key name of deploy name, string or list
"user_image": required, the object key name of user image, string or list
"driver_info": required, on which machine to test, used when ironic node created, string or list
"properties": required, properties info when ironic node created,
"config_drive": optional, boolean, will be used only if true
"boot_mode": optional, string or list, ["uefi","bios","none"], will be dicarded if "none"
"secure_boot": optional, string or list, ["true","none"], will be dicarded if "none"
"boot_option": optional, string or list, ["local","netboot","none"], will be discarded if "none"

At last, run 'python testplans.py' to confirm the generated result.


Dependencies
------------
Depends on testscenarios module, details in https://pypi.python.org/pypi/testscenarios/
Generate scenario test cases for each feature


How to run these tests?
-----------------------
1. make sure you have an available network
neutron net-list
+--------------------------------------+------------+----------------------------------------------------+
| id                                   | name       | subnets                                            |
+--------------------------------------+------------+----------------------------------------------------+
| 80959d58-bb53-473f-a0b4-1b8cdd58a03c | sharednet1 | a115537d-019a-40b1-a3d4-f6f34fcbb7ed 10.102.0.0/24 |
+--------------------------------------+------------+----------------------------------------------------+

2. configure tempest.conf and testplans.json, put them in /etc/tempest
sudo cp ./tempest.conf /etc/tempest/tempest.conf
sudo cp ./testplans.json /etc/tempest/testplans.json

3. run commands

cd /opt/stack/tempest

Run feature 'config_drive':
python -m unittest tempest.scenario.automate.test_baremetal_advanced_ops.TestConfigDrive.test_baremetal_config_drive

Run all features:
python -m subunit.run tempest.scenario.automate.test_baremetal_advanced_ops | subunit2pyunit

Get csv format output
python -m subunit.run tempest.scenario.automate.test_baremetal_advanced_ops | subunit2csv



File explanation
----------------
testplans.py: generate testcases with testplans.json.

baremetal_advanced_utils.py: class and functions for creating instance on bare metal node.

test_baremetal_advanced_ops.py: several classes, each class is a feature,
inherited from BaremetalAdvancedUtils and testscenarios.


Deploy image type
-----------------
"image": .vmlinuz and .initramfs file
"iso": .iso file

User image type
---------------
"fs": .vmlinuz, .initrd and .qcow2 file
"disk": .qcow2 file


Copy the private key
--------------------
# sudo cp ~/.ssh/id_rsa /etc/tempest
# sudo cp ~/.ssh/id_rsa.pub /etc/tempest
# sudo chown -R stack:stack /etc/tempest