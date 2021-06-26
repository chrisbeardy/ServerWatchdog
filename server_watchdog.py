#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from logging.handlers import RotatingFileHandler
import json
import requests
import smtplib
from dataclasses import dataclass
from sys import exit


def check_servers(servers, gmail):
    downed_servers = []
    for server_name, address in servers.items():
        try:
            logger.debug(f"Testing server '{server_name}' on address '{address}'")
            status = requests.get(address, timeout=60)
            if status.status_code != 200:
                logger.warning(f"Server '{server_name}' on address '{address}' responded with non 200 status code")
                downed_servers.append(server_name)
        except Exception as e:
            logger.warning(f"Server '{server_name}' on address '{address}' could not be reached")
            logger.warning(e)
            downed_servers.append(server_name)

    if not downed_servers:
        return

    try:
        server = smtplib.SMTP(gmail.smtp_server, gmail.smtp_port)
        server.starttls()
        server.login(gmail.username, gmail.password)
        header = "Subject: Server down alert\n\n"
        message = ""
        for server_name in downed_servers:
            message += f"Name: {server_name}, Address: {servers[server_name]}\n"
        message = f"The following servers are not correctly responding to requests:\n{message}"
        message = header + message
        server.sendmail(gmail.username, [gmail.username], message)
        server.quit()
    except Exception as e:
        logger.error("Failed to send warning email")
        logger.error(e)


@dataclass
class Gmail:
    smtp_server: str
    smtp_port: str
    username: str
    password: str
    timezone: str


if __name__ == '__main__':
    # logging
    log_handler = RotatingFileHandler("server_watchdog.log", maxBytes=20000, backupCount=2)
    log_formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d - %(levelname)s - %(filename)s:%(lineno)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    log_handler.setFormatter(log_formatter)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(log_handler)

    # config
    try:
        with open("server_watchdog.json") as file:
            config = json.load(file)
    except (IOError, FileNotFoundError, json.JSONDecodeError):
        logger.critical("Config file not OK")
        exit()
    try:
        ips = config["ips"]
        ports = config["ports"]
        names = config["names"]
        https = config["https"]
        if type(ips) is not list:
            ips = [ips]
        if type(ports) is not list:
            ports = [ports]
        if type(names) is not list:
            names = [names]
        if not (len(ips) == len(ports) == len(names) == len(https)):
            logger.critical("Config file inaccurate, server lists not the same size")
            exit()
        servers = {}
        for ip, port, name, secure in zip(ips, ports, names, https):
            if not secure:
                servers[name] = f"http://{ip}:{port}"
            else:
                servers[name] = f"https://{ip}:{port}"

        gmail = Gmail(
            config["smtp_server"],
            config["smtp_port"],
            config["username"],
            config["password"],
            config["timezone"],
        )
    except Exception as e:
        logger.critical("Config file inaccurate")
        logger.critical(e)
        exit()

    check_servers(servers, gmail)




