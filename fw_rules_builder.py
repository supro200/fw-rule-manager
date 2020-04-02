import pandas as pd
import numpy as np
import warnings
import argparse
import logging
import sys

from datetime import datetime

from colorama import init, Fore, Style  # colored screen output
from pathlib import Path  # OS-agnostic file handling

from classdefs import (
    AccessRuleClass,
    ApplicationClass,
    AddressBookEntryClass,
    ZoneClass,
)
from constdefs import *
from network_handlers import connect_to_fw_validate_config

warnings.simplefilter(action="ignore", category=FutureWarning)

level = logging.DEBUG
format = "%(asctime)s - %(funcName)s - %(levelname)s - %(message)s"
logging.basicConfig(filename="transactions.log", format=format, level=level)
logger = logging.getLogger("netmiko")


# -------------------------------------------------------------------------------------------
class CustomParser(argparse.ArgumentParser):
    """
    Overrides default CLI parser's print_help and error methods
    """

    def print_help(self):
        # Print default help from argparse.ArgumentParser class
        super().print_help()
        # print help messages
        # print(HELP_STRING)

    def error(self, message):
        print("error: %s\n" % message)
        print("Use --help or -h for help")
        exit(2)


def parse_args(args=sys.argv[1:]):
    """Parse arguments."""
    parser = CustomParser()
    parser._action_groups.pop()
    # required = parser.add_argument_group("required arguments")
    optional = parser.add_argument_group("optional arguments")
    optional.add_argument(
        "--validate",
        default=False,
        required=False,
        action="store_true",
        help="Validate with the live device",
    )
    optional.add_argument(
        "--screen-output",
        "--screen_output",
        default=True,
        required=False,
        action="store_true",
        help="Prints report to screen",
    )
    optional.add_argument(
        "--source_filename",
        "--source",
        help="File to parse",
    )
    optional.add_argument(
        "--network-os",
        "--network_os",
        help="Network OS to generate the config for",
    )
    return parser.parse_args(args)


def parse_source_and_generate_config(filename, device_os):
    #  -------------------------------- Load data from Excel spreadsheet--------------------------
    # --------------------------------------------------------------------------------------------
    # Load data from various Excel tabs into dataframes
    xl = pd.ExcelFile(filename)

    temp_df1 = xl.parse(traffic_flows_sheet_name)
    # Replace empty values with empty stings to avoid errors in processing data as strings
    traffic_flows_dataframe = temp_df1.replace(np.nan, "", regex=True)

    temp_df2 = xl.parse(address_book_sheet_name)
    address_book_dataframe = temp_df2.replace(np.nan, "", regex=True)

    temp_df3 = xl.parse(zones_sheet_name)
    zones_dataframe = temp_df3.replace(np.nan, "", regex=True)

    temp_df4 = xl.parse(standard_apps_sheet_name)
    standard_apps_dataframe = temp_df4.replace(np.nan, "", regex=True)

    print(Fore.GREEN + f"--------------- Loaded Data Sources -------------------")
    # print(Style.RESET_ALL)
    print(
        f"records found in {traffic_flows_sheet_name} sheet: {str(len(traffic_flows_dataframe[RuleColumnName]))}"
    )
    print(
        f"records found in {address_book_sheet_name} sheet: {str(len(address_book_dataframe[AddressBookNetworkColumnName]))}"
    )
    print(
        f"records found in {standard_apps_sheet_name} sheet: {str(len(standard_apps_dataframe[ApplicationColumnName]))}"
    )

    # --------------------- Parse Actions ---------------------

    action_list = []

    # Get Headers from the dataframe
    headers_list = list(traffic_flows_dataframe.columns.values)

    # search for Action header - Active/Delete/etc
    for header in headers_list:
        if (ActionEnable in header) or (ActionDelete in header):
            action_list.append(header)
    # Special case when Action is Enabled and set to No - deactivate
    action_list.append(ActionDeactivate)

    # --------------------------------------- Process dataframe ---------------------------------------

    acl_list = []

    # process each action - Enable/Delete/etc - create a sub-dataframe with the required actions only
    for action in action_list:
        # process special case when Active is set to No, deactivate the rule
        if action == ActionDeactivate:
            action_dataframe = temp_df1.loc[
                (traffic_flows_dataframe[ActionEnable] == "No")
                & (traffic_flows_dataframe[ActionDelete] == "No")
                ]
        elif action == ActionEnable:
            action_dataframe = temp_df1.loc[
                (traffic_flows_dataframe[action] == "Yes")
                & (traffic_flows_dataframe[ActionDelete] == "No")
                ]
        elif action == ActionDelete:
            action_dataframe = temp_df1.loc[(traffic_flows_dataframe[ActionDelete] == "Yes")]

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
        device_config = (
                device_config
                + f"\n\n# ------------------------------- {action} ---------------------------------"
        )

        for acl in acl_list:
            if acl.Action == action:
                application_definition = ApplicationClass(
                    standard_apps_dataframe, acl.Protocol, acl.SourcePort, acl.DestinationPort
                )
                zones_definition = ZoneClass(zones_dataframe, acl.SourceZone, acl.DestinationZone)
                address_book_definition = AddressBookEntryClass(
                    address_book_dataframe,
                    acl.Name,
                    acl.Description,
                    acl.SourceNetworkAndMask,
                    acl.DestinationNetworkAndMask,
                )
                device_config = device_config + f"\n# -------- {acl.Description} -------------"
                if action == ActionEnable:
                    device_config = (
                            device_config
                            + application_definition.convert_to_device_format(device_os)
                            + "\n"
                    )
                    device_config = (
                            device_config
                            + address_book_definition.convert_to_device_format(device_os)
                            + "\n"
                    )

                device_config = (
                        device_config
                        + acl.convert_to_device_format(
                    device_os, application_definition, address_book_definition, zones_definition
                )
                        + "\n"
                )

    return device_config


def main():
    # init colorama
    init(autoreset=True)

    # Check CLI arguments
    options = parse_args()

    source_filename = options.source_filename if options.source_filename else test_filename
    network_os = options.network_os if options.network_os else "junos"

    # get confirm from Excel file for a given Network OS
    config = parse_source_and_generate_config(source_filename, network_os)

    if config:
        print(Fore.GREEN + f"--------------- Config parsed and saved to a file -------------------")

        file_name = f"{output_dir}{network_os}-{datetime.now().strftime('%Y-%m-%d')}.txt".lower()
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        with open(file_name, "w") as f:
            f.write(config)
        print("\nConfig saved as: " + str(Path(file_name).resolve()))

    if options.screen_output:
        print("\n ************************* Firewall configuration below ****************************")
        print(config)

    if options.validate:
        connect_to_fw_validate_config(config, virtual_srx)


if __name__ == "__main__":
    main()
