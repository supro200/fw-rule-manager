import pandas as pd
import numpy as np
import textwrap
import logging
import os
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import argparse
output_directory = "_output"

level = logging.INFO
format = '%(asctime)s - %(funcName)s - %(levelname)s - %(message)s'
handlers = [logging.FileHandler('qos_config_builder.log'), logging.StreamHandler()]
# handlers = [logging.StreamHandler()]
logging.basicConfig(level=level, format=format, handlers=handlers)

#  -------------  Define Column Names -------------

ProtocolColumnName = "Protocol"
SourceNetworkColumnName = "Source Network"
SourceNetworkMaskColumnName = "Source Mask Length"
SourcePortColumnName = "Source Port"
DestinationNetworkColumnName = "Destination Network"
DestinationNetworkMaskColumnName = "Destination Mask Length"
DestinationPortColumnName = "Destination Port"
ReferenceColumnName = "Reference"
ServiceColumnName = "Service"
DescriptionColumnName = "Description"
SourceZoneColumnName = "Source Zone"
DestinationZoneColumnName = "Destination Zone"

QoSClassColumnDropDownName = "QoS Class Name"

QoSClassColumnName = "QoS Class"
ResultSheetName = "Result"

# Max length of remark statement in ACL
RemarkLenght = 90

filename = "fw_rules_test_02.xlsx"
traffic_flows_sheet_name = "Traffic Flows"
dropdown_fields_sheet_name = "Dropdown Fields"

ActionActive = "Active"
ActionDeactivate = "Deactivate"
ActionDelete = "Delete"

# --------------------------------------- Define Classes to store data ---------------------------------------

class clsTrafficFlowACL:
    """QoS ACL Entry.
    ACL Entry has the following properties:

    Attributes:
        QoSACL: ACL Entry itself
        QoSServiceName: Service description, such as Finance and Marketing, or Realtime Video
        QoSClassName: Class name, used for linking to QoS Classes
        QoSACLScope: ACL Scope - Where this ACL should be applied, i.e. Datacentre, Branch, Campus, etc.
        QoSACLDescription: ACL Description - put in the final config
        QoSACLPriority: ACL Priority - HZ
    """

    def __init__(self, ACL="", QoSServiceName="", QoSRecordRef="", QoSClassName="", QoSACLScope="",
                 QoSACLDescription="", QoSACLPriority=""):
        """Return a ACL object, Initialize with empty values"""
        self.QoSACL = ACL
        self.QoSServiceName = QoSServiceName
        self.QoSClassName = QoSClassName
        self.QoSRecordRef = QoSRecordRef
        self.QoSACLScope = QoSACLScope
        self.QoSACLDescription = QoSACLDescription
        self.QoSACLPriority = QoSACLPriority

#
# class clsQoSClass:
#     def __init__(self, QoSClassName="", QoSACLScope="", QoSACLPriority="", QoSACLList=[]):
#         """Return a QoS Class object, Initialize with empty values"""
#         self.QoSClassName = QoSClassName
#         self.QoSACLScope = QoSACLScope
#         self.QoSACLPriority = QoSACLPriority
#         self.QoSACLList = QoSACLList

#  --------------------------------------- Define functions  ---------------------------------------

# converts CIDR to dotted netmask (i.e %s 24  => 255.255.255.0)
def calcDottedNetmask(mask):
    bits = 0
    for i in range(32 - mask, 32):
        bits |= (1 << i)
    return "%d.%d.%d.%d" % ((bits & 0xff000000) >> 24, (bits & 0xff0000) >> 16, (bits & 0xff00) >> 8, (bits & 0xff))


# converts CIDR to wildcard (i.e %s 24  => 0.0.0.255)
def calcDottedWildcard(mask):
    bits = 0
    for i in range(32 - mask, 32):
        bits |= (1 << i)
    return "%d.%d.%d.%d" % (
        255 - ((bits & 0xff000000) >> 24), 255 - ((bits & 0xff0000) >> 16), 255 - ((bits & 0xff00) >> 8),
        255 - (bits & 0xff))

def define_application (Protocol, SourcePort, DestinationPort, Description):
    application_name = ""
    #print(Protocol, SourcePort, DestinationPort, Description)
    DestinationPort=str(DestinationPort).replace(" ", "_")
    application_name = f"set applications application {Protocol}_src_{SourcePort}_dst_{DestinationPort}".lower()
    return application_name

