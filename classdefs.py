from constdefs import *
# --------------------------------------- Define Classes to store data ---------------------------------------
class ApplicationClass:

    def __init__(self, Protocol="",SourcePort="", DestinationPort="", Description = "" ):
        """Return a ACL object, Initialize with empty values"""
        self.Name = f"{Protocol}_{DestinationPort}"
        self.Protocol = Protocol
        self.SourcePort = SourcePort
        self.DestinationPort = DestinationPort
        self.Description = Description

    def convert_to_device_format(self, device_type):
        if device_type == "JUNOS":

            prefix = f"set applications application {self.Name} protocol {self.Protocol}"
            source_port = f"" if self.SourcePort == "any" else f"{self.SourcePort}"
            destination_port = f" destination-port {self.DestinationPort}".lower()

            result_string = prefix + source_port + destination_port

        return result_string.lower()

    def get_app_name(self):
        return f"{self.Protocol}_{self.DestinationPort}".lower()

class AddressBookEntryClass:

    name = ""

    def __init__(self, Name = "",Description = "", SourceNetwork="", DestinationNetwork = ""):

        address_book_dict = {}
        address_book_list =[]

        if len(SourceNetwork) > 0 and SourceNetwork[0] != "any":
            for address in SourceNetwork:
                address_book_list.append({"name": address.replace("/","_"), "value": address, "direction":"source"})
        elif SourceNetwork[0] == "any":
            address_book_list = [{"name": "any", "value": "any", "direction":"source"}]
        else:
            address_book_list = [{"name": SourceNetwork[0].replace("/","_"), "value": SourceNetwork[0], "direction":"source"}]


        if len(DestinationNetwork) > 0 and DestinationNetwork[0] != "any":
            for address in DestinationNetwork:
                address_book_list.append({"name": address.replace("/","_"), "value": address, "direction":"destination"})
        elif DestinationNetwork[0] == "any":
            address_book_list.append({"name": "any", "value": "any", "direction":"destination"})
        else:
            address_book_list.append({"name": DestinationNetwork[0].replace("/","_"), "value": DestinationNetwork[0], "direction":"destination"})

        address_book_dict["name"] = "addr_book_"+ Name.lower().replace(" ","_")
        address_book_dict["items"] = address_book_list

        self.Description = Description
        self.AddressBook = address_book_dict

    def convert_to_device_format(self, device_type):

        address_book_entry_command = []

        if device_type == "JUNOS":
            for item in self.AddressBook["items"]:
                if item['name'] != "any":
                   address_book_entry_command.append(f"set security address-book global address "
                                                     f"{item['name']} "
                                                     f"{item['value']}")

        result_string = '\n'.join(str(x) for x in address_book_entry_command)
        return result_string.lower()

class AccessRuleClass:

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

        self.SourceNetworkAndMask = []
        self.DestinationNetworkAndMask = []

        #  if Source Network is "any" then Source Network Mask should be empty
        if SourceNetwork == "any":
            self.SourceNetworkAndMask.append("any")
        else:
            source_address_list = SourceNetwork.replace(" ", "").split(",")
            for source_address in source_address_list:
                self.SourceNetworkAndMask.append(source_address)

        # if Destination Network is "any" then Destination Network Mask should be empty
        if DestinationNetwork == "any":
            self.DestinationNetworkAndMask.append("any")
        else:
            destination_address_list = DestinationNetwork.replace(" ", "").split(",")
            for destination_address in destination_address_list:
                self.DestinationNetworkAndMask.append(destination_address)

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

    def convert_to_device_format(self, device_type, application_definition, address_book_definition):
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

            source_address_book_entries = []
            destination_address_book_entries = []

            if self.Action == ActionActive:
                for item in address_book_definition.AddressBook["items"]:
                    if item['direction'] == "source":
                        source_address_book_entries.append(item["name"])
                    elif item['direction'] == "destination":
                        destination_address_book_entries.append(item["name"])

                result_string = result_string + f" description \"{self.Description}\"" \
                        f" match source-address [{' '.join(str(x) for x in source_address_book_entries)}]" \
                        f" destination-address [{' '.join(str(x) for x in destination_address_book_entries)}]" \
                        f" application {application_definition.get_app_name()}" \
                        f"\nset security policies" \
                        f" from-zone {self.SourceZone}" \
                        f" to-zone {self.DestinationZone}" \
                        f" policy {(self.Name).replace(' ', '_')}" \
                        f" then permit" \
                        f"\nactivate security policies" \
                        f" from-zone {self.SourceZone}" \
                        f" to-zone {self.DestinationZone}" \
                        f" policy {(self.Name).replace(' ', '_')}"
                        # TODO - implement deny statement

        elif device_type == "Cisco ASA":
            # placeholder
            return ("Not yet implemented")
        else:
            return ("Not yet implemented")

        return result_string.lower()