
def parse_ts5(path):
    with open(path) as f:
        return f.read().splitlines()
