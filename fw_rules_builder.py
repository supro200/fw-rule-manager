import pandas as pd
import numpy as np
import textwrap
import logging
import os
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
DSCPColumnName = "DSCP"
DestinationNetworkColumnName = "Destination Network"
DestinationNetworkMaskColumnName = "Destination Mask Length"
DestinationPortColumnName = "Destination Port"
ReferenceColumnName = "Reference"
ServiceColumnName = "Service"
DescriptionColumnName = "Description"

QoSClassColumnDropDownName = "QoS Class Name"
QoSClassColumnDropDownDSCPName = "Target DSCP"

QoSClassColumnName = "QoS Class"
ResultSheetName = "Result"

# Max length of remark statement in ACL
RemarkLenght = 90

filename = "qos_master.xlsx"
qos_flows_sheet_name = "QoS Flows"
dropdown_fields_sheet_name = "Dropdown Fields"


# --------------------------------------- Define Classes to store data ---------------------------------------

class clsQoSACL:
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


class clsQoSClass:
    def __init__(self, QoSClassName="", QoSACLScope="", QoSACLPriority="", QoSACLList=[], QoSDSCPMarking=""):
        """Return a QoS Class object, Initialize with empty values"""
        self.QoSClassName = QoSClassName
        self.QoSACLScope = QoSACLScope
        self.QoSDSCPMarking = QoSDSCPMarking
        self.QoSACLPriority = QoSACLPriority
        self.QoSACLList = QoSACLList

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


# --------------------------------------- Define Procedures ---------------------------------------
def build_ACL(Protocol, SourceNetwork, SourceMaskLenth, SourcePort, DSCP, DestinationNetwork,
              DestinationMaskLength, DestinationPort):

    #  if Source Network is "any" then Source Network Mask should be empty
    if SourceNetwork == "any":
        SourceNetworkAndMask = " any"
        SourceNXOSNetworkMask = ""
    elif SourceMaskLenth == 32:
        SourceNetworkAndMask = " host " + SourceNetwork
    else:
        SourceNetworkAndMask = " " + SourceNetwork + " " + calcDottedWildcard(SourceMaskLenth)
        SourceNXOSNetworkMask = calcDottedNetmask(SourceMaskLenth)

    # if Destination Network is "any" then Destination Network Mask should be empty
    if DestinationNetwork == "any":
        DestinationNetworkAndMask = " any"
        DestinationNXOSNetworkMask = ""
    elif DestinationMaskLength == 32:
        DestinationNetworkAndMask = " host " + DestinationNetwork
    else:
        DestinationNetworkAndMask = " " + DestinationNetwork + " " + calcDottedWildcard(DestinationMaskLength)
        DestinationNXOSNetworkMask = calcDottedNetmask(DestinationMaskLength)

    # check if Source Port is a range or a single port
    if "-" in str(SourcePort):
        SourcePort = str(SourcePort).replace("-", " ")
        SourcePortCondition = " range "
    elif (SourcePort == "n/a") or (SourcePort == "") or (SourcePort == "any"):
        SourcePort = ""
        SourcePortCondition = ""
    else:
        SourcePortCondition = " eq "

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

    if DSCP != "":
        DSCP = " dscp " + DSCP

    if Protocol == "any":
        Protocol = "ip"
        SourcePort = ""
        SourcePortCondition = ""
        DestinationPort = ""
        SourceNetworkMask = ""
        DestinationPortCondition = ""

    # build a ACL
    resultACL = "permit" + " " + \
                Protocol + \
                SourceNetworkAndMask + \
                SourcePortCondition + \
                str(SourcePort) + \
                DestinationNetworkAndMask + \
                DestinationPortCondition + \
                str(DestinationPort) + \
                DSCP

    logging.debug(resultACL.lower())

    return resultACL.lower()


