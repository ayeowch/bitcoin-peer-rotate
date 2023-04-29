#!/usr/bin/env python
import argparse
import json
import logging
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# Bitcoin Core RPC config.
BITCOIN_DIR = os.getenv("BITCOIN_DIR", default=Path.home() / ".bitcoin")
RPC_HOST = os.getenv("BITCOIN_RPC_HOST", default="localhost")
RPC_PORT = os.getenv("BITCOIN_RPC_PORT", default=8332)
RPC_COOKIE_AUTH_PATH = os.getenv(
    "BITCOIN_RPC_COOKIE_AUTH_PATH", default=BITCOIN_DIR / ".cookie"
)

# URL to fetch new peers from.
NEW_PEERS_URL = os.getenv(
    "BITCOIN_NEW_PEERS_URL", default="https://bitnodes.io/api/v1/nodes/sample/"
)

PROG = "bitcoin-peer-rotate"
DESCRIPTION = "Rotate peers for local Bitcoin Core node."
ENVIRONMENT_VARIABLES = f"""
Environment variables:
BITCOIN_DIR={BITCOIN_DIR},
BITCOIN_RPC_HOST={RPC_HOST},
BITCOIN_RPC_PORT={RPC_PORT},
BITCOIN_RPC_COOKIE_AUTH_PATH={RPC_COOKIE_AUTH_PATH}
"""


class BitcoinRpcException(Exception):
    pass


class BitcoinPeerRotateException(Exception):
    pass


class BitcoinRpc:
    """
    Strictly implements only the Bitcoin Core RPC client calls required to
    operate bitcoin_peer_rotate.

    Works only with Bitcoin Core node that uses local cookie file for
    authentication.
    """

    def __init__(self):
        self.auth = self._read_cookie_auth(RPC_COOKIE_AUTH_PATH)

        self.rpc_url = f"http://{RPC_HOST}:{RPC_PORT}/"
        logging.debug(f"rpc_url={self.rpc_url}")

        self.allowed_rpc_calls = (
            "addnode",
            "disconnectnode",
            "getaddednodeinfo",
            "getpeerinfo",
        )

        self.request = Request()

    def addnode(self, addr, action="add"):
        return self._rpc("addnode", params=[addr, action])

    def disconnectnode(self, addr):
        return self._rpc("disconnectnode", params=[addr])

    def getaddednodeinfo(self):
        return self._rpc("getaddednodeinfo")

    def getpeerinfo(self):
        return self._rpc("getpeerinfo")

    def purge_peers(self, keep=None):
        """
        Orchestrates a sequence of RPC calls to completely remove existing
        peers.
        """
        purged = 0  # Total peers removed from getpeerinfo and getaddednodeinfo.

        logging.info("purging existing peers")

        # Immediately disconnect any connected peers.
        for peer in self.getpeerinfo():
            addr = peer["addr"]
            if self._keep_contains(keep, addr):
                continue
            logging.info(f"disconnecting peers seen in getpeerinfo - addr={addr}")
            try:
                self.disconnectnode(addr)
            except BitcoinRpcException as err:
                logging.warning(err)  # May already be disconnected.
            else:
                purged += 1

        # Flush added nodes.
        node_info = self.getaddednodeinfo()
        for entry in node_info:
            addr = entry["addednode"]
            if self._keep_contains(keep, addr):
                continue
            logging.info(f"removing peers from addednode - addr={addr}")
            self.addnode(addr, action="remove")
            purged += 1

        logging.info(f"peers purged={purged}")
        return purged

    def _read_cookie_auth(self, filepath):
        username, password = open(filepath, "r").read().split(":")
        return username, password

    def _keep_contains(self, keep, addr):
        if not keep:
            return False

        # Extracts IP/.onion part excluding the port and brackets for IPv6.
        ip = addr.rsplit(":", 1)[0].strip("[").strip("]")

        # Ensures keep contains only IP/.onion address of the same format.
        keep = [k.rsplit(":", 1)[0].strip("[").strip("]") for k in keep]

        return ip in keep

    def _rpc(self, cmd, params=None, max_tries=30):
        if cmd not in self.allowed_rpc_calls:
            raise BitcoinRpcException(f"RPC call {cmd} is not supported.")

        if params is None:
            params = []
        data = json.dumps(
            {
                "id": str(int(time.time() * 1e6)),
                "jsonrpc": "1.0",
                "method": cmd,
                "params": params,
            }
        )
        logging.debug(f"cmd={cmd} - params={params}")

        response = self.request.post(self.rpc_url, data=data, auth=self.auth)
        if response is None:
            raise BitcoinRpcException(f"No data from {self.rpc_url}")

        json_response = response.json()
        error = json_response.get("error")
        if error:
            # See https://github.com/bitcoin/bitcoin/blob/master/src/rpc/protocol.h
            rpc_in_warmup = -28
            if error.get("code") == rpc_in_warmup and max_tries > 0:
                time.sleep(1)
                return self._rpc(cmd, params, max_tries=max_tries - 1)
            raise BitcoinRpcException(error)

        result = json_response.get("result")
        return result


