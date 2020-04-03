import ipaddress
import json

from constdefs import *


# --------------------------------------- Classes - ZoneClass ---------------------------------------
class ZoneClass:
    def __init__(self, zones_dataframe, SourceZone="", DestinationZone=""):
        self.SourceZones = []
        self.DestinationZones = []

        source_zones = zones_dataframe.loc[zones_dataframe[ZoneNameColumnName] == SourceZone][ZoneSetColumnName].items()

        destination_zones = zones_dataframe.loc[zones_dataframe[ZoneNameColumnName] == DestinationZone][
            ZoneSetColumnName
        ].items()

        for index, value in source_zones:
            self.SourceZones = list(value.replace(",", "").split(" "))

        for index, value in destination_zones:
            self.DestinationZones = list(value.replace(",", "").split(" "))


# --------------------------------------- Classes - ApplicationClass ---------------------------------------
class ApplicationClass:
    def __init__(self, standard_apps_dataframe, Protocol="", SourcePort="", DestinationPortList="", Description=""):

        self.SourcePort = SourcePort if SourcePort else ""
        self.DestinationPortLis = []

        dest_port_list = []

        for port_or_app in DestinationPortList:
            if port_or_app.isdigit():
                dest_port_list.append(
                    {
                        "Name": f"{Protocol.lower()}-{port_or_app}",
                        "Protocol": Protocol.lower(),
                        "DestinationPort": port_or_app,
                    }
                )
            elif "-" in port_or_app:
                dest_port_list.append(
                    {
                        "Name": f"{Protocol.lower()}-{port_or_app}",
                        "Protocol": Protocol.lower(),
                        "DestinationPort": port_or_app,
                    }
                )
            else:
                try:
                    app_protocol = standard_apps_dataframe.loc[
                        standard_apps_dataframe[ApplicationColumnName] == port_or_app
                        ][ApplicationProtocolColumnName].item()
                except ValueError as e:
                    print(f"Exception:{e}\n\n Exiting")
                    exit(1)

                if app_protocol == ("tcp" or "udp"):
                    dest_port = standard_apps_dataframe.loc[
                        standard_apps_dataframe[ApplicationColumnName] == port_or_app
                        ][ApplicationPortColumnName].item()
                else:
                    dest_port = ""

                dest_port_list.append(
                    {"Name": f"{app_protocol}-{dest_port}", "Protocol": app_protocol, "DestinationPort": dest_port}
                )
        self.DestinationPortList = dest_port_list

    # ----------------------------------------------------------------
    def check_standard_app(self, acl_app, standard_app_definitions):
        """
        Check if Application in ACL is already defined in Network OS
        :param acl_app: Application object to check
        :param standard_app_definitions:
        :return: if found - Standart application name, such as junos-bgp, or None if not found
        """

        if "-" not in str(acl_app["DestinationPort"]):
            for app in standard_app_definitions:
                if (
                        int(app["destination-port"]) == int(acl_app["DestinationPort"])
                        and app["protocol"] == acl_app["Protocol"]
                ):
                    return app["name"]
        return None

    # ----------------------------------------------------------------
    def convert_to_device_format(self, device_type):
        """
        Converts Application object to specific device config

        :param device_type: Network OS, such as junos
        :return: actual device config as a single string
        """

        result_string = ""
        if device_type == "junos":

            with open(junos_app_definitions, "r") as f:
                standard_app_definitions = json.load(f)

            # For every destination port in ACL check if a it's a standard application in device
            for item in self.DestinationPortList:

                app_name = self.check_standard_app(item, standard_app_definitions)

                if app_name:
                    item["Name"] = app_name
                else:
                    prefix = f"set applications application {item['Name']} protocol {item['Protocol']} destination-port {item['DestinationPort']}".lower()
                    result_string += "\n" + prefix

        return result_string.lower()


# --------------------------------------- Classes - AddressBookEntryClass ---------------------------------------


