#!/usr/bin/python3

import argparse
import copy
import re
import logging
from pathlib import Path

import sys
import os
TOOLBOX_HOME = os.environ.get('TOOLBOX_HOME')
if TOOLBOX_HOME is None:
    print("This script requires libraries that are provided by the toolbox project.")
    print("Toolbox can be acquired from https://github.com/perftool-incubator/toolbox and")
    print("then use 'export TOOLBOX_HOME=/path/to/toolbox' so that it can be located.")
    exit(1)
else:
    p = Path(TOOLBOX_HOME) / 'python'
    if not p.exists() or not p.is_dir():
        print("ERROR: <TOOLBOX_HOME>/python ('%s') does not exist!" % (p))
        exit(2)
    sys.path.append(str(p))
from toolbox.system_cpu_topology import *

# define some global variables
class t_global(object):
    args = None
    log_debug_format =    '[%(asctime)s %(levelname)s %(module)s %(funcName)s:%(lineno)d] %(message)s'
    log_verbose_format =  '[%(asctime)s %(levelname)s] %(message)s'
    log_normal_format =   '%(message)s'
    log = None

def process_options():
    parser = argparse.ArgumentParser(description="Discover CPU Partitioning configuration (if any)")

    parser.add_argument("--log-level",
                        dest = "log_level",
                        help = "Control how much logging output should be generated",
                        default = "normal",
                        choices = [ "normal", "verbose", "debug" ])

    parser.add_argument("--environment",
                        dest = "environment",
                        help = "What runtime environment is this expected to be.",
                        default = "process",
                        choices = [ "container", "process" ])

    t_global.args = parser.parse_args()

    if t_global.args.log_level == 'debug':
        logging.basicConfig(level = logging.DEBUG, format = t_global.log_debug_format, stream = sys.stdout)
    elif t_global.args.log_level == 'verbose':
        logging.basicConfig(level = logging.INFO, format = t_global.log_verbose_format, stream = sys.stdout)
    elif t_global.args.log_level == 'normal':
        logging.basicConfig(level = logging.INFO, format = t_global.log_normal_format, stream = sys.stdout)

    t_global.log = logging.getLogger(__file__)

    return(0)

def get_rcu_nocbs():
    kernel_cli = ''
    rcu_nocbs = []

    input_file = '/proc/cmdline'

    path = Path(input_file)
    if path.exists() and path.is_file():
        with path.open() as fh:
            kernel_cli = fh.readline().rstrip()
            t_global.log.debug("get_rcu_nocbs: kernel_cli: %s" % (kernel_cli))

            # find 'rcu_nocbs=<cpu-list>' if it exists in the kernel command line
            match = re.search(r"rcu_nocbs=[0-9\-,]+", kernel_cli)
            if match:
                partition = match.group(0).partition('=')
                if partition[1] == partition[2] == '':
                    # this implies that 'rcu_nocbs' exists in the
                    # kernel command line but without a <cpu-list>
                    pass
                else:
                    t_global.log.debug("get_rcu_nocbs: found rcu_nocbs=%s" % (partition[2]))
                    rcu_nocbs = system_cpu_topology.parse_cpu_list(partition[2])
            else:
                t_global.log.debug("get_rcu_nocbs: rcu_nocbs not found")
    else:
        raise FileNotFoundError("get_rcu_nocbs: Could not find '%s'" % (input_file))

    return(rcu_nocbs)

def get_isolcpus():
    kernel_cli = ''
    isolcpus = []

    input_file = '/proc/cmdline'

    path = Path(input_file)
    if path.exists() and path.is_file():
        with path.open() as fh:
            kernel_cli = fh.readline().rstrip()
            t_global.log.debug("get_isolcpus: kernel_cli: %s" % (kernel_cli))

            # find 'isolcpus=[<arg>[,<arg>[,]]]<cpu-list>' if it exists in the kernel command line
            match = re.search(r"\bisolcpus=([a-zA-Z_]+,)*([0-9\-,]+)", kernel_cli)
            if match:
                t_global.log.debug("get_isolcpus: %s" % (match.group(2)))
                isolcpus = system_cpu_topology.parse_cpu_list(match.group(2))
            else:
                t_global.log.debug("get_isolcpus: no isolcpus found")
    else:
        raise FileNotFoundError("get_isolcpus: Could not find '%s'" % (input_file))

    return(isolcpus)

