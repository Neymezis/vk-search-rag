import argparse

from common.opensearch_client import get_client, create_index, create_search_pipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-recreate", action="store_true")
    args = parser.parse_args()

    client = get_client()
    create_index(client, force=args.force_recreate)
    create_search_pipeline(client)
    print("Готово.")


if __name__ == "__main__":
    main()