class AddressBookEntryClass:

    name = ""

    def __init__(
        self, address_book_dataframe, Name="", Description="", SourceNetwork="", DestinationNetwork="",
    ):

        address_book_dict = {}
        address_book_list = []

        # -------------- Parse SourceNetwork

        for address in SourceNetwork:
            try:
                if ipaddress.IPv4Network(address).is_global or ipaddress.IPv4Network(address).is_private:
                    address_book_list.append(
                        {"name": "net-" + address.replace("/", "_"), "value": address, "direction": "source"}
                    )
            except ValueError:
                if address == "any":
                    address_book_list = [{"name": "any", "value": "any", "direction": "source"}]
                else:
                    address_book_list.append(
                        {
                            "name": address,
                            "value": address_book_dataframe.loc[
                                address_book_dataframe[AddressBookEntryColumnName] == address
                            ][AddressBookNetworkColumnName].item(),
                            "direction": "source",
                        }
                    )

        # -------------- Parse DestinationNetwork
        for address in DestinationNetwork:
            try:
                if ipaddress.IPv4Network(address).is_global or ipaddress.IPv4Network(address).is_private:
                    address_book_list.append(
                        {"name": "net-" + address.replace("/", "_"), "value": address, "direction": "destination"}
                    )
            except ValueError:
                if address == "any":
                    address_book_list.append({"name": "any", "value": "any", "direction": "destination"})
                else:
                    address_book_list.append(
                        {
                            "name": address,
                            "value": address_book_dataframe.loc[
                                address_book_dataframe[AddressBookEntryColumnName] == address
                            ][AddressBookNetworkColumnName].item(),
                            "direction": "destination",
                        }
                    )

        address_book_dict["name"] = "addr_book_" + Name.lower().replace(" ", "_")
        address_book_dict["items"] = address_book_list

        self.Description = Description
        self.AddressBook = address_book_dict

    def convert_to_device_format(self, device_type):

        address_book_entry_command = []

        if device_type == "junos":
            for item in self.AddressBook["items"]:
                try:
                    if (
                        ipaddress.IPv4Network(item["value"]).is_global
                        or ipaddress.IPv4Network(item["value"]).is_private
                    ):
                        address_book_entry_command.append(
                            f"set security address-book global address " f"{item['name']} " f"{item['value']}"
                        )
                except ValueError:
                    if item["name"] != "any":
                        address_book_entry_command.append(
                            f"set security address-book global address " f"{item['name']} " f"dns-name {item['value']}"
                        )

        result_string = "\n".join(str(x) for x in address_book_entry_command)
        return result_string.lower()


class AccessRuleClass:

    """ ACL Object.
    """

    def __init__(
        self,
        Name="",
        Description="",
        Action="",
        Protocol="",
        SourcePort="",
        SourceZone="",
        SourceNetwork="",
        DestinationZone="",
        DestinationNetwork="",
        DestinationPort="",
        RuleAction="",
    ):
        """Return a ACL object, Initialize with empty values"""

        self.Name = Name
        self.Description = Description
        self.Action = Action
        self.SourceZone = SourceZone
        self.DestinationZone = DestinationZone
        self.RuleAction = RuleAction
        self.Protocol = Protocol

        self.SourceNetworkAndMask = []
        self.DestinationNetworkAndMask = []
        self.SourcePort = []
        self.DestinationPort = []

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

        # if Destination Network is "any" then Destination Network Mask should be empty
        if DestinationPort == "any":
            self.DestinationPort.append("any")
        else:
            destination_port_list = str(DestinationPort).replace(" ", "").split(",")
            for destination_port in destination_port_list:
                self.DestinationPort.append(destination_port)

    def convert_to_device_format(
        self, device_type, application_definition, address_book_definition, zones_definition,
    ):
        """

        :param device_type:
        :return:
        """

        source_address_book_entries = []
        destination_address_book_entries = []
        application_entries = []

        if device_type == "junos":

            if self.Action == ActionDelete:
                result_string = f"\ndelete security policies global" f" policy {self.Name.replace(' ', '_')} "
                return result_string.lower()

            elif self.Action == ActionDeactivate:
                result_string = f"\ndeactivate security policies global" f" policy {self.Name.replace(' ', '_')} "
                return result_string.lower()

            elif self.Action == ActionEnable:
                for item in address_book_definition.AddressBook["items"]:

                    if item["direction"] == "source":
                        source_address_book_entries.append(item["name"])
                    elif item["direction"] == "destination":
                        destination_address_book_entries.append(item["name"])

                for item in application_definition.DestinationPortList:
                    application_entries.append(item["Name"])

                result_string = (
                    f"set security policies global"
                    f" policy {self.Name.replace(' ', '_')} "
                    f' description "{self.Description}"'
                    f" match"
                    f" from-zone [{' '.join(zones_definition.SourceZones)}]"
                    f" to-zone [{' '.join(zones_definition.DestinationZones)}]"
                    f" source-address [{' '.join(str(x) for x in source_address_book_entries)}]"
                    f" destination-address [{' '.join(str(x) for x in destination_address_book_entries)}]"
                    f" application [{' '.join(str(x) for x in application_entries)}]"
                    f"\nset security policies global"
                    f" policy {self.Name.replace(' ', '_')}"
                    f" then {self.RuleAction}"
                    f"\nactivate security policies global"
                    f" policy {self.Name.replace(' ', '_')}"
                )

        elif device_type == "Cisco ASA":
            # placeholder
            return "Not yet implemented"
        else:
            return "Not yet implemented"

        return result_string.lower()