class BitcoinPeerRotate:
    def __init__(
        self,
        types=None,
        asns=None,
        country_codes=None,
        speed=None,
        limit=None,
        keep=None,
        min_limit=8,
    ):
        self.types = types or []  # ipv4, ipv6, onion.
        self.asns = asns or []  # List of AS numbers.
        self.country_codes = country_codes or []  # List of country codes.
        self.speed = speed  # Percentile value if set.
        self.limit = limit  # Number of new peers to fetch.
        self.keep = keep  # List of IP addresses if set.

        # Hard minimum of number of new peers required for rotation to take effect.
        self.min_limit = min_limit

        # Limit to 10 entries for ASNs and country codes.
        max_entries = 10
        self.asns = list(set(self.asns))[:max_entries]
        self.country_codes = list(set(self.country_codes))[:max_entries]

        logging.info(
            f"effective args - "
            f"types={self.types} - "
            f"asns={self.asns} - "
            f"country_codes={self.country_codes} - "
            f"speed={self.speed} - "
            f"limit={self.limit} - "
            f"keep={self.keep}"
        )

        self.rpc = BitcoinRpc()

        self.request = Request()

    def rotate(self):
        response = self.request.get(NEW_PEERS_URL, params=self._get_params())
        if response is None:
            raise BitcoinPeerRotateException(f"No data from {NEW_PEERS_URL}")

        json_response = response.json()
        new_nodes = json_response.get("nodes", {})
        new_addrs = list(new_nodes.keys())
        logging.info(f"new peers available - new_addrs={len(new_addrs)}")

        if new_addrs and len(new_addrs) >= self.min_limit:
            self.rpc.purge_peers(keep=self.keep)
            for idx, (addr, data) in enumerate(new_nodes.items()):
                logging.info(f"new peer - addr={addr} - data={data}")
                self.rpc.addnode(addr)
        else:
            logging.warning(
                f"skipping rotation due to insufficient new peers - new_addrs={len(new_addrs)}"
            )

    def _get_params(self):
        params = dict(
            types=",".join(self.types),
            asns=",".join(self.asns),
            country_codes=",".join(self.country_codes),
            speed=self.speed,
            limit=self.limit,
        )
        return params


class Request:
    def __init__(self, headers=None, timeout=30, max_tries=10):
        self.session = requests.Session()
        self.headers = headers or {"content-type": "application/json"}
        self.timeout = timeout  # In seconds.
        self.max_tries = max_tries

    def get(self, url, params=None):
        return self._retryable(self.session.get, url, self.max_tries, params=params)

    def post(self, url, data=None, auth=None):
        return self._retryable(
            self.session.post, url, self.max_tries, data=data, auth=auth
        )

    def _retryable(self, func, url, tries, params=None, data=None, auth=None):
        response = None

        while tries > 0:
            try:
                response = func(
                    url,
                    params=params,
                    data=data,
                    auth=auth,
                    headers=self.headers,
                    timeout=self.timeout,
                )
            except requests.exceptions.RequestException as err:
                logging.error(f"url={url} - err={err}")
            else:
                if response.status_code in (200, 500):
                    break

            logging.warning(f"retrying - url={url}")
            tries -= 1
            time.sleep(1)

        return response


