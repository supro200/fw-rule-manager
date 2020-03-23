from constdefs import *
# --------------------------------------- Define Classes to store data ---------------------------------------
class Application:

    def __init__(self, Protocol="",SourcePort="", DestinationPort="", Description = "" ):
        """Return a ACL object, Initialize with empty values"""
        self.Name = f"{Protocol}_{DestinationPort}"
        self.Protocol = Protocol
        self.SourcePort = SourcePort
        self.DestinationPort = DestinationPort
        self.Description = Description

    def convert_to_device_format(self, device_type):
        if device_type == "JUNOS":
            # print(Protocol, SourcePort, DestinationPort, Description)
            # DestinationPort = str(DestinationPort).replace(" ", "_")
            # one_line = 'yes' if predicate(value) else 'no'

            prefix = f"set applications application {self.Name} protocol {self.Protocol}"
            source_port = f"" if self.SourcePort == "any" else f"{self.SourcePort}"
            destination_port = f" destination-port {self.DestinationPort}".lower()

            result_string = prefix + source_port + destination_port

        return result_string.lower()

    def get_app_name(self):
        return f"{self.Protocol}_{self.DestinationPort}".lower()

class clsAddressBookEntry:

    name = ""

    def __init__(self, Name="", Description = "", AddressRange = "" ):
        """Return a ACL object, Initialize with empty values"""
        self.name = Name
        self.Description = Description


class AccessRule:

    """ ACL Object.
    """

    def __init__(self, Name="", Description = "", Action="",Protocol="",
                 SourcePort="", SourceZone="", SourceNetwork="", SourceMaskLenth="",
                 DestinationZone="", DestinationNetwork = "",DestinationMaskLength="", DestinationPort=""):
        """Return a ACL object, Initialize with empty values"""

        self.Name = Name
        self.Description = Description
        self.Action = Action
        self.SourceZone = SourceZone
        self.DestinationZone = DestinationZone

        #  if Source Network is "any" then Source Network Mask should be empty
        if SourceNetwork == "any":
            self.SourceNetworkAndMask = " any"
        else:
            self.SourceNetworkAndMask = " " + SourceNetwork + "/" + str(SourceMaskLenth)

        # if Destination Network is "any" then Destination Network Mask should be empty
        if DestinationNetwork == "any":
            self.DestinationNetworkAndMask = " any"
        else:
            self.DestinationNetworkAndMask = " " + DestinationNetwork + "/" + str(DestinationMaskLength)

        # check if Destination Port is a range or a single port
        if "-" in str(DestinationPort):
            self.DestinationPort = str(DestinationPort).replace("-", " ")
            DestinationPortCondition = " range "
        elif (DestinationPort == "n/a") or (DestinationPort == "") or (DestinationPort == "any"):
            self.DestinationPort = ""
            DestinationPortCondition = ""
        else:
            self.DestinationPort = DestinationPort
            DestinationPortCondition = " eq "

        if Protocol == "any":
            self.Protocol = "ip"
            self.SourcePort = ""
            SourcePortCondition = ""
            self.DestinationPort = ""
            SourceNetworkMask = ""
            DestinationPortCondition = ""
        else:
            self.Protocol = Protocol
            self.SourcePort = SourcePort

    def convert_to_device_format(self, device_type, application_definition):
        """

        :param device_type:
        :return:
        """

        if device_type == "JUNOS":
            if self.Action == ActionActive:
                action_to_device_command = "set"
            elif self.Action == ActionDelete:
                action_to_device_command = "delete"
            elif self.Action == ActionDeactivate:
                action_to_device_command = "deactivate"

            result_string = f"{action_to_device_command} security policies" \
                        f" from-zone {self.SourceZone}" \
                        f" to-zone {self.DestinationZone}" \
                        f" policy {(self.Name).replace(' ', '_')}"
            if self.Action == ActionActive:
                result_string = result_string + \
                        f" description \"{self.Description}\"" \
                        f" match source-address {self.SourceNetworkAndMask}" \
                        f" destination-address {self.DestinationNetworkAndMask}" \
                        f" application {application_definition.get_app_name()}"

        return(result_string)