import bisect

def get_closest_configs_bisect(timestamp, timestamps):
    timestamps_len = len(timestamps)
    if timestamps_len == 1:
        return 0
    index = bisect.bisect_left(timestamps, timestamp)
    if index == timestamps_len:
        return index - 1
    return index