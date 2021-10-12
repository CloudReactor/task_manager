EXCLUDED_PATH_FRAGMENTS = [
  'process',
  'api_key',
  '/group',
  'invitation',
  'user'
]

def preprocessing_hook(endpoints):
    filtered_endpoints = []
    for endpoint in endpoints:
        path = endpoint[0]

        included = True
        i = 0
        while included and (i < len(EXCLUDED_PATH_FRAGMENTS)):
            if EXCLUDED_PATH_FRAGMENTS[i] in path:
                included = False
                break
            i += 1

        if included:
            filtered_endpoints.append(endpoint)
        else:
            print(f'Skipping {path=}')

    return filtered_endpoints