# --------------------------------------- Define Procedures ---------------------------------------
def build_acl(PolicyName, Protocol, SourcePort, SourceZone, SourceNetwork, SourceMaskLenth, DestinationZone, DestinationNetwork,
              DestinationMaskLength, DestinationPort, action, Description):

    fw_type = "JUNOS"

    #  if Source Network is "any" then Source Network Mask should be empty
    if SourceNetwork == "any":
        SourceNetworkAndMask = " any"
    else:
        SourceNetworkAndMask = " " + SourceNetwork + "/" + str(SourceMaskLenth)


    # if Destination Network is "any" then Destination Network Mask should be empty
    if DestinationNetwork == "any":
        DestinationNetworkAndMask = " any"
    else:
        DestinationNetworkAndMask = " " + DestinationNetwork + "/" + str(DestinationMaskLength)


    # check if Destination Port is a range or a single port
    if "-" in str(DestinationPort):
        DestinationPort = str(DestinationPort).replace("-", " ")
        DestinationPortCondition = " range "
    elif (DestinationPort == "n/a") or (DestinationPort == "") or (DestinationPort == "any"):
        DestinationPort = ""
        DestinationPortCondition = ""
    else:
        # DestinationPort = ""
        DestinationPortCondition = " eq "


    if Protocol == "any":
        Protocol = "ip"
        SourcePort = ""
        SourcePortCondition = ""
        DestinationPort = ""
        SourceNetworkMask = ""
        DestinationPortCondition = ""

    print(define_application(Protocol, SourcePort, DestinationPort, ""))

    if action == ActionActive and fw_type == "JUNOS":
        action_to_device_command = "set"
    elif action == ActionDelete:
        action_to_device_command = "delete"
    elif action == ActionDeactivate:
        action_to_device_command = "deactivate"

    # build a ACL
    resultACL = action_to_device_command + " security policies from-zone " +\
                SourceZone+ \
                " to-zone " + \
                DestinationZone + \
                " policy " + \
                PolicyName.replace(" ", "_") + \
                " description " + \
                 "\"" + Description + "\"" + \
                " match source-address" + \
                SourceNetworkAndMask + \
                " destination-address" + \
                DestinationNetworkAndMask + \
                DestinationPortCondition + \
                str(DestinationPort)

    logging.debug(resultACL.lower())
    print(resultACL)

    return resultACL.lower()


