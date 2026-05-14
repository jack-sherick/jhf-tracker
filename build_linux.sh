#!/bin/sh
apt-get update -q
apt-get install -y -q binutils
pip install psycopg2-binary pyinstaller
pyinstaller jhf-tracker.spec
