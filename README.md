# Cardano Accointing Exporter

This software is provided "as is" without any warranty or liability. Use it at your own risk.

## Purpose

The purpose of this program is to recreate the transaction history of your Cardano wallets. It uses APIs from [blockfrost.io](https://blockfrost.io/) and [koios.rest](https://www.koios.rest/) to gather data from the Cardano blockchain without the need for running a node or toolchain. Price information is provided by [coingecko](https://www.coingecko.com/en/api). It initially supported the use of an exporter for the [accointing](https://www.accointing.com/) crypto portfolio tracker and crypto tax software, but also provides a generic exporter and the ability to write custom exporters for your desired data format.

## Functionality

The program reads every file with a '.wallet' extension in the 'wallets/' subdirectory and recreates the transaction history of each wallet using the specified exporter. It outputs two files for each '.wallet' file: a '.csv' and a '.xlsx' file. For example, using the accointing exporter, the '.xlsx' file can be directly imported into accointing.

## Usage

1. Ensure that python3 and virtualenv are installed
2. Create a free account on [blockfrost.io](https://blockfrost.io/) and find your project ID
3. Put your project ID in either a 'project.id' file in the root directory or the 'PROJECT_ID' variable in 'config.py'
4. Create a 'wallets/' subdirectory in the script's root directory
5. Create a '.wallet' file for each wallet in the 'wallets/' subdirectory, as described above
6. Create a virtual environment with 'virtualenv venv' and activate it with 'source venv/bin/activate'
7. Install dependencies with 'pip install -r requirements.txt'
8. Check the help section with 'python3 cardano-accointing-exporter.py -h'
9. Run the program with desired settings

## Notes

The program uses a multi-stage cache approach with in-memory and on-disk caching for API requests, reducing API calls and improving performance. On first execution, the script may take some time, but subsequent runs will be faster. Cached data, such as old blocks or transactions, is stored indefinitely, while frequently changing data expires after a configurable amount of time. You can adjust the caching times in 'config.py' to meet your needs. When recreating the transaction history for many wallets with large amounts of transactions (50k+), the in-memory cache may consume several GB of memory. To avoid memory issues, either run the calculation on fewer wallets at once or set a 'cache_limit' in 'config.py' to limit memory consumption.