def main():
    #  -------------------------------- Load data from Excel spreadsheet--------------------------
    # --------------------------------------------------------------------------------------------
    # Load data from QoS Flows Sheet into dataframe
    xl = pd.ExcelFile(filename)
    logging.debug("=====> sheet_names: ", xl.sheet_names)
    # Load data from QoS Flows Tab into dataframe
    df = xl.parse(qos_flows_sheet_name)
    # Replace empty values with empty stings to avoid errors in processing data as strings
    qos_flows_dataframe = df.replace(np.nan, '', regex=True)
    print("Total records found in " + qos_flows_sheet_name + " sheet: " + str(len(qos_flows_dataframe['Reference'])))

    # ------------------------------------------------------------------------------------
    # Load data from Dropdown Fields Tab into dataframe - this is for matching QoS Class to DSCP, for example
    temp_df1 = xl.parse(dropdown_fields_sheet_name)
    # Replace empty values with empty stings to avoid errors in processing data as strings
    dropdown_fields_dataframe = temp_df1.replace(np.nan, '', regex=True)

    qos_class_to_dscp_mapping_list = []

    for index, row in dropdown_fields_dataframe.iterrows():
        if not (dropdown_fields_dataframe.ix[index, "QoS Class Name"] == ""):
            qos_class_to_dscp_mapping_dict = {
                "qos_class_name": dropdown_fields_dataframe.ix[index, "QoS Class Name"],
                "qos_class_dscp": dropdown_fields_dataframe.ix[index, "Target DSCP"]
            }
            qos_class_to_dscp_mapping_list.append(qos_class_to_dscp_mapping_dict)

    logging.debug("Found Classes to DCP mapping:")
    for item in qos_class_to_dscp_mapping_list:
        logging.debug(item)

    # --------------------- Parse Services ---------------------
    # Get a list of unique services - this will be used for grouping records into ACLs
    services_list = np.unique(np.array(qos_flows_dataframe["Service"]))

    # Convert list to string for correct logging output
    # https://stackoverflow.com/questions/44778/how-would-you-make-a-comma-separated-string-from-a-list-of-strings
    logging.debug("=====> service_list: " + ','.join(services_list))

    # --------------------- Parse QoS classes ---------------------
    # Get a list of unique services - this will be used for grouping records into ACLs
    qos_classes_list = np.unique(np.array(qos_flows_dataframe["QoS Class"]))

    # Convert list to string for correct logging output
    # https://stackoverflow.com/questions/44778/how-would-you-make-a-comma-separated-string-from-a-list-of-strings
    logging.info("=====> qos_classes_list: " + ','.join(qos_classes_list))
    # --------------------- Parse Areas/Scopes ---------------------
    # Areas/Scopes, such as Access, M2M, Datacentre, Cloud, etc.
    area_list = []

    # Get Headers from the dataframe
    headers_list = list(qos_flows_dataframe.columns.values)
    # Search headers with 'Area' word and cut off first word 'Area' and last word which should be 'Return' or 'Entry'
    # Result is an unique list of areas in area_list[]
    for header in headers_list:
        if "Area" in header:
            temp_str = header.split(' ', 1)[1]
            area_list.append(' '.join(temp_str.split(' ')[:-1]))

    # Make the values in the list unique
    # https://stackoverflow.com/questions/12897374/get-unique-values-from-a-list-in-python
    area_list = list(set(area_list))
    logging.debug("=====> area_list: " + ','.join(area_list))

    # --------------------------------------- Process dataframe ---------------------------------------

    # List of objects of class QosACL
    acl_list = []
    # Search for Areas/Scopes and for each row generate separate ACL for every Area
    # headers_list - all dataframe headers
    # area_list - all Areas/Scopes
    for header in headers_list:
        for area in area_list:
            if area in header:
                # Found header indicating the colunm is Area
                # Get new dataframe where Area value is Yes
                # resulting dataframe is area_dataframe which consists of only records relevant to this area
                area_dataframe = df.loc[qos_flows_dataframe[header] == 'Yes']
                logging.debug("=====> Found", len(area_dataframe['Reference']), "entries for area", header)
                # process this Area-specific dataframe and generate ACLs
                for index, row in area_dataframe.iterrows():
                    # If the record indicates it is return traffic, swap destination and source IP, mask and port
                    if "Return" in header:
                        acl = clsQoSACL( \
                            build_ACL( \
                                qos_flows_dataframe.ix[index, ProtocolColumnName], \
                                qos_flows_dataframe.ix[index, DestinationNetworkColumnName], \
                                qos_flows_dataframe.ix[index, DestinationNetworkMaskColumnName], \
                                qos_flows_dataframe.ix[index, DestinationPortColumnName], \
                                qos_flows_dataframe.ix[index, DSCPColumnName], \
                                qos_flows_dataframe.ix[index, SourceNetworkColumnName], \
                                qos_flows_dataframe.ix[index, SourceNetworkMaskColumnName], \
                                qos_flows_dataframe.ix[index, SourcePortColumnName]), \
                            qos_flows_dataframe.ix[index, ServiceColumnName], \
                            qos_flows_dataframe.ix[index, ReferenceColumnName], \
                            qos_flows_dataframe.ix[index, QoSClassColumnName], \
                            area, \
                            qos_flows_dataframe.ix[index, DescriptionColumnName], \
                            )
                    else:
                        acl = clsQoSACL( \
                            build_ACL( \
                                qos_flows_dataframe.ix[index, ProtocolColumnName], \
                                qos_flows_dataframe.ix[index, SourceNetworkColumnName], \
                                qos_flows_dataframe.ix[index, SourceNetworkMaskColumnName], \
                                qos_flows_dataframe.ix[index, SourcePortColumnName], \
                                qos_flows_dataframe.ix[index, DSCPColumnName], \
                                qos_flows_dataframe.ix[index, DestinationNetworkColumnName], \
                                qos_flows_dataframe.ix[index, DestinationNetworkMaskColumnName], \
                                qos_flows_dataframe.ix[index, DestinationPortColumnName]), \
                            qos_flows_dataframe.ix[index, ServiceColumnName], \
                            qos_flows_dataframe.ix[index, ReferenceColumnName], \
                            qos_flows_dataframe.ix[index, QoSClassColumnName], \
                            area, \
                            qos_flows_dataframe.ix[index, DescriptionColumnName], \
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
    for area in area_list:
        with open(output_directory+ "/qos_output_area_"+ (area.replace(" ", "_")).lower()+".txt", 'w+') as out_file:
            # Generate separate ACLs for each area/scope
            area_banner = "\n!******************************* AREA: " + area + " *******************************"
            # Only print this banner once - at the beginning
            print_area_banner = True

            qos_class_object_list = []
            for qos_class in qos_classes_list:
                qos_class_acl_list = []
                for service in services_list:
                    service_banner = "\n!----------------------- SERVICE: " + service + " -----------------------\n"
                    print_service_banner = True
                    acl_header = "ip access-list extended " + area.replace(" ", "_") + "_QoS_" + service.replace(" ",
                                                                                                                 "_") + "_Mark_ACL"

                    for acl_record in acl_list:
                        # Go throught all ACLs and only print those matching current service and area
                        if (acl_record.QoSServiceName == service) and (acl_record.QoSACLScope == area) and (
                                acl_record.QoSClassName == qos_class):
                            if print_area_banner:
                                print(area_banner)
                                out_file.write(area_banner)
                                # don't print the banner next time
                                print_area_banner = False
                            if print_service_banner:
                                print(service_banner)
                                out_file.write(service_banner)
                                print(acl_header)
                                out_file.write(acl_header + "\n")
                                print_service_banner = False

                            # Print ACL remark if not alredy printed
                            remark = textwrap.wrap(acl_record.QoSACLDescription, RemarkLenght, break_long_words=False)
                            if not (last_remark == remark):
                                for line in remark:
                                    print("  remark", line)
                                    out_file.write(" remark "+ line + "\n")
                            last_remark = remark

                            # Print ACL itself
                            print(" ", acl_record.QoSACL)
                            out_file.write(" "+ acl_record.QoSACL + "\n")
                            # Add ACL to the QoS Class
                            qos_class_acl_list.append(
                                acl_record.QoSACLScope.replace(" ", "_") + "_QoS_" + acl_record.QoSServiceName.replace(" ",
                                                                                                                       "_") + "_Mark_ACL")
                # Get DSCP value for a class with name 'qos_class', such as Signalling, Gold, etc..
                dscp_mapping = \
                    next((item for item in qos_class_to_dscp_mapping_list if item["qos_class_name"] == qos_class), None)[
                        'qos_class_dscp']
                logging.debug("=====> qos_class: " + qos_class + " , qos_dscp mapping: " + dscp_mapping)

                # Build list of QoS class objects
                # Make the values in the list unique
                # https://stackoverflow.com/questions/12897374/get-unique-values-from-a-list-in-python
                qos_class_acl_list = list(set(qos_class_acl_list))
                qos_class_object = clsQoSClass(qos_class, area, acl_record.QoSClassName.replace(" ", "_"),
                                               qos_class_acl_list, dscp_mapping)
                qos_class_object_list.append(qos_class_object)


            # --------------------------------------- 2. print classes ---------------------------------------
            print_qos_classes_banner = True
            qos_classes_banner = "\n!---------------------------- QoS Classes ----------------------------"

            for qos_class_object_item in qos_class_object_list:
                if not (qos_class_object_item.QoSACLList == []):  # if the list of ACLs is not empty
                    if print_qos_classes_banner:
                        print(qos_classes_banner)
                        out_file.write("\n" + qos_classes_banner + "\n")
                        # don't print the banner next time
                        print_qos_classes_banner = False
                    print("class-map match-any " + qos_class_object_item.QoSACLScope.replace(" ",
                                                                                             "_") + "_QoS_" + qos_class_object_item.QoSClassName + "_Mark_Class")
                    out_file.write("class-map match-any " + qos_class_object_item.QoSACLScope.replace(" ",
                                                                                             "_") + "_QoS_" + qos_class_object_item.QoSClassName + "_Mark_Class" + "\n")
                    for qos_acl_object_item in qos_class_object_item.QoSACLList:
                        print(" match access-group name " + qos_acl_object_item)
                        out_file.write(" match access-group name " + qos_acl_object_item + "\n")


            # --------------------------------------- 3. print marking policies ---------------------------------------

            print_qos_policies_banner = True
            qos_policies_banner = "\n!---------------------------- QoS Marking Policies ----------------------------"

            for qos_class_object_item in qos_class_object_list:
                if not (qos_class_object_item.QoSACLList == []):  # if the list of ACLs is not empty
                    if print_qos_policies_banner:
                        print(qos_policies_banner)
                        out_file.write(qos_policies_banner + "\n")
                        print("policy-map", qos_class_object_item.QoSACLScope.replace(" ", "_") + "_Reclassify_Traffic")
                        out_file.write("policy-map" + qos_class_object_item.QoSACLScope.replace(" ", "_") + "_Reclassify_Traffic" + "\n")
                        # don't print the banner next time
                        print_qos_policies_banner = False

                    print(" class " + qos_class_object_item.QoSACLScope.replace(" ",
                                                                                "_") + "_QoS_" + qos_class_object_item.QoSClassName + "_Mark_Class")
                    out_file.write(" class " + qos_class_object_item.QoSACLScope.replace(" ",
                                                                                "_") + "_QoS_" + qos_class_object_item.QoSClassName + "_Mark_Class" + "\n")
                    print("  set dscp " + qos_class_object_item.QoSDSCPMarking)
                    out_file.write("  set dscp " + qos_class_object_item.QoSDSCPMarking + "\n")


if __name__ == '__main__':
    # argparse here 
    main()
