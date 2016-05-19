def main():
    import util

    name = 'catalog_service'

    util.delete_rest_api_by_name(name)
    util.delete_function(name)


if __name__ == '__main__':
    main()
