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

from itertools import product
from itertools import izip
import json


def load_json_file(json_file='/etc/tempest/testplans.json'):
    with open(json_file) as data_file:
        _json_obj = json.load(data_file)
    return _json_obj


def dict_product(dicts, filter_list):
    tmp_list = list(dict(izip(dicts, x)) for x in product(*dicts.itervalues()))
    res_list = []
    for item in tmp_list:
        for filter_obj in filter_list:
            # item contains filter_obj
            pair_in_dict = True
            for key, value in filter_obj.iteritems():
                if value != item[key]:
                    pair_in_dict = False
                    break
            if pair_in_dict:
                break
        else:
            res_list.append(item)

    return res_list


def get_feature_scenarios(g_json_obj, feature):
    current_task = g_json_obj['tasks'][feature]
    for item in current_task:
        for key, value in item['testcases'].iteritems():
            if not isinstance(value, list):
                item['testcases'][key] = [value]

    res_list = []
    for item in current_task:
        res_list += dict_product(item['testcases'], item['filters'])

    res_scenarios = []
    for res_item in res_list:
        scenario_name = res_item['driver'] + ' + ' + res_item['deploy_image'] + ' + ' + res_item['user_image']
        if 'config_drive' in res_item:
            scenario_name += ' + config_drive'
        if 'boot_mode' in res_item and res_item['boot_mode'] != 'none':
            scenario_name += ' + boot_mode:' + res_item['boot_mode']
        if 'secure_boot' in res_item and res_item['secure_boot'] != 'false':
            scenario_name += ' + secure_boot'
        if 'boot_option' in res_item and res_item['boot_option'] != 'none':
            scenario_name += ' + boot_option:' + res_item['boot_option']

        res_item['deploy_image'] = g_json_obj['deploy_images'][res_item['deploy_image']]
        res_item['user_image'] = g_json_obj['user_images'][res_item['user_image']]
        # port and driver_info have the same key
        res_item['port'] = g_json_obj['ports'][res_item['driver_info']]
        res_item['driver_info'] = g_json_obj['driver_infos'][res_item['driver_info']]
        # flavor and properties have the same key
        res_item['flavor'] = g_json_obj['flavors'][res_item['properties']]
        res_item['properties'] = g_json_obj['properties'][res_item['properties']]

        res_scenarios.append((scenario_name, res_item,))

    return res_scenarios


def test_get_feature_scenarios(g_json_obj, feature):
    print(feature.upper())
    current_task = g_json_obj['tasks'][feature]
    res_list = []
    for item in current_task:
        for key, value in item['testcases'].iteritems():
            if not isinstance(value, list):
                item['testcases'][key] = [value]

    for item in current_task:
        print("")
        res = dict_product(item['testcases'], item['filters'])
        for val in res:
            print(val)
    print("------------------------------------")


def _has_image_key(task_name, image_dict, image_list):
    for image in image_list:
        if image_dict.get(image, None) is None:
            print(task_name + 'image key \"' + image + '\" does not exist')
            return False
    return True


def _check_image(g_json_obj):
    tasks = g_json_obj['tasks']
    for task_name, task_list in tasks.iteritems():
        for item in task_list:
            deploy_image = item['testcases']['deploy_image']
            user_image = item['testcases']['user_image']
            if not isinstance(deploy_image, list):
                item['testcases']['deploy_image'] = [deploy_image]
            if not isinstance(user_image, list):
                item['testcases']['user_image'] = [user_image]
            if not _has_image_key(task_name, g_json_obj['deploy_images'], deploy_image):
                break
            if not _has_image_key(task_name, g_json_obj['user_images'], user_image):
                break


if __name__ == '__main__':
    g_json_obj = load_json_file('testplans.json')
    test_get_feature_scenarios(g_json_obj, "config_drive")
    test_get_feature_scenarios(g_json_obj, "secure_boot")
    test_get_feature_scenarios(g_json_obj, "hardware_discovery")
    test_get_feature_scenarios(g_json_obj, "local_boot_for_iscsi")
    test_get_feature_scenarios(g_json_obj, "whole_disk_for_iscsi")
    test_get_feature_scenarios(g_json_obj, "automate_boot_for_iscsi")
    test_get_feature_scenarios(g_json_obj, "uefi_for_agent")
    test_get_feature_scenarios(g_json_obj, "tear_down")
    test_get_feature_scenarios(g_json_obj, "stand_alone")
    test_get_feature_scenarios(g_json_obj, "conductor_failover")
    test_get_feature_scenarios(g_json_obj, "ipxe_for_pxe")

    _check_image(g_json_obj)
    # TODO cleaning secure firmware update
    #
    # TODO cleaning iLO license install
    #