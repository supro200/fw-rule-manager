import getpass
import os

from netmiko import ConnectHandler, NetMikoTimeoutException
from paramiko import AuthenticationException
from colorama import init, Fore, Style  # colored screen output


def connect_to_fw_validate_config(config, device):

    try:
        device["password"] = os.environ["FW_MAN_PASSWORD"]
    except KeyError:
        device["password"] = getpass.getpass()

    print("------------ Deploying configuration --------------")

    try:
        net_connect = ConnectHandler(**device)
    except AuthenticationException as e:
        print("Authentication failed.")
        exit(1)
    except NetMikoTimeoutException:
        print("Timeout error occured.")
        exit(1)

    # net_connect.session_preparation()
    # net_connect.enable()

    config_commands = config.splitlines()

    test_config_commands = [
        "set security zones security-zone test-segment2",
        "set applications application tcp_22 protocol tcp destination-port 22",
        "set applications application tcp_50410 protocol tcp destination-port 50410",
        "set security address-book global address azure-aus-redhat01 10.248.59.21/32",
        "set security address-book global address net-10.1.2.0_24 10.1.2.0/24",
        "set security address-book global address aueafrmnprxy01 10.248.57.50/32",
        "set security address-book global address net-10.64.0.0_16 10.64.0.0/16",
        "set security address-book global address net-10.5.0.0_28 10.5.0.0/28",
        'set security policies global policy digital_media_content description "interact application client to server" match from-zone dmz1 to-zone internal-management source-address net-10.1.2.0_24 destination-address net-10.5.0.0_28 application tcp_50410',
        "set security policies global policy digital_media_content then permit",
        "activate security policies global policy digital_media_content",
    ]
    config_commands = config.splitlines()
    # print("Deploying config:", config_commands)

    net_connect.send_config_set(config_commands, exit_config_mode=False, cmd_verify=False)

    # for command in config_commands:
    #     print("sending", command)
    #     try:
    #         net_connect.send_config_set(command, exit_config_mode=False, cmd_verify=False)
    #     except NetMikoTimeoutException:
    #         print('Timeout error occured.')
    #         print(f"Failed to push command: {command} \n Exception: {e}")
    #     except Exception as e:
    #         print(f"Failed to push command: {command} \n Exception: {e}")
    #         exit(1)

    print("Done\n")

    print("------------ Validating configuration --------------")
    commit_check_commands = ["commit check"]
    commit_check = net_connect.send_config_set(commit_check_commands, exit_config_mode=False)
    # sleep(5)
    print(commit_check, "\n\n")

    if "succeeds" in commit_check:
        print(Fore.GREEN + "----------- Success ----------- ")
        #print(Style.RESET_ALL)
        show_compare_commands = "show | compare"
        show_compare = net_connect.send_config_set(show_compare_commands, exit_config_mode=False)
        #     sleep(5)
        print(show_compare)

        # Rollback anyway to previous clean state
        # print("------------ Validation failed - Rollback -----------")
        rollback = net_connect.send_command("rollback 0")
        # print (rollback)

    #    commit = net_connect.send_command("commit and-quit")
    #    print (commit)
    #    print ("configuration saved on " + device)
    #    f = open('configured/configured.txt', 'a+')
    #    f.write(device +' has been configured \n')
    #    f.close()
    else:
        print(Fore.RED + "------------ Validation failed - Rollback -----------")
        #print(Style.RESET_ALL)
        rollback = net_connect.send_command("rollback 0")
        print(rollback)
        # print ("the following device " + device + " had a commit error and has been rolled back")
        # f = open('failed/commit_error.txt', 'a')
        # f.write('Commit check failed for ' + device + '\n')
        # f.close()

    print("\n")
    print(80 * "-")

