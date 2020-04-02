import argparse
import logging
import sys
import warnings
from datetime import datetime
from pathlib import Path  # OS-agnostic file handling

from colorama import init, Fore  # colored screen output

from constdefs import *
from data_handlers import load_source, parse_flows_dataframes, generate_config
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


# -------------------------------------------------------------------------------------------


def parse_args(args=sys.argv[1:]):
    """Parse arguments."""
    parser = CustomParser()
    parser._action_groups.pop()
    # placeholder for required arguments
    # required = parser.add_argument_group("required arguments")
    optional = parser.add_argument_group("optional arguments")
    optional.add_argument(
        "--validate", default=False, required=False, action="store_true", help="Validate with the live device",
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
        "--source_filename", "--source", help="File to parse",
    )
    optional.add_argument(
        "--network-os", "--network_os", help="Network OS to generate the config for",
    )
    return parser.parse_args(args)


def main():
    # init colorama
    init(autoreset=True)

    # Check CLI arguments
    options = parse_args()

    source_filename = options.source_filename if options.source_filename else test_filename
    network_os = options.network_os if options.network_os else "junos"

    # 1. parse Excel into dataframes
    traffic_flows_dataframe, address_book_dataframe, zones_dataframe, standard_apps_dataframe = load_source(
        source_filename
    )

    # 2. Get list of Firewall Rules and actions
    acl_list, action_list = parse_flows_dataframes(traffic_flows_dataframe)

    # 3. Generate config for a given network OS
    config = generate_config(
        acl_list, action_list, address_book_dataframe, zones_dataframe, standard_apps_dataframe, network_os
    )

    if config:
        print(Fore.GREEN + f"--------------- Config parsed and saved to a file -------------------")

        file_name = f"{output_dir}{network_os}-{datetime.now().strftime('%Y-%m-%d')}.txt".lower()
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        with open(file_name, "w") as f:
            f.write(config)
        print("\nConfig saved as: " + str(Path(file_name).resolve()))

    if options.screen_output:
        print(Fore.GREEN + "\n------------------- Firewall configuration below --------------------")
        print(config)

    if options.validate:
        connect_to_fw_validate_config(config, virtual_srx)


if __name__ == "__main__":
    main()
