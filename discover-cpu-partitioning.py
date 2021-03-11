#!/usr/bin/python3

import argparse
import copy
import re
from pathlib import Path
from system_cpu_topology import *

# define some global variables
class t_global(object):
    args = None

def debug(log_msg):
    return(print("DEBUG: %s" % (log_msg)))

def error(log_msg):
    return(print("ERROR: %s" % (log_msg)))

def process_options():
    parser = argparse.ArgumentParser(description="Discover CPU Partitioning configuration (if any)")

    parser.add_argument("--debug",
                        dest = "debug",
                        help = "Turn on debug output",
                        action = "store_true")

    parser.add_argument("--environment",
                        dest = "environment",
                        help = "What runtime environment is this expected to be.",
                        default = "process",
                        choices = [ "container", "process" ])

    t_global.args = parser.parse_args()

    return(0)

def get_rcu_nocbs():
    kernel_cli = ''
    rcu_nocbs = []

    input_file = '/proc/cmdline'

    path = Path(input_file)
    if path.exists() and path.is_file():
        with path.open() as fh:
            kernel_cli = fh.readline().rstrip()
            if t_global.args.debug:
                debug("get_rcu_nocbs: kernel_cli: %s" % (kernel_cli))

            # find 'rcu_nocbs=<cpu-list>' if it exists in the kernel command line
            match = re.search(r"rcu_nocbs=[0-9\-,]+", kernel_cli)
            if match:
                partition = match.group(0).partition('=')
                if partition[1] == partition[2] == '':
                    # this implies that 'rcu_nocbs' exists in the
                    # kernel command line but without a <cpu-list>
                    pass
                else:
                    if t_global.args.debug:
                        debug("get_rcu_nocbs: found rcu_nocbs=%s" % (partition[2]))
                    rcu_nocbs = system_cpu_topology.parse_cpu_list(partition[2])
    else:
        raise FileNotFoundError("get_rcu_nocbs: Could not find '%s'" % (input_file))

    return(rcu_nocbs)

def get_pid_cpus_allowed(pid):
    path = Path('/proc/' + pid + '/status')
    cpus_allowed = []

    if path.exists() and path.is_file():
        with path.open() as fh:
            contents = fh.readlines()
            for line in contents:
                match = re.search(r"Cpus_allowed_list", line)
                if match:
                    line = line.rstrip()
                    if t_global.args.debug:
                        debug("get_pid_cpus_allowed: found '%s'" % (line))
                    pieces = line.split()
                    if len(pieces) != 2:
                        raise AttributeError("get_pid_cpus_allowed: Could not extract cpus_allowed from '%s'" % (line))
                    else:
                        cpus_allowed = system_cpu_topology.parse_cpu_list(pieces[1])
                        if t_global.args.debug:
                            debug("get_pid_cpus_allowed: extracted cpus_allowed=%s" % (cpus_allowed))
    else:
        raise FileNotFoundError("get_pid_cpus_allowed: Requested pid '%s' probably does not exist" % (pid))

    if len(cpus_allowed) == 0:
        raise AttributeError("get_pid_cpus_allowed: failed to determine cpus_allowed")

    return(cpus_allowed)

def output_cpu_info(label, cpu_list):
    if t_global.args.debug:
        debug("%s cpus: %d" % (label, len(cpu_list)))
        short_cpu_list = system_cpu_topology.formatted_cpu_list(cpu_list)
        formatted_short_cpu_list = ','.join(short_cpu_list)
        debug("%s cpus: %s" % (label, formatted_short_cpu_list))

    cpu_list = ','.join(map(str, cpu_list))
    print("%s cpus: %s" % (label, cpu_list))

    print("")

    return(0)

def main():
    process_options()

    if t_global.args.environment == "process":
        system_cpus = system_cpu_topology(debug = t_global.args.debug)

        all_cpus = system_cpus.get_all_cpus()
        output_cpu_info("all", all_cpus)

        online_cpus = system_cpus.get_online_cpus()
        output_cpu_info("online", online_cpus)

        rcu_nocbs_cpus = get_rcu_nocbs()
        output_cpu_info("rcu_nocbs", rcu_nocbs_cpus)

        odd_list = list(set(rcu_nocbs_cpus) - set(online_cpus))
        if len(odd_list) > 0:
            print("this is odd, rcu_nocbs contains cpus that are not online: %s" % (odd_list))

        housekeeping_cpus = list(set(online_cpus) - set(rcu_nocbs_cpus))
        if len(housekeeping_cpus) == 0:
            print("this is odd, there are no housekeeping cpus")
        else:
            output_cpu_info("housekeeping", housekeeping_cpus)

            output_cpu_info("isolated", rcu_nocbs_cpus)
    elif t_global.args.environment == "container":
        system_cpus = system_cpu_topology(debug = t_global.args.debug)

        all_cpus = system_cpus.get_all_cpus()
        output_cpu_info("all", all_cpus)

        online_cpus = system_cpus.get_online_cpus()
        output_cpu_info("online", online_cpus)

        try:
            cpus_allowed = get_pid_cpus_allowed('self')
        except Exception as e:
            print(e)
            return(1)

        housekeeping_cpus = []
        isolated_cpus = []
        if len(cpus_allowed) == 1:
            print("this is odd, there really needs to be more than 1 CPU in the cpus_allowed list for proper functionality")
            housekeeping_cpus = copy.deepcopy(cpus_allowed)
            isolated_cpus = copy.deepcopy(cpus_allowed)
        else:
            housekeeping_cpus.append(cpus_allowed.pop(0))
            isolated_cpus = copy.deepcopy(cpus_allowed)

        output_cpu_info("housekeeping", housekeeping_cpus)

        output_cpu_info("isolated", isolated_cpus)

    return(0)

if __name__ == "__main__":
    exit(main())