def main():
    #  -------------------------------- Load data from Excel spreadsheet--------------------------
    # --------------------------------------------------------------------------------------------
    # Load data from QoS Flows Sheet into dataframe
    xl = pd.ExcelFile(filename)
    logging.debug("=====> sheet_names: ", xl.sheet_names)
    # Load data from QoS Flows Tab into dataframe
    df = xl.parse(traffic_flows_sheet_name)
    # Replace empty values with empty stings to avoid errors in processing data as strings
    traffic_flows_dataframe = df.replace(np.nan, '', regex=True)
    print("Total records found in " + traffic_flows_sheet_name + " sheet: " + str(len(traffic_flows_dataframe['Reference'])))

    # ------------------------------------------------------------------------------------
    # Load data from Dropdown Fields Tab into dataframe - this is for matching QoS Class to DSCP, for example
    #temp_df1 = xl.parse(dropdown_fields_sheet_name)
    # Replace empty values with empty stings to avoid errors in processing data as strings
    #dropdown_fields_dataframe = temp_df1.replace(np.nan, '', regex=True)

    # --------------------- Parse Services ---------------------
    # Get a list of unique services - this will be used for grouping records into ACLs
    services_list = np.unique(np.array(traffic_flows_dataframe["Service"]))

    # Convert list to string for correct logging output
    # https://stackoverflow.com/questions/44778/how-would-you-make-a-comma-separated-string-from-a-list-of-strings
    logging.debug("=====> service_list: " + ','.join(services_list))

    # --------------------- Parse QoS classes ---------------------
    # Get a list of unique services - this will be used for grouping records into ACLs
    traffic_classes_list = np.unique(np.array(traffic_flows_dataframe["QoS Class"]))

    # Convert list to string for correct logging output
    # https://stackoverflow.com/questions/44778/how-would-you-make-a-comma-separated-string-from-a-list-of-strings
    #logging.info("=====> traffic_classes_list: " + ','.join(traffic_classes_list))
    # --------------------- Parse Actions ---------------------

    action_list = []

    # Get Headers from the dataframe
    headers_list = list(traffic_flows_dataframe.columns.values)
    # Search headers with 'Area' word and cut off first word 'Area' and last word which should be 'Return' or 'Entry'
    # Result is an unique list of areas in action_list[]
    for header in headers_list:
        if (ActionActive in header) or (ActionDelete in header):
            action_list.append(header)
    # Special case when Action is Active and aet to No - deactivate
    action_list.append(ActionDeactivate)

    # Make the values in the list unique
    # https://stackoverflow.com/questions/12897374/get-unique-values-from-a-list-in-python
    action_list = list(set(action_list))
    logging.debug("=====> action_list: " + ','.join(action_list))

    print(action_list)

    # --------------------------------------- Process dataframe ---------------------------------------

    # List of objects of class QosACL
    acl_list = []
    # Search for Areas/Scopes and for each row generate separate ACL for every Area
    # headers_list - all dataframe headers
    # action_list - all Areas/Scopes
   # for header in headers_list:
    for action in action_list:
    #        if action in header:

                # Found header indicating the colunm is Area
                # Get new dataframe where Area value is Yes
                # resulting dataframe is action_dataframe which consists of only records relevant to this area


                #process special case when Active is set to No
                if action == ActionDeactivate:
                    action_dataframe = df.loc[traffic_flows_dataframe[ActionActive] == 'No']
                    print(">>>>>>>>>>>>>deact")
                else:
                    action_dataframe = df.loc[traffic_flows_dataframe[action] == 'Yes']

                #logging.debug("=====> Found", len(action_dataframe['Reference']), "entries for area", header)
                # process this Area-specific dataframe and generate ACLs

                for index, row in action_dataframe.iterrows():
                        acl = clsTrafficFlowACL( \
                            build_acl( \
                                traffic_flows_dataframe.ix[index, ServiceColumnName], \
                                traffic_flows_dataframe.ix[index, ProtocolColumnName], \
                                traffic_flows_dataframe.ix[index, SourcePortColumnName], \
                                traffic_flows_dataframe.ix[index, SourceZoneColumnName], \
                                traffic_flows_dataframe.ix[index, SourceNetworkColumnName], \
                                traffic_flows_dataframe.ix[index, SourceNetworkMaskColumnName], \
                                traffic_flows_dataframe.ix[index, DestinationZoneColumnName], \
                                traffic_flows_dataframe.ix[index, DestinationNetworkColumnName], \
                                traffic_flows_dataframe.ix[index, DestinationNetworkMaskColumnName], \
                                traffic_flows_dataframe.ix[index, DestinationPortColumnName], action,
                            traffic_flows_dataframe.ix[index, DescriptionColumnName]), \
                            #traffic_flows_dataframe.ix[index, ServiceColumnName], \
                            #traffic_flows_dataframe.ix[index, ReferenceColumnName], \
                            #traffic_flows_dataframe.ix[index, QoSClassColumnName], \
                                action, \
                                traffic_flows_dataframe.ix[index, DescriptionColumnName], \
                            )

                        acl_list.append(acl)


    # --------------------------------------- 1. print ACLs ---------------------------------------
    # print full dataframe strings, don't cut them
    pd.set_option('display.max_colwidth', -1)

    # don't put remark statement in ACL if previous remark is the same
    last_remark = ""
    # we will make sure that the output directory exists
    if not os.path.exists(output_directory):
        os.mkdir(output_directory)
    for action in action_list:
        #print(action)
        with open(output_directory+ "/qos_output_area_"+ (action.replace(" ", "_")).lower()+".txt", 'w+') as out_file:
            # Generate separate ACLs for each area/scope
            action_banner = "\n!******************************* Action: " + action + " *******************************"
            # Only print this banner once - at the beginning
            print_action_banner = True

            traffic_class_object_list = []
            for qos_class in traffic_classes_list:
                #print(qos_class)
                traffic_class_acl_list = []
                for service in services_list:
                    service_banner = "\n!----------------------- SERVICE: " + service + " -----------------------\n"

                    for acl_record in acl_list:
                        # Go throught all ACLs and only print those matching current service and area
                        if (acl_record.QoSServiceName == service) and (acl_record.QoSACLScope == action) and (
                                acl_record.QoSClassName == qos_class):
                            if print_action_banner:
                                print(action_banner)
                                out_file.write(action_banner)
                                # don't print the banner next time
                                print_action_banner = False
                            if print_service_banner:
                                print(service_banner)
                                out_file.write(service_banner)
                                print_service_banner = False

                            # Print ACL remark if not alredy printed
                            remark = textwrap.wrap(acl_record.QoSACLDescription, RemarkLenght, break_long_words=False)
                            if not (last_remark == remark):
                                for line in remark:
                                  #  print("  remark", line)
                                    out_file.write(" remark "+ line + "\n")
                            last_remark = remark
                            if action == ActionActive:
                                # Print ACL itself
                                print("set", acl_record.QoSACL)
                                out_file.write("set"+ acl_record.QoSACL + "\n")
                            elif action == ActionDelete:
                                print("delete", acl_record.QoSACL)
                                out_file.write("delete"+ acl_record.QoSACL + "\n")
                            elif action == ActionDeactivate:
                                print("deactivate", acl_record.QoSACL)
                                out_file.write("delete"+ acl_record.QoSACL + "\n")
                            # Add ACL to the QoS Class
                           # traffic_class_acl_list.append(
                            #    acl_record.QoSACLScope.replace(" ", "_") + "_QoS_" + acl_record.QoSServiceName.replace(" ",
                          #                                                                                             "_") + "_Mark_ACL")
            #     # Get DSCP value for a class with name 'qos_class', such as Signalling, Gold, etc..
            #     dscp_mapping = \
            #         next((item for item in traffic_class_to_dscp_mapping_list if item["traffic_class_name"] == qos_class), None)[
            #             'traffic_class_dscp']
            #     logging.debug("=====> qos_class: " + qos_class + " , qos_dscp mapping: " + dscp_mapping)
            #
            #     # Build list of QoS class objects
            #     # Make the values in the list unique
            #     # https://stackoverflow.com/questions/12897374/get-unique-values-from-a-list-in-python
            #     traffic_class_acl_list = list(set(traffic_class_acl_list))
            #     traffic_class_object = clsQoSClass(qos_class, area, acl_record.QoSClassName.replace(" ", "_"),
            #                                    traffic_class_acl_list)
            #     traffic_class_object_list.append(traffic_class_object)
            #
            #
            # # --------------------------------------- 2. print classes ---------------------------------------
            # print_traffic_classes_banner = True
            # traffic_classes_banner = "\n!---------------------------- QoS Classes ----------------------------"
            #
            # for traffic_class_object_item in traffic_class_object_list:
            #     if not (traffic_class_object_item.QoSACLList == []):  # if the list of ACLs is not empty
            #         if print_traffic_classes_banner:
            #             print(traffic_classes_banner)
            #             out_file.write("\n" + traffic_classes_banner + "\n")
            #             # don't print the banner next time
            #             print_traffic_classes_banner = False
            #         print("class-map match-any " + traffic_class_object_item.QoSACLScope.replace(" ",
            #                                                                                  "_") + "_QoS_" + traffic_class_object_item.QoSClassName + "_Mark_Class")
            #         out_file.write("class-map match-any " + traffic_class_object_item.QoSACLScope.replace(" ",
            #                                                                                  "_") + "_QoS_" + traffic_class_object_item.QoSClassName + "_Mark_Class" + "\n")
            #         for qos_acl_object_item in traffic_class_object_item.QoSACLList:
            #             print(" match access-group name " + qos_acl_object_item)
            #             out_file.write(" match access-group name " + qos_acl_object_item + "\n")
            #
            #
            # # --------------------------------------- 3. print marking policies ---------------------------------------
            #
            # print_qos_policies_banner = True
            # qos_policies_banner = "\n!---------------------------- QoS Marking Policies ----------------------------"
            #
            # for traffic_class_object_item in traffic_class_object_list:
            #     if not (traffic_class_object_item.QoSACLList == []):  # if the list of ACLs is not empty
            #         if print_qos_policies_banner:
            #             print(qos_policies_banner)
            #             out_file.write(qos_policies_banner + "\n")
            #             print("policy-map", traffic_class_object_item.QoSACLScope.replace(" ", "_") + "_Reclassify_Traffic")
            #             out_file.write("policy-map" + traffic_class_object_item.QoSACLScope.replace(" ", "_") + "_Reclassify_Traffic" + "\n")
            #             # don't print the banner next time
            #             print_qos_policies_banner = False
            #
            #         print(" class " + traffic_class_object_item.QoSACLScope.replace(" ",
            #                                                                     "_") + "_QoS_" + traffic_class_object_item.QoSClassName + "_Mark_Class")
            #         out_file.write(" class " + traffic_class_object_item.QoSACLScope.replace(" ",
            #                                                                     "_") + "_QoS_" + traffic_class_object_item.QoSClassName + "_Mark_Class" + "\n")



if __name__ == '__main__':
    # argparse here 
    main()
