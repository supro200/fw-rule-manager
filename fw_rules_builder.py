import pandas as pd
import numpy as np
import textwrap
import logging
import os
import warnings
import ipaddress

warnings.simplefilter(action="ignore", category=FutureWarning)
import argparse

output_directory = "_output"

level = logging.INFO
format = "%(asctime)s - %(funcName)s - %(levelname)s - %(message)s"
handlers = [logging.FileHandler("qos_config_builder.log"), logging.StreamHandler()]
# handlers = [logging.StreamHandler()]
logging.basicConfig(level=level, format=format, handlers=handlers)

from classdefs import AccessRuleClass, ApplicationClass, AddressBookEntryClass
from constdefs import *


def main():
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
                traffic_flows_dataframe[ActionActive] == "No"
            ]
        else:
            action_dataframe = temp_df1.loc[traffic_flows_dataframe[action] == "Yes"]

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
            )

            acl_list.append(acl)

    # --------------------------------------- 1. print ACLs ---------------------------------------
    # print full dataframe strings, don't cut them
    pd.set_option("display.max_colwidth", -1)

    # we will make sure that the output directory exists
    if not os.path.exists(output_directory):
        os.mkdir(output_directory)

    print(
        "\n ************************* Firewall configuration below ****************************"
    )

    for action in action_list:
        print(
            f"\n# ------------------------------- {action} ---------------------------------"
        )
        for acl in acl_list:
            if acl.Action == action:
                application_definition = ApplicationClass(
                    acl.Protocol, acl.SourcePort, acl.DestinationPort
                )
                address_book_definition = AddressBookEntryClass(
                    address_book_dataframe,
                    acl.Name,
                    acl.Description,
                    acl.SourceNetworkAndMask,
                    acl.DestinationNetworkAndMask,
                )

                print(f"# -------- {acl.Description} -------------")
                if action == ActionActive:
                    print(application_definition.convert_to_device_format("JUNOS"))
                    print(address_book_definition.convert_to_device_format("JUNOS"))
                print(
                    acl.convert_to_device_format(
                        "JUNOS", application_definition, address_book_definition
                    )
                )


if __name__ == "__main__":
    # argparse here
    main()
