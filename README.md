# bitcoin-peer-rotate

*Rotate peers for local Bitcoin Core node.*

`bitcoin-peer-rotate` is a Python package designed to facilitate the rotation of
peers for your local Bitcoin Core node as and when required.

The use cases of `bitcoin-peer-rotate` are intended for Bitcoin Core node
that makes outgoing connections only and does not accept incoming connections,
i.e. unreachable node.

**WARNING: If you are operating a reachable Bitcoin Core node, use of
`bitcoin-peer-rotate` will result in your node becoming unreachable externally
from its existing peers, including from the Bitnodes crawler.**

New peers are sampled by `bitcoin-peer-rotate` from Bitnodes API endpoint:
https://bitnodes.io/api/v1/nodes/sample/

## Use cases

- Periodically rotate peers, i.e. disconnect existing peers and connect to a
fresh list of randomly sampled peers with optional filter for one of the
following attributes:
  - IPv4/IPv6 peers from specific ASNs
  - IPv4/IPv6 peers from specific countries
  - IPv4/IPv6 peers that meet specific minimum download speed percentile

- One-off rotation to sync up your fresh Bitcoin Core node installation with
nearby peers.

The use cases above assume you are operating a local Bitcoin Core node that makes
outgoing connections only and does not accept incoming connections.

## Quickstart

### Install

```
$ pip install bitcoin-peer-rotate
```

Add the following in your `~/.bitcoin/bitcoin.conf` file to allow
`bitcoin-peer-rotate` to communicate with your local Bitcoin Core node locally
over RPC protocol. `noconnect=1` is to prevent additional connections not made
by `bitcoin-peer-rotate`:

```
rpcbind=127.0.0.1
rpcport=8332
rpcallowip=127.0.0.1

noconnect=1
```

### Environment variables

`bitcoin-peer-rotate` uses the following environment variables.
You will need to set them only if the default values differ from your Bitcoin Core installation.

| Environment variable name    | Default value          |
|------------------------------|:-----------------------|
| BITCOIN_DIR                  | $HOME/.bitcoin         |
| BITCOIN_RPC_HOST             | localhost              |
| BITCOIN_RPC_PORT             | 8332                   |
| BITCOIN_RPC_COOKIE_AUTH_PATH | $HOME/.bitcoin/.cookie |

### Rotate

If you intend to connect to IPv4 peers only, simply run:

```
bitcoin-peer-rotate
```

This will remove existing peers and add 20 randomly selected IPv4 peers to your
Bitcoin Core node to allow it to maintain active connections with 8 of these
peers at any one time.

For periodic rotation, add `bitcoin-peer-rotate` to your cronjob entries.
Daily rotation could look like this in your crontab:

```
0 0 * * * bitcoin-peer-rotate
```

See `bitcoin-peer-rotate -h` for more options, e.g. for filtering by network
types, ASNs, countries, and speed percentile.

### Sample log

```
$ bitcoin-peer-rotate --limit 8
2023-05-01 11:37:41,925 - INFO - effective args - types=['ipv4'] - asns=[] - country_codes=[] - speed=1 - limit=8 - keep=[]
2023-05-01 11:37:42,529 - INFO - purging existing peers
2023-05-01 11:37:42,535 - INFO - removing peers from addednode - addr=91.19.101.14:8333
2023-05-01 11:37:42,537 - INFO - removing peers from addednode - addr=70.121.103.126:8333
2023-05-01 11:37:42,538 - INFO - removing peers from addednode - addr=87.98.243.138:8333
2023-05-01 11:37:42,539 - INFO - removing peers from addednode - addr=209.89.249.203:8333
2023-05-01 11:37:42,540 - INFO - removing peers from addednode - addr=159.246.25.52:8333
2023-05-01 11:37:42,540 - INFO - removing peers from addednode - addr=66.25.136.85:8333
2023-05-01 11:37:42,541 - INFO - removing peers from addednode - addr=193.42.110.30:8333
2023-05-01 11:37:42,542 - INFO - removing peers from addednode - addr=75.40.189.179:8333
2023-05-01 11:37:42,542 - INFO - peers purged=8
2023-05-01 11:37:42,542 - INFO - new peer - addr=91.19.101.14:8333 - data={'user_agent': '/Satoshi:24.0.1/', 'services': 1033, 'height': 787721, 'cc': 'DE', 'asn': 'AS3320', 'org': 'Deutsche Telekom AG', 'type': 'ipv4', 'mbps': 18.181859}
2023-05-01 11:37:42,543 - INFO - new peer - addr=70.121.103.126:8333 - data={'user_agent': '/Satoshi:24.0.1/', 'services': 1033, 'height': 787723, 'cc': 'US', 'asn': 'AS11427', 'org': 'TWC-11427-TEXAS', 'type': 'ipv4', 'mbps': 6.721767}
2023-05-01 11:37:42,543 - INFO - new peer - addr=87.98.243.138:8333 - data={'user_agent': '/Satoshi:22.0.0/', 'services': 1032, 'height': 787723, 'cc': 'FR', 'asn': 'AS16276', 'org': 'OVH SAS', 'type': 'ipv4', 'mbps': 84.46897}
2023-05-01 11:37:42,544 - INFO - new peer - addr=209.89.249.203:8333 - data={'user_agent': '/Satoshi:22.0.0/', 'services': 1033, 'height': 787700, 'cc': 'CA', 'asn': 'AS852', 'org': 'TELUS Communications', 'type': 'ipv4', 'mbps': 5.394991}
2023-05-01 11:37:42,545 - INFO - new peer - addr=159.246.25.52:8333 - data={'user_agent': '/Satoshi:24.0.1/', 'services': 1033, 'height': 787723, 'cc': 'US', 'asn': 'AS30491', 'org': 'CROWELLP', 'type': 'ipv4', 'mbps': 8.010063}
2023-05-01 11:37:42,545 - INFO - new peer - addr=66.25.136.85:8333 - data={'user_agent': '/Satoshi:22.0.0/', 'services': 1033, 'height': 787723, 'cc': 'US', 'asn': 'AS11427', 'org': 'TWC-11427-TEXAS', 'type': 'ipv4', 'mbps': 4.662538}
2023-05-01 11:37:42,546 - INFO - new peer - addr=193.42.110.30:8333 - data={'user_agent': '/Satoshi:22.0.0/', 'services': 1032, 'height': 787723, 'cc': 'NL', 'asn': 'AS60144', 'org': '3W Infra B.V.', 'type': 'ipv4', 'mbps': 12.099487}
2023-05-01 11:37:42,546 - INFO - new peer - addr=75.40.189.179:8333 - data={'user_agent': '/Satoshi:22.0.0/', 'services': 1033, 'height': 787723, 'cc': 'US', 'asn': 'AS7018', 'org': 'ATT-INTERNET4', 'type': 'ipv4', 'mbps': 6.546299}
```

### Reverting back to normal operation

To revert your local Bitcoin Core node to operate normally without
`bitcoin-peer-rotate`, simply remove the configuration described in the
*Install* section above from your `~/.bitcoin/bitcoin.conf` file and restart
your Bitcoin Core node.

## Package development

### Setup

```
~/.pyenv/versions/3.11.2/bin/python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

### Test

```
./test.sh
```

### Format

```
./format.sh
```

### Build

```
./build.sh
```
