#!/usr/bin/env python3

import argparse
import logging
import logging.handlers
import os
import re
import time
import requests
import json
import sys


def dir_path(path):
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"Path {path} is not a valid directory")


def setup_logger(stderr_log_lvl):
    """
    Create logger that logs to both stderr and log file but with different log levels
    """
    # Remove all handlers from root logger if any
    logging.basicConfig(
        level=logging.NOTSET, handlers=[]
    )  # `force=True` was added in Python 3.8 :-(
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


from html.parser import HTMLParser
from html.entities import name2codepoint

class MyHTMLParser(HTMLParser):
    suspected = None
    matches = {}

    def handle_starttag(self, tag, attrs):
        self.suspected = None
        if tag == "a":
            for attr in attrs:
                if len(attr) != 2:
                    continue
                if attr[0] != "href":
                    continue
                if not attr[1].startswith("/nastaveni-tarifu-a-sluzeb/"):
                    continue
                if not attr[1].split("/")[2].isnumeric():
                    continue
                self.suspected = attr[1].split("/")[2]

    def handle_endtag(self, tag):
        self.suspected = None

    def handle_data(self, data):
        if self.suspected is None:
            return
        data_strip = data.strip()
        if not data_strip.isnumeric():
            return
        self.matches[data_strip] = self.suspected
        self.suspected = None


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
        "--save-as",
        type=dir_path,
        help="Adresář kam zapsat zjištěná soubory se zjištěnými daty, pojmenované '<tel_cislo>.json'",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Pokud soubor poskytnutý v '--save-as ...' existuje, přepiš ho",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show verbose output",
    )
    parser.add_argument(
        "-d",
        "--debug",
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
    response = session.post("https://moje.o2family.cz/", data=data)
    response.raise_for_status()
    logger.debug(f"Cookies after login: {session.cookies}")  # Expect to see PHPSESSID

    # Parse phone number IDs
    ###print(response.text)
    parser = MyHTMLParser()
    parser.feed(response.text)
    for phone_number, phone_id in parser.matches.items():
        logger.info(f"Working on number {phone_number} id {phone_id}")

        # Get info about phone number
        response = session.get(f"https://moje.o2family.cz/api/tariff-info/{phone_id}")
        response.raise_for_status()
        logger.debug(f"Received: {response.json()}")

        if args.save_as is not None:
            save_as_file = os.path.join(args.save_as, f"{phone_number}.json")
            if os.path.exists(save_as_file):
                if args.force:
                    os.remove(save_as_file)
                    logger.debug(f"Removed {save_as_file}")
                else:
                    logger.error(
                        f"File {save_as_file} already exists. If you want to override it, use option '--force'"
                    )
                    return 1
            with open(save_as_file, "w") as fp:
                json.dump(response.json(), fp)
                logger.info(f"Dumped data to {save_as_file}")


if __name__ == "__main__":
    sys.exit(main() or 1)
