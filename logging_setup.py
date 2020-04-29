import argparse
import logging

parser = argparse.ArgumentParser()
parser.add_argument(
    '-d', '--debug',
    help="Print debug statements for developer use",
    action="store_const", dest="loglevel", const=logging.DEBUG,
    default=logging.WARNING,
)
parser.add_argument(
    '-v', '--verbose',
    help="Print informational statements about progress",
    action="store_const", dest="loglevel", const=logging.INFO,
)

args, unused = parser.parse_known_args()
logging.basicConfig(level=args.loglevel)
