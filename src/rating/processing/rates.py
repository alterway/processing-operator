from rating.processing import utils


def rate(rule, frame):
    price = rule.get('price')
    if price is not None:
        return float(rule['price']) * frame['qty']
    return None


def rate_multiple_frames(frames, rules):
    for frame in frames:
        frame['frame_price'] = calc_frame_price(frame, rules)


def calc_frame_price(frame, rules):
    nodetype = frame['instance_type']
    metric = frame['metric']
    if metric not in rules:
        raise utils.ConfigurationException('Unsupported metric: ', metric)
    return rate(rules[metric][nodetype], frame)


def convert_metrics_unit(metric_unit, rating_unit, qty):
    try:
        return {
            ('byte-seconds', 'GiB-hours'): lambda x: (float(x) / 1024 ** 3) / 3600,
            ('core-seconds', 'core-hours'): lambda x: float(x) / 3600,
            ('byte', 'GiB'): lambda x: (float(x) / 1024 ** 3)
        }[(metric_unit, rating_unit)](qty)
    except KeyError:
        raise utils.ConfigurationException('Unsupported key in conversion')
