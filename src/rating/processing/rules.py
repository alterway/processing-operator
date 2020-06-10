from rating.processing import utils


def check_label_match(frame_labels, labelset):
    for key, value in labelset.items():
        if frame_labels.get(key) != value:
            return False
    return True


def find_match(metric, frame_labels, rules):
    for ruleset in rules:
        labelset = ruleset.get('labelSet', {})
        rulelist = ruleset.get('ruleset', [])
        for rule in rulelist:
            if rule['metric'] != metric:
                continue
            if check_label_match(frame_labels, labelset):
                return labelset, rule
    return {}, {}


def validate_value(value):
    return isinstance(value, str) and utils.is_valid_against(value, '^[a-zA-Z0-9-_]+$')


def ensure_rules_config(ruleset):
    accepted_rules_keys = {'metric', 'price', 'unit'}
    for entry in ruleset:
        pair_checking = []

        # Rules checking
        rules = entry.get('ruleset')
        if not rules or len(rules) == 0:
            raise utils.ConfigurationException(
                'No rules provided')
        for rule in rules:
            if rule in pair_checking:
                raise utils.ConfigurationException(
                    'Duplicated (metric, price, unit)',
                    rule)
            # Keys checking
            keys = set(rule.keys())
            if keys != accepted_rules_keys:
                raise utils.ConfigurationException(
                    'Wrong key in ruleset',
                    keys)
            # Values checking
            for value in rule.values():
                if isinstance(value, (int, float)):
                    continue
                elif not validate_value(value):
                    raise utils.ConfigurationException(
                        'Invalid value in ruleset',
                        value
                    )
            pair_checking.append(rule)

        # Labels checking
        labels = entry.get('labels')
        if not labels:
            continue
        for value in labels.values():
            if not isinstance(value, (str, int, float)):
                raise utils.ConfigurationException('Wrong type for label', value)
