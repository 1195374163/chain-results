import os
import glob
import matplotlib.pyplot as plt
import numpy as np

# Press Shift+F10 to execute it or replace it with your code.

exp_names = ["read_strong/test"]
savedir = "graphs/"
os.makedirs(savedir, exist_ok=True)

n_threads = [1,20, 50, 100, 150, 200, 300, 500, 600, 750, 1000, 1500, 2000, 3000, 4000, 5000, 6000, 7000,
             8000]
n_clients = 3
payload = 128
reads = [0, 50, 95, 100]
n_servers = [3, 7]

algorithms = [
    "esolatedpaxos",
    "chain_delayed",
    "chain_mixed",
]

alg_limiter = {
    3: {
        0: {"chain_mixed": 200,
            "esolatedpaxos": 200},
        50: {"chain_delayed": 300},
        95: {"chain_mixed": 200,
             "chain_delayed": 2000},
        100: {"esolatedpaxos": 200}
    },
    7: {
        0: {"chain_mixed": 300,
            "esolatedpaxos": 200},
        50: {"chain_mixed": 300,
             "chain_delayed": 500},
        95: {"chain_mixed": 300,
             "chain_delayed": 5000},
        100: {"esolatedpaxos": 200}
    }
}

alg_mapper = {"chain_mixed_0": "Chain Reads 0/100%",
              "chain_delayed_50": "Local Reads 50%",
              "chain_delayed_95": "Local Reads 95%",
              "chain_mixed_95": "Chain Read 95%",
              "esolatedpaxos_0": "EPaxos-NoDeps 0%",
              "esolatedpaxos_100": "EPaxos-NoDeps 100%"}

markermap = {"chain_mixed_0": "o",
             "chain_delayed_50": "8",
             "chain_delayed_95": "s",
             "chain_mixed_95": "p",
             "esolatedpaxos_0": "P",
             "esolatedpaxos_100": "X"}

n_runs = 3
skip = 3
time_min = 30
time_max = 80


def average(lst):
    # print(lst)
    # print(sum(lst) / len(lst))
    return sum(lst) / len(lst)


def weighted_average(lst):
    vals_sum = 0
    weight_sum = 0
    for (val, weight) in lst:
        vals_sum += (val * weight)
        weight_sum += weight
    return vals_sum / weight_sum


def check_folder_or_exit(path):
    if not os.path.isdir(path):
        print("No folder: " + path)
        exit(1)


def check_folder(path):
    return os.path.isdir(path)


def check_len_or_exit(obj_to_check, size, message=""):
    if not len(obj_to_check) == size:
        print("Size mismatch: " + str(size) + " " + str(len(obj_to_check)) + " - " + message)
        exit(1)


def get_idx_of(split, word, initial_look=0):
    for i in range(initial_look, len(split)):
        if split[i] == word:
            return i
    # print("String not found: " + word + " in " + " ".join(split))
    return -1


