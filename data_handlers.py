import numpy as np
import pandas as pd

from classdefs import (
    AccessRuleClass,
    ApplicationClass,
    AddressBookEntryClass,
    ZoneClass,
)
from constdefs import *


# -------------------------------------------------------------------------------------------


def load_source(filename):
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

    # print(Fore.GREEN + f"--------------- Loaded Data Sources -------------------")
    # print(f"records found in {traffic_flows_sheet_name} sheet: {str(len(traffic_flows_dataframe[RuleColumnName]))}")

    return traffic_flows_dataframe, address_book_dataframe, zones_dataframe, standard_apps_dataframe


# -------------------------------------------------------------------------------------------


def parse_flows_dataframes(traffic_flows_dataframe):

    action_list = []

    # Get Headers from the dataframe and search for Action header - Active/Delete/etc
    headers_list = list(traffic_flows_dataframe.columns.values)

    for header in headers_list:
        if (ActionEnable in header) or (ActionDelete in header):
            action_list.append(header)
    # Special case when Action is Enabled and set to No - deactivate
    action_list.append(ActionDeactivate)

    # Process dataframe
    # Result is List of Access Rules objects
    acl_list = []

    # process each action - Enable/Delete/etc - create a sub-dataframe with the required actions only
    for action in action_list:
        # process special case when Active is set to No, deactivate the rule
        if action == ActionDeactivate:
            action_dataframe = traffic_flows_dataframe.loc[
                (traffic_flows_dataframe[ActionEnable] == "No")
                & (traffic_flows_dataframe[ActionDelete] == "No")
                ]
        elif action == ActionEnable:
            action_dataframe = traffic_flows_dataframe.loc[
                (traffic_flows_dataframe[action] == "Yes") & (traffic_flows_dataframe[ActionDelete] == "No")
            ]
        elif action == ActionDelete:
            action_dataframe = traffic_flows_dataframe.loc[(traffic_flows_dataframe[ActionDelete] == "Yes")]

        # Process each Action Dataframe and generate rules for this action
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

    return (acl_list, action_list)


def generate_config(
        acl_list, action_list, address_book_dataframe, zones_dataframe, standard_apps_dataframe, device_os
):
    """

    :param acl_list:
    :param action_list:
    :param device_os: Network OS, such as junos
    :param address_book_dataframe:
    :param zones_dataframe:
    :param standard_apps_dataframe:
    :return: Device Configuration as a string
    """

    device_config = ""
    for action in action_list:
        device_config = (
                device_config
                + f"\n\n# ------------------------ Rules to {action} ---------------------------------"
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
                            device_config + application_definition.convert_to_device_format(device_os) + "\n"
                    )
                    device_config = (
                            device_config + address_book_definition.convert_to_device_format(device_os) + "\n"
                    )

                device_config = (
                    device_config
                    + acl.convert_to_device_format(
                        device_os, application_definition, address_book_definition, zones_definition
                    )
                    + "\n"
                )

    return device_config
