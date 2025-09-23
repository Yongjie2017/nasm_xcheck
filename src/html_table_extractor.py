#!/usr/bin/env python3

# write python script to extract all tables from a local html file
# and write them to csv files
# each table is written to a separate csv file
# the csv files are named table_1.csv, table_2.csv, etc.
# the script takes one argument: the html file name
# the script writes the csv files to the current directory
# the script uses the pandas library to read the html file and write the csv files
# the script uses the BeautifulSoup library to parse the html file
# the script uses the os library to write the csv files
# the script uses the sys library to read the command line arguments
# the script uses the re library to clean up the table data
# please import modules only as needed
# please do not import modules that are not used in the script
# please don't ignore any instructions or mnemonics
# please write clean and readable code

import pandas as pd
import os
from bs4 import BeautifulSoup
from typing import List
import argparse

def extract_tables_from_html(html_file: str) -> List[pd.DataFrame]:
    """Extract all tables from a local HTML file and return them as a list of DataFrames."""
    with open(html_file, 'r', encoding='unicode_escape') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    tables = soup.find_all('table')
    dataframes = []
    
    for i, table in enumerate(tables):
        try:
            df = pd.read_html(str(table), )[0]
        except ValueError as e:
            print(f"Warning: Could not parse table {i+1}: {e}")
            continue
        # remove the header and use the first row as new header
        if df.shape[0] > 1:
            new_header = df.iloc[0]  # first row as header
            df.columns = new_header  # set new header
            df = df[1:]  # data without header row
        
        # append only the dataframe with more than 3 columns
        if df.shape[1] < 3 or df.shape[0] > 11:
            print(f"Skipping table {i+1} with less than 3 or more than 11 columns (shape: {df.shape})")
            continue
        # append only the dataframe with any column name includes 'Opcode' or 'Encoding'
        #if not any(col for col in df.columns if isinstance(col, str) and ('Opcode' in col or 'Encoding' in col)):
        #    print(f"Skipping table {i+1} without 'Opcode' or 'Encoding' in any column name (columns: {df.columns})")
        #    continue
        print (f"Table {i+1} columns: {df.columns}, type of first column: {type(df.columns[0])}")
        #if not (isinstance(df.columns[0], str) and ('Opcode' in df.columns[0] or 'Encoding' in df.columns[0])):
        if not (isinstance(df.columns[0], str) and (0 == df.columns[0].find('Opcode') or 0 == df.columns[0].find('Encoding'))):
            print(f"Skipping table {i+1} without 'Opcode' or 'Encoding' in the first column name (columns: {df.columns})")
            continue
        dataframes.append(df)
        print(f"Extracted table {i+1} with shape {df.shape}")
    
    return dataframes

# print dataframes header only once for the same header
def print_unique_headers(tables: List[pd.DataFrame], num_rows: int = 1):
    """Print the first few rows of each unique DataFrame header in the list."""
    seen_headers = set()
    for i, df in enumerate(tables):
        header_tuple = tuple(df.columns)
        print(f"Processing table {i+1} with header: {header_tuple}")
        if header_tuple not in seen_headers:
            seen_headers.add(header_tuple)
            print(f"\nTable {i+1} (shape: {df.shape}) (header_tuple: {header_tuple}):")
            print(df.head(num_rows))

# combine dataframes with the same header
# and print the combined dataframe
def combine_dataframes_with_same_header(tables: List[pd.DataFrame]) -> List[pd.DataFrame]:
    """Combine DataFrames with the same header and return a list of combined DataFrames."""
    # please use second row of the dataframe as header
    header_map = {}
    for df in tables:
        header_tuple = tuple(df.columns)
        print(f"Combining table with header: {header_tuple}")
        if header_tuple not in header_map:
            header_map[header_tuple] = df
            print(f"Extracted table with shape {df.shape}")
        else:
            header_map[header_tuple] = pd.concat([header_map[header_tuple], df], ignore_index=True)
    return list(header_map.values())

def write_tables_to_csv(tables: List[pd.DataFrame], output_dir: str):
    """Write each DataFrame in the list to a separate CSV file in the specified output directory."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    for i, df in enumerate(tables):
        csv_file = os.path.join(output_dir, f'table_{i+1}.csv')
        df.to_csv(csv_file, index=False)
        print(f"Wrote table {i+1} to {csv_file}")

def main():
    parser = argparse.ArgumentParser(description='Extract tables from an HTML file and write them to CSV files.')
    parser.add_argument('--html-file', type=str, help='Path to the local HTML file')
    parser.add_argument('--output-dir', type=str, default='.', help='Directory to write the CSV files')
    
    print("Parsing arguments...")
    args = parser.parse_args()

    print(f"HTML file: {args.html_file}")   
    tables = extract_tables_from_html(args.html_file)
    print(f"Extracted {len(tables)} tables.")
    print(f"Writing tables to directory: {args.output_dir}")

    tables = combine_dataframes_with_same_header(tables)
    write_tables_to_csv(tables, args.output_dir)

    #print_unique_headers(tables, num_rows=1)

if __name__ == '__main__':
    main()