def get_nohz_full():
    kernel_cli = ''
    nohz_full = []

    input_file = '/proc/cmdline'

    path = Path(input_file)
    if path.exists() and path.is_file():
        with path.open() as fh:
            kernel_cli = fh.readline().rstrip()
            t_global.log.debug("get_nohz_full: kernel_cli: %s" % (kernel_cli))

            # find 'nohz_full=<cpu-list>' if it exists in the kernel command line
            match = re.search(r"nohz_full=[0-9\-,]+", kernel_cli)
            if match:
                partition = match.group(0).partition('=')
                if partition[1] == partition[2] == '':
                    pass
                else:
                    t_global.log.debug("get_nohz_full: %s" % (partition[2]))
                    nohz_full = system_cpu_topology.parse_cpu_list(partition[2])
            else:
                t_global.log.debug("get_nohz_full: no nohz_full found")
    else:
        raise FileNotFoundError("get_nohz_full: Could not find '%s'" % (input_file))

    return(nohz_full)

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
                    t_global.log.debug("get_pid_cpus_allowed: found '%s'" % (line))
                    pieces = line.split()
                    if len(pieces) != 2:
                        raise AttributeError("get_pid_cpus_allowed: Could not extract cpus_allowed from '%s'" % (line))
                    else:
                        cpus_allowed = system_cpu_topology.parse_cpu_list(pieces[1])
                        t_global.log.debug("get_pid_cpus_allowed: extracted cpus_allowed=%s" % (cpus_allowed))
    else:
        raise FileNotFoundError("get_pid_cpus_allowed: Requested pid '%s' probably does not exist" % (pid))

    if len(cpus_allowed) == 0:
        raise AttributeError("get_pid_cpus_allowed: failed to determine cpus_allowed")

    return(cpus_allowed)

def output_cpu_info(label, cpu_list):
    t_global.log.debug("%s cpus: %d" % (label, len(cpu_list)))
    short_cpu_list = system_cpu_topology.formatted_cpu_list(cpu_list)
    formatted_short_cpu_list = ','.join(short_cpu_list)
    t_global.log.debug("%s cpus: %s" % (label, formatted_short_cpu_list))

    cpu_list = ','.join(map(str, cpu_list))
    t_global.log.info("%s cpus: %s" % (label, cpu_list))

    t_global.log.info("")

    return(0)

def main():
    process_options()

    if t_global.args.environment == "process":
        system_cpus = system_cpu_topology(log = t_global.log)

        all_cpus = system_cpus.get_all_cpus()
        output_cpu_info("all", all_cpus)

        online_cpus = system_cpus.get_online_cpus()
        output_cpu_info("online", online_cpus)

        isolcpus_cpus = get_isolcpus()
        output_cpu_info("isolcpus", isolcpus_cpus)

        isolation_cpus = isolcpus_cpus
        if len(isolation_cpus) == 0:
            nohz_full_cpus = get_nohz_full()
            output_cpu_info("nohz_full", nohz_full_cpus)

            isolation_cpus = nohz_full_cpus
            if len(isolation_cpus) == 0:
                rcu_nocbs_cpus = get_rcu_nocbs()
                output_cpu_info("rcu_nocbs", rcu_nocbs_cpus)

                isolation_cpus = rcu_nocbs_cpus
                if len(isolation_cpus) == 0:
                    t_global.log.error("There are no isolated cpus that could be identified")
                    return(1)

        odd_list = list(set(isolation_cpus) - set(online_cpus))
        if len(odd_list) > 0:
            t_global.log.warning("this is odd, isolation cpus contains cpus that are not online: %s" % (odd_list))

        housekeeping_cpus = list(set(online_cpus) - set(isolation_cpus))
        if len(housekeeping_cpus) == 0:
            t_global.log.warning("this is odd, there are no housekeeping cpus")
        else:
            output_cpu_info("housekeeping", housekeeping_cpus)

            output_cpu_info("isolated", isolation_cpus)
    elif t_global.args.environment == "container":
        system_cpus = system_cpu_topology(log = t_global.log)

        all_cpus = system_cpus.get_all_cpus()
        output_cpu_info("all", all_cpus)

        online_cpus = system_cpus.get_online_cpus()
        output_cpu_info("online", online_cpus)

        try:
            cpus_allowed = get_pid_cpus_allowed('self')
        except Exception as e:
            t_global.log.error(e)
            return(1)

        housekeeping_cpus = []
        isolated_cpus = []
        if len(cpus_allowed) == 1:
            t_global.log.warning("this is odd, there really needs to be more than 1 CPU in the cpus_allowed list for proper functionality")
            housekeeping_cpus = copy.deepcopy(cpus_allowed)
            isolated_cpus = copy.deepcopy(cpus_allowed)
        else:
            hk_cpu = cpus_allowed.pop(0)
            t_global.log.debug("using first cpu '%d' from cpus_allowed as housekeeping" % (hk_cpu))
            housekeeping_cpus.append(hk_cpu)
            isolated_cpus = copy.deepcopy(cpus_allowed)

            hk_siblings = []
            for cpu in housekeeping_cpus:
                for sibling in system_cpus.get_thread_siblings(cpu):
                    try:
                        isolated_cpus.remove(sibling)
                        housekeeping_cpus.append(sibling)
                        t_global.log.debug("moving cpu '%d' from isolated to housekeeping because it is a thread sibling of the housekeeping cpu" % (sibling))
                    except ValueError as e:
                        pass

        output_cpu_info("housekeeping", housekeeping_cpus)

        output_cpu_info("isolated", isolated_cpus)

    return(0)

if __name__ == "__main__":
    exit(main())
