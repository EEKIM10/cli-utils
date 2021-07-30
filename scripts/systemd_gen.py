#!/usr/bin/env python3
import argparse
import sys
import os
try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.syntax import Syntax
    console = Console()
except ImportError:
    print("Rich is not installed. Please install rich.", file=sys.stderr)
    sys.exit(4)


if os.geteuid() != 0:
    try:
        from elevate import elevate
        console.log("[gray italics]Attempting to elevate program permissions...[/]")
        elevate()
    except ImportError:
        elevate = None
        console.log(
            r"[yellow]\[Warning\][/] Program is not running as root!"
            r" This will be unable to write your configuration files, only print them."
        )

if __name__ == "__main__":
    types = ["simple", "exec", "forking", "oneshot", "dbus", "notify", "idle"]
    restart_on = ["always", "on-failure", "on-success", "on-abnormal", "on-abort", "on-watchdog", "no"]

    parser = argparse.ArgumentParser(description="Simple tool to assist with generation of systemd services.")
    parser.add_argument(
        "--interactive",
        "-I",
        action="store_true",
        help="Whether to do this interactively. Defaults to true.",
        default=None,
    )
    parser.add_argument(
        "--description",
        "-D",
        action="store",
        help="The description of the service.",
        required=False,
        default="Automatically generated service via systemd-gen.py",
    )
    parser.add_argument(
        "--type",
        "-T",
        action="store",
        choices=types,
        help="The type of service. See https://www.freedesktop.org/software/systemd/man/systemd.service.html for more"
        " detail.",
        required=False,
        default="simple",
    )
    parser.add_argument(
        "--remain-after-exit",
        "-R",
        action="store_true",
        required=False,
        default=False,
        help="Whether to consider the service alive if all the processes are dead.",
    )
    parser.add_argument(
        "--exec-path",
        "--exec-start",
        "--path",
        "--start",
        "--exec",
        "-E",
        action="store",
        required=False,
        default=None,
        help="The command to actually run.",
    )
    parser.add_argument("--name", "-N", action="store", required=False, default=None, help="The name of the service.")

    args = parser.parse_args()

    if args.interactive in [True, None]:
        name = input("Please enter a name for this service: ")
        description = input("Please enter a description of this service:\n")
        _type = Prompt.ask(f"What type is this service?", choices=types).lower().strip()
        remain_after_exit = Confirm.ask(
            "Should this service be considered offline when all of its processes are exited?", default=True
        )
        restart_on_death = Confirm.ask("Should this service be automatically restarted on death?", default=False)
        max_restarts = int(input("If enabled, how many times can this service restart before systemd gives up? "))
        exec_path = input(
            "What command should this service run? (e.g. /usr/local/opt/python-3.9.0/bin/python3.9 /root/" "thing.py)\n"
        )
    else:
        name = args.name
        description = args.description
        _type = args.type
        remain_after_exit = args.remain_after_exit
        exec_path = args.exec_path
        restart_on_death = True
        max_restarts = 10

    console.log("Generating file...")
    content = """
[Unit]
Description={}
StartLimitBurst={}

[Service]
Type={}
RemainAfterExit={}
ExecStart={}
Restart={}
RestartSec=5s

[Install]
WantedBy=multi-user.target
    """
    content = content.format(
        description,
        str(max_restarts),
        _type,
        "yes" if remain_after_exit else "no",
        exec_path,
        "always" if restart_on_death else "no",
    )

    console.log("===== BEGIN CONFIGURATION FILE =====")
    console.log(Syntax(content, "toml"))
    console.log("=====  END CONFIGURATION FILE  =====")
    if Confirm.ask("Does this configuration look right?"):
        try:
            with open("/etc/systemd/system/{}.service".format(name), "w+") as wfile:
                console.log("[gray italics]Writing file...[/]")
                written = wfile.write(content)
                console.log(f"[gray italics]Wrote {written} bytes to `/etc/systemd/system/{name}.service`.")
        except PermissionError as e:
            console.print_exception()
            print("Unable to write configuration file. Try sudo.")
            sys.exit(1)
        else:
            print("Finished writing configuration file.\nTo start the service, run `sudo service {name} start`.")
            sys.exit()
    else:
        print("Ok, cancelled.")
        console.log("[red dim italics]User cancelled[/]")
        sys.exit(2)