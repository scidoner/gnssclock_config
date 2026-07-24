import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

def parse_chrony_stats(file_path):
    """
    Parse chrony statistics log file and return a pandas DataFrame
    """
    # read file contents first
    with open(file_path, 'r') as f:
        file_contents = f.readlines()

    # for each line, if it starts with '=' or ' ', skip it
    file_contents = [line for line in file_contents if not line.startswith('=') and not line.startswith(' ')]

    # exclude lines that include 'PPS'
    file_contents = [line for line in file_contents if 'PPS' not in line]

    # Use StringIO to create a file-like object from the filtered contents
    from io import StringIO
    csv_data = StringIO(''.join(file_contents))

    # Read the filtered data using pandas
    df = pd.read_csv(csv_data,
                     sep=r"\s+",
                     names=['Date', 'Time', 'IP_Address', 'Std_dev', 'Est_offset', 'Offset_sd', 
                           'Diff_freq', 'Est_skew', 'Stress', 'Ns', 'Bs', 'Nr', 'Asym'])
    

    # Combine Date and Time columns into a datetime column
    df['timestamp'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
    
    return df

def plot_est_offset(df):
    """
    Create a plot of Est_offset vs time for each IP address
    """
    plt.figure(figsize=(12, 6))
    
    # Plot each IP address as a separate series
    for ip in df['IP_Address'].unique():
        ip_data = df[df['IP_Address'] == ip]
        plt.plot(ip_data['timestamp'], ip_data['Est_offset'], 
                marker='o', label=ip, linestyle='-', markersize=4)
    
    plt.xlabel('Time')
    plt.ylabel('Estimated Offset (seconds)')
    plt.title('Chrony Estimated Offset Over Time by IP Address')
    plt.legend()
    plt.grid(True)
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    return plt

def analyze_chrony_stats(file_path):
    """
    Main function to analyze chrony statistics
    """
    # Parse the data
    df = parse_chrony_stats(file_path)
    
    # Create summary statistics
    summary = {
        'IP Addresses': df['IP_Address'].nunique(),
        'Time Range': f"{df['timestamp'].min()} to {df['timestamp'].max()}",
        'Average Est Offset by IP': df.groupby('IP_Address')['Est_offset'].mean().to_dict(),
        'Max Est Offset by IP': df.groupby('IP_Address')['Est_offset'].max().to_dict(),
        'Min Est Offset by IP': df.groupby('IP_Address')['Est_offset'].min().to_dict(),
        'Median Est Offset by IP': df.groupby('IP_Address')['Est_offset'].median().to_dict()
    }
    
    # Create the plot
    plot = plot_est_offset(df)
    
    return df, summary, plot

# Example usage
if __name__ == "__main__":
    file_path = "chrony_statistics.log"  # Replace with your file path
    df, summary, plot = analyze_chrony_stats(file_path)
    
    # Print summary statistics
    print("\nChrony Statistics Summary:")
    print("-" * 30)
    print(f"Number of IP Addresses: {summary['IP Addresses']}")
    print(f"Time Range: {summary['Time Range']}")
    print("\nAverage Estimated Offset by IP:")
    for ip, avg in summary['Average Est Offset by IP'].items():
        print(f"{ip}: {avg:.2e}")

    print("\nMedian Estimated Offset by IP:")
    for ip, median in summary['Median Est Offset by IP'].items():
        print(f"{ip}: {median:.2e}")
    
    # Show the plot
    plt.show()