def process_alg(alg_path):
    results_raw = {}
    # 1,2,3
    n_threads_filtered = list(filter(lambda t: t <= alg_limiter[server][read][alg], n_threads))
    print(n_threads_filtered)
    for run in range(1, n_runs + 1):
        results_raw[run] = {}
        run_path = alg_path + "/" + str(run)
        check_folder_or_exit(run_path)
        # 1,2,5,10,20,...
        for thread in n_threads_filtered:
            # print("----" + str(thread))
            if alg_limiter[server][read][alg] < thread:
                continue
            results_raw[run][thread] = {}
            thread_files = glob.glob(run_path + "/" + str(thread) + "_*")
            if not len(thread_files) == n_clients:
                print(str(len(thread_files)) + " instead of " + str(n_clients) + " clients for thread " +
                      str(thread) + " in path " + run_path)
                exit(1)
            client = 0
            # paravance-26, paravance-30,...
            for thread_file in thread_files:
                results_raw[run][thread][client] = {}
                # print(thread_file)
                file = open(thread_file, 'r')
                for line in file.readlines()[skip:]:
                    split = line.split()
                    try:
                        time = int(split[2])

                        if time_min > time or time > time_max:
                            print("Unexpected time " + str(time) + " in file " + thread_file)
                            exit(1)

                        throughput = float(split[6])
                        write_idx = get_idx_of(split, "[INSERT:", initial_look=7)
                        if write_idx != -1:
                            n_writes = int(split[write_idx + 1].strip(',').split('=')[1])
                            avg_write_lats = float(split[write_idx + 4].strip(',').split('=')[1])
                        else:
                            n_writes = 0
                            avg_write_lats = 0
                        read_idx = get_idx_of(split, "[READ:", initial_look=7)
                        if read_idx != -1:
                            n_reads = int(split[read_idx + 1].strip(',').split('=')[1])
                            avg_read_lats = float(split[read_idx + 4].strip(',').split('=')[1])
                        else:
                            n_reads = 0
                            avg_read_lats = 0

                        avg_lats = ((n_reads * avg_read_lats) + (n_writes * avg_write_lats)) / (n_reads + n_writes)

                        results_raw[run][thread][client][int(split[2])] = (throughput, avg_lats, n_reads + n_writes)
                        if time == time_max:
                            break
                    except:
                        print("Error parsing " + thread_file)
                        print("On line: " + line)
                        raise
                check_len_or_exit(results_raw[run][thread][client], (time_max - time_min) / 10 + 1,
                                  f"alg {alg} run {run} thread {thread} client {client}")
                client += 1
            check_len_or_exit(results_raw[run][thread], n_clients)
        check_len_or_exit(results_raw[run], len(n_threads_filtered))
    check_len_or_exit(results_raw, n_runs)

    # list of nThreads, throughput, latency
    results_parsed = []
    stds_perf = []
    stds_lat = []

    for thread in n_threads_filtered:
        # One position per run
        n_total_threads = thread * n_clients
        avg_thread_tp_list = []
        avg_thread_lat_list = []
        for run in range(1, n_runs + 1):
            # One position per time interval
            avg_run_tp_list = []
            # One position per client per time interval (weighted)
            avg_run_lat_list = []
            for time in range(time_min, time_max + 1, 10):
                # Sum of clients in this time interval
                total_time_tp = 0
                # One position per client in a time interval
                for client in range(0, n_clients):
                    (tp, lat, nOps) = results_raw[run][thread][client][time]
                    total_time_tp += tp
                    avg_run_lat_list.append((lat, nOps))
                # Average clients for each time interval
                avg_run_tp_list.append(total_time_tp)
            # Average times for each run
            avg_thread_tp_list.append(average(avg_run_tp_list))
            try:
                avg_thread_lat_list.append(weighted_average(avg_run_lat_list))
            except:
                print("Exception in average calculation: " + str(avg_run_lat_list) + " thread " + str(
                    thread) + "run " + str(run))
                exit(1)
        # Average runs
        # print(avg_thread_lat_list)
        stds_lat.append(np.std(avg_thread_lat_list) * 100 / average(avg_thread_lat_list))
        stds_perf.append(np.std(avg_thread_tp_list) * 100 / average(avg_thread_tp_list))

        results_parsed.append(
            (n_total_threads, average(avg_thread_tp_list) / 1000, average(avg_thread_lat_list) / 1000))
    print("lat " + str(max(stds_lat)))
    print("perf " + str(max(stds_perf)))

    return results_parsed


def create_plot(results_all):
    plt.rcParams.update({'font.size': 12})
    # figB, axB = plt.subplots(num=1, clear=True)
    # figT, axT = plt.subplots(num=2, clear=True)
    # figL, axL = plt.subplots(num=3, clear=True)

    plt.figure(figsize=(6.4, 3.2))
    for alg, points in results_all.items():
        tps = []
        lats = []
        threads = []
        for th, tp, lat in points:
            tps.append(tp)
            lats.append(lat)
            threads.append(th)
            # if alg == "bayou":
            #    plt.annotate(th, (tp, lat), rotation=30)
            # axL.annotate(th, (th, lat), rotation=45)

        plt.plot(tps, lats, linewidth=2, label=alg_mapper[alg],
                 markersize=7, marker=markermap[alg])

    # axT.plot(threads, tps, label=alg)
        # axL.plot(threads, lats, label=alg)
    plt.xlabel("Throughput (1000 ops/s) - " + str(server) + " Replicas")
    plt.ylabel("Average latency (ms)")
    plt.xlim(left=0,right=1780)
    plt.ylim(bottom=0)
    if server == 3:
        plt.legend(frameon=False,loc='lower right')
    plt.tight_layout()
    # plt.legend(loc="upper right")
    plt.savefig(savedir + "reads_alt" + "_" + str(server) + ".pdf")
    # plt.title(exp_name + " reads " + str(reads) + " runs " + str(n_runs))

    # axT.legend()
    # axL.legend()

    plt.show()


if __name__ == '__main__':
    results_all = {}
    for exp_name in exp_names:
        for server in n_servers:
            for read in reads:
                print("Reads " + str(read))
                for alg in algorithms:
                    print(alg)
                    alg_path = "logs/" + exp_name + "/client/" + str(server) + "/" + str(read) + "/" + str(
                        payload) + "/" + alg
                    if check_folder(alg_path):
                        results_all[alg + "_" + str(read)] = process_alg(alg_path)
                        for tuple in results_all[alg + "_" + str(read)]:
                            print("%4s" % tuple[0],
                                  "%10s" % round(tuple[1], 2),
                                  "%10s" % round(tuple[2], 2))
                    else:
                        print("No data for read " + str(read) + " alg " + alg)
            create_plot(results_all)
