def main():
    import util

    name = 'catalog_service'
    function_names = [
        name,
        'catalog_register',
        'catalog_deregister',
    ]

    util.delete_rest_api_by_name(name)
    for function_name in function_names:
        util.delete_function(function_name)


if __name__ == '__main__':
    main()