def parse_arguments():
    parser = argparse.ArgumentParser(
        prog=PROG, description=DESCRIPTION, epilog=ENVIRONMENT_VARIABLES
    )

    parser.add_argument(
        "--types",
        nargs="+",
        choices=("ipv4", "ipv6", "onion"),
        default=["ipv4"],
        help="List of space-separated network types to connect to. Default: ipv4",
    )

    asns_or_country_codes = parser.add_mutually_exclusive_group()

    asns_or_country_codes.add_argument(
        "--asns",
        nargs="+",
        default=[],
        help="List of up to 10 space-separated ASNs to connect to. "
             "Not applicable for .onion peers. "
             "Specify numbers only, e.g. --asns 24940 16509. "
             "Cannot be specified together with --country-codes. "
             "Default: unset",
    )

    asns_or_country_codes.add_argument(
        "--country-codes",
        nargs="+",
        default=[],
        help="List of up to 10 space-separated country codes to connect to. "
             "Not applicable for .onion peers. "
             "Specify country codes only, e.g. --country-codes US DE FR. "
             "Cannot be specified together with --asns. "
             "Default: unset",
    )

    parser.add_argument(
        "--speed",
        default=1,
        choices=(1, 25, 50, 75, 90, 95, 99),
        type=int,
        help="Filter for IPv4/IPv6 peers starting from the specified minimum download speed percentile. "
             "Not applicable for .onion peers. "
             "Default: 1",
    )

    parser.add_argument(
        "--limit",
        default=20,
        choices=(8, 10, 20, 30, 40, 50),
        type=int,
        help="Number of new peers to fetch. Default: 8",
    )

    parser.add_argument(
        "--keep",
        nargs="+",
        default=[],
        help="List of space-separated existing peer IP addresses to keep. "
             "These peers won't be rotated out. "
             "Default: Empty list",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=logging.getLevelNamesMapping().keys(),
        help="Set log output level. Default: INFO",
    )

    parser.add_argument(
        "--log-file",
        default=BITCOIN_DIR / f"{PROG}.log",
        help=f"Path for log file. Default: {BITCOIN_DIR / f'{PROG}.log'}",
    )

    return parser.parse_args()


def check_env():
    if not os.path.isdir(BITCOIN_DIR):
        raise BitcoinRpcException(
            f"Bitcoin directory not found at {BITCOIN_DIR}. "
            f"Is BITCOIN_DIR environment variable set?"
        )

    if not os.path.isfile(RPC_COOKIE_AUTH_PATH):
        raise BitcoinRpcException(
            f"Bitcoin RPC cookie file not found at {RPC_COOKIE_AUTH_PATH}. "
            f"Is Bitcoin Core running and BITCOIN_RPC_COOKIE_AUTH_PATH environment variable set?"
        )


def configure_logging(log_level, log_file):
    logger = logging.getLogger()
    logger.setLevel(logging.getLevelNamesMapping()[log_level])

    console_handler = logging.StreamHandler()
    logfile_handler = logging.FileHandler(log_file)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    logfile_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(logfile_handler)


def main():
    args = parse_arguments()

    check_env()

    configure_logging(args.log_level, args.log_file)

    logging.info(f"running - {PROG}")
    bpr = BitcoinPeerRotate(
        types=args.types,
        asns=args.asns,
        country_codes=args.country_codes,
        speed=args.speed,
        limit=args.limit,
        keep=args.keep,
    )
    bpr.rotate()
    logging.info(f"completed - {PROG}")


if __name__ == "__main__":
    main()
