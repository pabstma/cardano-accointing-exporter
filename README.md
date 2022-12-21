# Cardano Accointing Exporter

Note: This software is a private project and comes without any warranty. Use it at your own risk!

## What is this for?
This script was specifically made to create an importable history for accointing.com for your Cardano wallets.
It uses the api provided by blockfrost.io to get the needed data from the blockchain without the need to run a node and
the toolchain needed to parse it.

## How does it work?
The script parses every file in the wallets/ subdirectory with the ending .wallet
It is expected that a .wallet file contains exactly one address per line or exactly one stake key.

0. Make sure you that python3 and virtualenv is installed
1. Create a free account at https://blockfrost.io/ and find your project id.
2. Put your project id into the PROJECT_ID variable in the config.py
3. Create a wallets/ subdirectory in the scripts root directory
4. Create a .wallet file for every wallet in the wallets/ subdirectory as described above
5. Create a virtual environment 'virtualenv venv' and source it 'source venv/bin/activate'
6. Install the dependencies 'pip install -r requirements.txt'
7. Run the script 'python3 cardano-accointing-exporter.py'

It will output two files for every found .wallet file: a .csv and a .xlsx file
The xlsx file can be directly imported into accointing.

This script also caches already requested data. Thus reducing the api calls to blockfrost significantly. At the first
execution the script may take its time. But it should be much faster in subsequent runs. Data that does not change e.g.
old blocks or transactions are cached indefinitely. Data that frequently changes expires in the cache after a 
configurable amount of time. The default expiry for an accounts reward history is 5 days and for the transactions of an 
address 24 hours. Thus, no new rewards or transactions will be recognized within these 5 days or 24 hours caching 
period. You can always adjust those caching times to your needs in the config.py file.