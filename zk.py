import os
import glob
import matplotlib.pyplot as plt
import numpy as np
import matplotlib

matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
# Press Shift+F10 to execute it or replace it with your code.

exp_names = ["zk/test"]
savedir = "graphs/"
os.makedirs(savedir, exist_ok=True)

n_threads = [1, 2, 5, 10, 20, 30, 50, 75, 100, 150, 200, 250, 300, 350, 500]
n_clients = 3
payload = 128
reads = 0
n_servers = [3,5,7]


alg_limiter = {
    "original": {3: 350, 5: 150, 7: 100},
    "chain": {3: 500, 5: 500, 7: 500}
}
alg_mapper = {
    "original_1": "Zk-Zab 1 Rep",
    "chain_1": "Zk-Chain 1 Rep",
    "original_3": "Zk-Zab 3 Reps",
    "chain_3": "Zk-Chain 3 Reps",
    "original_5": "Zk-Zab 5 Rep",
    "chain_5": "Zk-Chain 5 Rep",
    "original_7": "Zk-Zab 7 Rep",
    "chain_7": "Zk-Chain 7 Rep",
}

color_mapper = {
    "original_1": "coral",
    "original_3": "red",
    "original_5": "firebrick",
    "original_7": "darkred",
    "chain_1": "lime",
    "chain_3": "limegreen",
    "chain_5": "green",
    "chain_7": "darkgreen",
}
marker_mapper = {
    "original_3": "o",
    "original_5": "P",
    "original_7": "s",
    "chain_3": "o",
    "chain_5": "P",
    "chain_7": "s",
}

algorithms = ["original", "chain"]

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


def check_len_or_exit(obj_to_check, size, message=""):
    if not len(obj_to_check) == size:
        print("Size mismatch: " + str(size) + " " + str(len(obj_to_check)) + " - " + message)
        exit(1)


def get_idx_of(split, word, initial_look=0):
    for i in range(initial_look, len(split)):
        if split[i] == word:
            return i
    print("String not found: " + word + " in " + " ".join(split))
    return -1


def process_alg(alg_path):
    results_raw = {}
    # 1,2,3
    n_threads_filtered = list(filter(lambda t: t <= alg_limiter[alg][n_server], n_threads))
    print(n_threads_filtered)
    for run in range(1, n_runs + 1):
        results_raw[run] = {}
        run_path = alg_path + "/" + str(run)
        check_folder_or_exit(run_path)
        # 1,2,5,10,20,...
        for thread in n_threads_filtered:
            # print("----" + str(thread))
            if alg_limiter[alg][n_server] < thread:
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
                        write_idx = get_idx_of(split, "[UPDATE:", initial_look=7)
                        n_writes = int(split[write_idx + 1].strip(',').split('=')[1])
                        avg_write_lats = float(split[write_idx + 4].strip(',').split('=')[1])
                        if reads > 0:
                            read_idx = get_idx_of(split, "[READ:", initial_look=7)
                            n_reads = int(split[read_idx + 1].strip(',').split('=')[1])
                            avg_read_lats = float(split[read_idx + 4].strip(',').split('=')[1])
                        else:
                            n_reads = 0
                            avg_read_lats = 0

                        avg_lats = ((n_reads * avg_read_lats) + (n_writes * avg_write_lats)) / (n_reads + n_writes)
                        # print(split[2] + " " + str(throughput) + " " + str(avg_lats))
                        # print(thread_file + " " + str(avg_lats))
                        results_raw[run][thread][client][int(split[2])] = (throughput, avg_lats, n_writes)
                        if time == time_max:
                            break
                    except:
                        print("Error parsing " + thread_file)
                        print("On line: " + line)
                        raise
                check_len_or_exit(results_raw[run][thread][client], (time_max - time_min) / 10 + 1,
                                  f"alg {alg} run {run} thread {thread} client {thread_file}")
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
            avg_thread_lat_list.append(weighted_average(avg_run_lat_list))
        # Average runs
        # print(avg_thread_lat_list)
        if thread > 1:
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

    # plt.figure(figsize=(10, 8))
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

        plt.plot(tps, lats, linewidth=2, marker=marker_mapper[alg], color=color_mapper[alg], label=alg_mapper[alg],
                 markersize=8)

        #plt.plot(tps, lats, color=color_mapper[alg], label=alg_mapper[alg], markersize=10, marker=".")
        # axT.plot(threads, tps, label=alg)
        # axL.plot(threads, lats, label=alg)
    plt.xlabel("Throughput (1000 ops/s)")
    plt.ylabel("Average latency (ms)")
    plt.xlim(left=0)
    plt.ylim(bottom=0)
    # plt.legend(loc="upper right")
    plt.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(savedir + "zookeeper" + "_serv" + str(n_servers) + "_read" + str(reads) + ".pdf")
    # plt.title(exp_name + " reads " + str(reads) + " runs " + str(n_runs))

    # axT.legend()
    # axL.legend()
    plt.show()


if __name__ == '__main__':
    results_all = {}
    for exp_name in exp_names:
        for alg in algorithms:
            print(alg)
            for n_server in n_servers:
                print(n_server)
                alg_path = "logs/" + exp_name + "/client/" + str(n_server) + "/" + str(reads) + "/" + str(
                    payload) + "/" + alg
                check_folder_or_exit(alg_path)
                results_all[alg + "_" + str(n_server)] = process_alg(alg_path)
                for tuple in results_all[alg + "_" + str(n_server)]:
                    print("%4s" % tuple[0],
                          "%10s" % round(tuple[1], 2),
                          "%10s" % round(tuple[2], 2))
        create_plot(results_all)
