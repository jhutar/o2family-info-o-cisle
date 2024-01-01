#!/usr/bin/env python3

import argparse
import logging
import logging.handlers
import os
import time
import requests
import json
import sys


def setup_logger(stderr_log_lvl):
    """
    Create logger that logs to both stderr and log file but with different log levels
    """
    # Remove all handlers from root logger if any
    logging.basicConfig(level=logging.NOTSET, handlers=[])   # `force=True` was added in Python 3.8 :-(
    # Change root logger level from WARNING (default) to NOTSET in order for all messages to be delegated
    logging.getLogger().setLevel(logging.NOTSET)

    # Log message format
    formatter = logging.Formatter(
        "%(asctime)s %(name)s %(threadName)s %(levelname)s %(message)s"
    )
    formatter.converter = time.gmtime

    # Add stderr handler, with provided level
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(stderr_log_lvl)
    logging.getLogger().addHandler(console_handler)

    # Add file rotating handler, with level DEBUG
    rotating_handler = logging.handlers.RotatingFileHandler(
        filename=f"/tmp/o2family_info.log", maxBytes=100 * 1000, backupCount=2
    )
    rotating_handler.setFormatter(formatter)
    rotating_handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(rotating_handler)

    return logging.getLogger("root")

def main():
    parser = argparse.ArgumentParser(
        description="Získá informace o O2Family čísle z jejich samoobsluhy",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--username",
        required=True,
        type=str,
        help="Uživatelské jméno pro přihlášení do O2Family samoobsluhy",
    )
    parser.add_argument(
        "--password",
        required=True,
        type=str,
        help="Heslo pro přihlášení do O2Family samoobsluhy",
    )
    parser.add_argument(
        "--id",
        required=True,
        type=int,
        help="ID vašeho čísla v O2Family samoobsluze. Je v URL když po přihlášení na číslo klikáte pro zobrazení detailů.",
    )
    parser.add_argument(
        "--save-as",
        type=str,
        help="Soubor kam zapsat zjištěná data",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Pokud soubor poskytnutý v '--save-as ...' existuje, přepiš ho",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output",
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Show debug output",
    )
    args = parser.parse_args()

    if args.debug:
        logger = setup_logger(logging.DEBUG)
    elif args.verbose:
        logger = setup_logger(logging.INFO)
    else:
        logger = setup_logger(logging.WARNING)

    logger.debug(f"Args: {args}")

    session = requests.Session()
    data = {
        "_username": args.username,
        "_password": args.password,
        "_logintype": "login",
    }

    # Log in
    session.post("https://moje.o2family.cz/", data=data)
    logger.debug(f"Cookies after login: {session.cookies}")   # Expect to see PHPSESSID

    # Get info
    response = session.get(f"https://moje.o2family.cz/api/tariff-info/{args.id}")
    logger.info(f"Received: {response.json()}")

    if args.save_as is not None:
        if os.path.exists(args.save_as):
            if args.force:
                os.remove(args.save_as)
                logger.debug(f"Removed {args.save_as}")
            else:
                logger.error(f"File {args.save_as} already exists. If you want to override it, use option '--force'")
                return 1
        with open(args.save_as, 'w') as fp:
            json.dump(response.json(), fp)
            logger.info(f"Dumped data to {args.save_as}")


if __name__ == "__main__":
    sys.exit(main() or 1)
