def get_config(config_path):
    with open(config_path, 'r') as file_config:
        config = dict()
        lines = file_config.readlines()
        for item in lines:
            k,v = item.split('=')
            config[k] = v.strip('\n')

    return config