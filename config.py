import argparse
import sys
import logging
import os
from datetime import datetime
from Lighthouse.lighthouse import Lighthouse, clients, connect

def setup_logging(script_name):
    """
    Configures logging to both console and a file.
    """
    if not os.path.exists("logs"):
        os.makedirs("logs")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/{script_name}_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_file

def parse_args():
    """
    Parses command line arguments for client name and environment.
    """
    parser = argparse.ArgumentParser(description="Lighthouse API Enrollment Utility")
    parser.add_argument("client", help="Name of the client (e.g., petroreconcavo, prio)")
    parser.add_argument("environment", nargs="?", default="dev", help="Environment (dev or prod). Defaults to dev.")
    
    return parser.parse_args()

def get_lighthouse_client(client_name, environment, debug=True):
    """
    Initializes and returns a Lighthouse API client based on configuration.
    """
    return connect(client_name, environment, debug)