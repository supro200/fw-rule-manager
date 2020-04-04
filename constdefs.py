#  -------------  Define Column Names -------------

ProtocolColumnName = "Protocol"
SourceNetworkColumnName = "Source Network"
SourcePortColumnName = "Source Port"
DestinationNetworkColumnName = "Destination Network"
DestinationPortColumnName = "Destination Port or Application"
ReferenceColumnName = "Reference"
RuleColumnName = "Rule Name"
DescriptionColumnName = "Description"
SourceZoneColumnName = "Source Zone"
DestinationZoneColumnName = "Destination Zone"
RuleActionColumnName = "Action"
ZoneNameColumnName = "Zone Name"
ZoneSetColumnName = "Zone Set"

AddressBookEntryColumnName = "Object Name"
AddressBookNetworkColumnName = "Network"

ApplicationColumnName = "Application"
ApplicationProtocolColumnName = "Protocol"
ApplicationPortColumnName = "Port"

DrodDownFieldNonStandartProtocol = "Other"

test_filename = "fw_rules_test_02.xlsx"

traffic_flows_sheet_name = "Traffic Flows"
address_book_sheet_name = "Address Book"
standard_apps_sheet_name = "Applications"
zones_sheet_name = "Zones"

dropdown_fields_sheet_name = "Dropdown Fields"
output_dir = "output/"

ActionEnable = "Enable"
ActionDeactivate = "Deactivate"
ActionDelete = "Delete"

virtual_srx = {
    "device_type": "juniper",
    "host": "10.27.40.180",
    "username": "alex",
    "password": "",
    "port": 22,
    "verbose": "True",
}
junos_app_definitions = "junos-standard-apps.json"
