import subprocess
import time
import asyncio
import sys
import time
import re
import json
import os

sim = True
total_time = []

WATCHDOG = 100 #maximum number of samples (seconds) - useful if bf hangs

asyncio.set_event_loop_policy(
    asyncio.WindowsProactorEventLoopPolicy())

test_fn = r"C:\Users\teenage\cces\2.8.3\benchmarks\src\test.h"
    
timestr = time.strftime("%Y%m%d-%H%M%S")
power_measurements_fn = "benchmarks_" + timestr + ".json"

if sim:
    power_measurements_fn = "sim_benchmarks_" + timestr + ".json"
    
current_regex = '\d+mA'

all_tests_dict = []

for i in range(0, 100):
    with open(test_fn, 'w') as f:
        f.write("#define TEST " + str(i) + "\n")
        if sim:
            f.write("#define SIM 1\n")

    test_results = {}

    try:
        os.replace(r'C:\Users\teenage\cces\2.8.3\benchmarks\Debug\benchmarks.dxe', r'C:\Users\teenage\cces\2.8.3\benchmarks\Debug\benchmarksold.dxe')
    except:
        pass

    print('launching make process, test# ' + str(i))
    
    try:
        make = subprocess.Popen([r"C:\Analog Devices\Crosscore Embedded Studio 2.8.3\Make.exe", "all", "-C", r"C:\Users\teenage\cces\2.8.3\benchmarks\Debug"], stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        make.wait(timeout=WATCHDOG)
        test_results["make_stdout"] = make.stdout.read().decode()
        test_results["make_stderr"] = make.stderr.read().decode()

        if (test_results["make_stderr"]):
            print('error in make, ending tests')
            print(test_results["make_stderr"])
            all_tests_dict.append(test_results)
            break
        
    except Exception as e:
        print('error in make')
        print(e)
        break

    print('launching cces process, test# ' + str(i))

    try:
        if sim:
            start_time = time.time()
            cces_runner = subprocess.Popen([r"C:\Analog Devices\Crosscore Embedded Studio 2.8.3\CCES_runner.exe", "-@", "options_sim.txt"], stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            cces_runner.wait(timeout=WATCHDOG)
            total_time.append(time.time()-start_time)
        else:
            cces_runner = subprocess.Popen([r"C:\Analog Devices\Crosscore Embedded Studio 2.8.3\CCES_runner.exe", "-@", "options.txt"], stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            if cces_runner.poll():
                print('error starting runner, ending tests')
                all_tests_dict.append(test_results)
                break

            time.sleep(5)

            watchdog = WATCHDOG
            raw_readings = []
            current_readings = []
            
            while cces_runner.poll() is None and watchdog:
                watchdog-=1
                portpilot = subprocess.Popen(["PortPilotCmd.exe", "-r1"], stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                portpilot.wait()
                time.sleep(1)
                out = portpilot.stdout.read().decode()
                raw_readings.append(out)
                if raw_readings:
                    current_readings.append(int(re.search(current_regex, out).group()[:-2]))

            if not watchdog:
                cces_runner.kill()
                print('watchdog timeout')
                break
        
            test_results["portpilot_stdout"] = raw_readings
            test_results["portpilot_stderr"] = portpilot.stderr.read().decode()
            if (test_results["portpilot_stderr"]):
                print('error in portpilot, ending tests')
                all_tests_dict.append(test_results)
                break

            test_results["current_readings"] = current_readings
            test_results["max_current"] = max(current_readings)
            
        out = cces_runner.stdout.read().decode()
        test_results["cces_runner_stdout"] = out
        test_results["cces_runner_stderr"] = cces_runner.stderr.read().decode()
        if (test_results["cces_runner_stderr"]):
            print('error in cces, ending tests')
            all_tests_dict.append(test_results)
            break

        test_results["name"] = out.split()[0]
        out = out.split("cycles:")[1]
        test_results["cycles"] = int(out.split()[0])
        test_results["numbenchmarks"] = out.split("numbenchmarks: ")[1]

        all_tests_dict.append(test_results)
        
    except Exception as e:
        print('error in portpilot or cces process')
        print(e)
        all_tests_dict.append(test_results)
        break

    if test_results["name"] == 'end':
        break
    
with open(power_measurements_fn, 'w') as outfile:
    json.dump(all_tests_dict, outfile)
    print('data dumped to ' + power_measurements_fn)
