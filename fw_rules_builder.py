import pandas as pd
import numpy as np
import logging
import os
import warnings

from netmiko import ConnectHandler
import getpass
import logging
from classdefs import (
    AccessRuleClass,
    ApplicationClass,
    AddressBookEntryClass,
    ZoneClass,
)
from constdefs import *

warnings.simplefilter(action="ignore", category=FutureWarning)

level = logging.DEBUG
format = "%(asctime)s - %(funcName)s - %(levelname)s - %(message)s"

logging.basicConfig(filename='netmiko_transactions.log', format=format, level=level)
logger = logging.getLogger("netmiko")

def parse_source_and_generate_config(filename, device_os):
    #  -------------------------------- Load data from Excel spreadsheet--------------------------
    # --------------------------------------------------------------------------------------------
    # Load data from QoS Flows Sheet into dataframe
    xl = pd.ExcelFile(filename)
    logging.debug("=====> sheet_names: ", xl.sheet_names)
    # Load data from QoS Flows Tab into dataframe
    temp_df1 = xl.parse(traffic_flows_sheet_name)
    # Replace empty values with empty stings to avoid errors in processing data as strings
    traffic_flows_dataframe = temp_df1.replace(np.nan, "", regex=True)

    temp_df2 = xl.parse(address_book_sheet_name)
    address_book_dataframe = temp_df2.replace(np.nan, "", regex=True)

    temp_df3 = xl.parse(zones_sheet_name)
    zones_dataframe = temp_df3.replace(np.nan, "", regex=True)

    print(f"--------------- Loaded Data Sources -------------------")
    print(
        f"records found in {traffic_flows_sheet_name} sheet: {str(len(traffic_flows_dataframe[RuleColumnName]))}"
    )
    print(
        f"records found in {address_book_sheet_name} sheet: {str(len(address_book_dataframe[AddressBookNetworkColumnName]))}"
    )

    # --------------------- Parse Actions ---------------------

    action_list = []

    # Get Headers from the dataframe
    headers_list = list(traffic_flows_dataframe.columns.values)

    # search for Action header - Active/Delete/etc
    for header in headers_list:
        if (ActionActive in header) or (ActionDelete in header):
            action_list.append(header)
    # Special case when Action is Active and aet to No - deactivate
    action_list.append(ActionDeactivate)

    # --------------------------------------- Process dataframe ---------------------------------------

    acl_list = []

    # process each action - Active/Delete/etc - create a sub-dataframe with the required actions only
    for action in action_list:
        # process special case when Active is set to No, deactivate the rule
        if action == ActionDeactivate:
            action_dataframe = temp_df1.loc[
                (traffic_flows_dataframe[ActionActive] == "No")
                & (traffic_flows_dataframe[ActionDelete] == "No")
                ]
        elif action == ActionActive:
            action_dataframe = temp_df1.loc[
                (traffic_flows_dataframe[action] == "Yes")
                & (traffic_flows_dataframe[ActionDelete] == "No")
                ]
        elif action == ActionDelete:
            action_dataframe = temp_df1.loc[
                (traffic_flows_dataframe[ActionDelete] == "Yes")
            ]

        for index, row in action_dataframe.iterrows():
            # app_definition = clsApplication()
            acl = AccessRuleClass(
                traffic_flows_dataframe.ix[index, RuleColumnName],
                traffic_flows_dataframe.ix[index, DescriptionColumnName],
                action,
                traffic_flows_dataframe.ix[index, ProtocolColumnName],
                traffic_flows_dataframe.ix[index, SourcePortColumnName],
                traffic_flows_dataframe.ix[index, SourceZoneColumnName],
                traffic_flows_dataframe.ix[index, SourceNetworkColumnName],
                traffic_flows_dataframe.ix[index, DestinationZoneColumnName],
                traffic_flows_dataframe.ix[index, DestinationNetworkColumnName],
                traffic_flows_dataframe.ix[index, DestinationPortColumnName],
                traffic_flows_dataframe.ix[index, RuleActionColumnName],
            )

            acl_list.append(acl)

    # --------------------------------------- 1. print ACLs ---------------------------------------
    # print full dataframe strings, don't cut them
    pd.set_option("display.max_colwidth", -1)

    device_config = ""
    for action in action_list:
            device_config = device_config + f"\n\n# ------------------------------- {action} ---------------------------------"

            for acl in acl_list:
                if acl.Action == action:
                    application_definition = ApplicationClass(
                        acl.Protocol, acl.SourcePort, acl.DestinationPort
                    )
                    zones_definition = ZoneClass(
                        zones_dataframe, acl.SourceZone, acl.DestinationZone
                    )
                    address_book_definition = AddressBookEntryClass(
                        address_book_dataframe,
                        acl.Name,
                        acl.Description,
                        acl.SourceNetworkAndMask,
                        acl.DestinationNetworkAndMask,
                    )
                    device_config = device_config +  f"\n# -------- {acl.Description} -------------"
                    if action == ActionActive:
                        device_config = device_config  + application_definition.convert_to_device_format(device_os) + "\n"
                        device_config = device_config + address_book_definition.convert_to_device_format(device_os) + "\n"
                    device_config =  device_config + acl.convert_to_device_format(
                            device_os, application_definition, address_book_definition, zones_definition) + "\n"

    return device_config

def connect_to_fw_validate_config(config):

    # Establish a connection to the router

    password = getpass.getpass()

    virtual_srx = {
        'device_type': 'juniper',
        'host': '10.27.40.180',
        'username': 'alex',
        'password': password,
        'port': 22,
        "verbose": "True",
        'global_delay_factor': 4,
    }
    net_connect = ConnectHandler(**virtual_srx)

    net_connect.session_preparation()
    net_connect.enable()

    print("------------ Deploying configuration --------------")
    config_commands = config.splitlines()

    config_commands = ['set security zones security-zone test-segment2']

    print("Commands:", config_commands)

    output = net_connect.send_config_set(config_commands, exit_config_mode=False)
    print("Done\n")

    print("------------ Validating configuration --------------")
    commit_check_commands = ['commit check']
    commit_check = net_connect.send_config_set(commit_check_commands, exit_config_mode=False)
    # sleep(5)
    print(commit_check, "\n\n")

    if "succeeds" in commit_check:
        print("----------- Success ----------- ")
        show_compare_commands = "show | compare"
        show_compare = net_connect.send_config_set(show_compare_commands, exit_config_mode=False)
        #     sleep(5)
        print(show_compare)

        # Rollback anyway to previous clean state
        # print("------------ Validation failed - Rollback -----------")
        rollback = net_connect.send_command("rollback 0")
        # print (rollback)

    #    commit = net_connect.send_command("commit and-quit")
    #    print (commit)
    #    print ("configuration saved on " + device)
    #    f = open('configured/configured.txt', 'a+')
    #    f.write(device +' has been configured \n')
    #    f.close()
    else:
        print("------------ Validation failed - Rollback -----------")
        rollback = net_connect.send_command("rollback 0")
        print(rollback)
        # print ("the following device " + device + " had a commit error and has been rolled back")
        # f = open('failed/commit_error.txt', 'a')
        # f.write('Commit check failed for ' + device + '\n')
        # f.close()

    print('\n')
    print(80 * '-')


def main():
    config = parse_source_and_generate_config(filename, "JUNOS")
    print(
        "\n ************************* Firewall configuration below ****************************"
    )
    print(config)

    connect_to_fw_validate_config(config)

if __name__ == "__main__":
    # argparse here
    main()
