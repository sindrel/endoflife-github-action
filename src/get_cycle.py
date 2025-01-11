# pylint: disable=C0114,C0116,W0621,C0301

import json
import os
import sys
import argparse
import re
import http.client

from datetime import datetime

import yaml


def get_product_cycle(args):
    result = {}
    version = None

    if not args.version:
        with open(file=args.file_path, mode='r', encoding='utf8') as file:
            file_contents = file.read()
        if args.file_format in ['yaml', 'json']:
            print(f"Looking for version in file '{args.file_path}' using key '{args.file_key}'...")
            version = _get_version_from_structured_file(args, file_contents)
        elif args.file_format == 'text':
            print(f"Looking for version in file '{args.file_path}' using regex '{args.regex}'...")
            version = _extract_value_from_string(args.regex, file_contents)
    else:
        version = args.version

    if not version:
        print("No version was extracted or supplied.")
        return result

    print(f"Version found: {version}")

    product_cycles = _get_product_details(args.product)

    if version:
        semantic = _parse_semantic_version(version)
        cycle = _match_version_to_cycle(product_cycles, *semantic)
        if cycle["eol"]:
            eol_passed, eol_days_until = _check_eol_date(
                cycle["eol"])
        else:
            eol_passed = False
            eol_days_until = None

        result = {
            "product": args.product,
            "version": version,
            "cycle": cycle,
            "end_of_life": eol_passed,
            "days_until_eol": eol_days_until,
        }

        result['text_summary'] = _construct_summary(result)

    return result


def write_to_output_file(result, output_file):
    outputs = f"""
version={result['version']}
end_of_life={str(result['end_of_life']).lower()}
days_until_eol={result['days_until_eol']}
text_summary={result['text_summary']}
"""
    with open(file=output_file, mode='a', encoding='utf8') as file:
        file.write(outputs)


def _check_eol_date(eol_date):
    eol_datetime = datetime.strptime(eol_date, "%Y-%m-%d")
    current_datetime = datetime.now()
    days_until_eol = (eol_datetime - current_datetime).days
    end_of_life = days_until_eol < 0

    return end_of_life, days_until_eol


def _parse_semantic_version(version):
    parts = version.lstrip('v').split('.')
    major = parts[0]
    minor = parts[1] if len(parts) > 1 else None
    patch = parts[2] if len(parts) > 2 else None

    print(f"Split version {version} into major: {major}, minor: {minor}, patch: {patch}")
    return major, minor, patch


def _match_version_to_cycle(cycles, major, minor, patch):
    for cycle in cycles:
        if cycle["cycle"] in [
            f"{major}.{minor}.{patch}",
            f"{major}.{minor}",
            f"{major}"
        ]:
            return cycle
    return None


def _get_product_details(product):
    host = "endoflife.date"
    path = f"/api/{product}.json"
    conn = http.client.HTTPSConnection(host)
    headers = {'Accept': "application/json"}
    conn.request("GET", path, headers=headers)
    res = conn.getresponse()
    data = res.read()

    if res.status != 200:
        print(f"Unable to fetch product details from {host}{path}: {res.status}")
        return None

    json_contents, error = _json_decode(data.decode("utf-8"))
    if error:
        print(f"Unable to parse result from {host}: {error}")
        return None

    return json_contents


def _get_version_from_structured_file(args, file_contents):
    if args.file_format == "yaml":
        yaml_file, error = _yaml_decode(file_contents)
        if error:
            print(f"Error parsing file: {error}")
            return None

    elif args.file_format == "json":
        yaml_file, error = _json_decode(file_contents)
        if error:
            print(f"Error parsing file: {error}")
            return None

    else:
        raise ValueError(f"Unsupported format: {args.file_format}")

    keys = args.file_key.split('.')
    value = yaml_file
    for k in keys:
        value = value.get(k, None)
        if value is None:
            break
    return value


def _yaml_decode(file_contents):
    try:
        return yaml.safe_load(file_contents), ""
    except yaml.YAMLError as e:
        msg = f"Error parsing YAML: {e}"
        return None, msg


def _json_decode(file_contents):
    try:
        return json.loads(file_contents), ""
    except json.JSONDecodeError as e:
        msg = f"Error parsing JSON: {e}"
        return None, msg


def _extract_value_from_string(regex, string):
    # 'v([0-9]+\.[0-9]+\.[0-9]+)'
    match = re.search(regex, string)
    if match:
        return match.group(0)
    return None

def _construct_summary(result):
    if result['end_of_life']:
        return f"{result['product']} {result['version']} is end-of-life."
    if not result['days_until_eol']:
        return f"{result['product']} {result['version']} has no end-of-life date set."
    return f"{result['product']} {result['version']} has {result['days_until_eol']} days left until end-of-life."

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Get product cycle information from endoflife.date.')
    parser.add_argument('--product', type=str, required=True,
                        help='Product name to fetch the cycle information.')
    parser.add_argument('--file_path', type=str, required=False,
                        help='Path to the file containing the version information.')
    parser.add_argument('--file_key', type=str, required=False,
                        help='Key to extract the version from the file (if yaml or json).')
    parser.add_argument('--file_format', type=str, required=False,
                        choices=['yaml', 'json', 'text'], help='File format (yaml, json or text).')
    parser.add_argument('--version', type=str, required=False,
                        help='A known product version.')
    parser.add_argument('--regex', type=str, required=False,
                        help='A regular expression used for extracting the product version.')
    parser.add_argument('--fail_on_eol', type=str, required=False,
                        help='Fail the workflow if the product is end-of-life.')
    parser.add_argument('--fail_days_left', type=str, required=False,
                        help='Fail the workflow if less than x days until end-of-life.')

    args = parser.parse_args()

    if not args.file_path and not args.version:
        sys.exit("Either file_path or version must be provided.")

    if args.file_path and not (args.file_key or args.regex):
        sys.exit(
            "Either file_key or regex must be provided when extracting from file.")

    if args.file_key and args.regex:
        sys.exit("Only one of file_key or regex can be provided.")

    if args.regex:
        try:
            re.compile(args.regex)
        except re.error:
            sys.exit(f"Invalid regular expression: '{args.regex}'")
        args.file_format = "text"

    if args.file_format not in ['yaml', 'json'] and not args.regex:
        sys.exit("A regex must be provided when using text format.")

    result = get_product_cycle(args)
    if not result:
        sys.exit("No result.")

    print(result['text_summary'])

    env_file = os.getenv('GITHUB_OUTPUT', 'output.tmp')
    write_to_output_file(result, env_file)

    if (args.fail_on_eol and args.fail_on_eol.lower() == "true") and result['end_of_life']:
        sys.exit(result['text_summary'])

    if args.fail_days_left and result['days_until_eol'] <= int(args.fail_days_left):
        sys.exit(result['text_summary'])
