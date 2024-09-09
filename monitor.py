import psutil
import time
import logging
import argparse
import signal
import configparser

# Default configuration file
CONFIG_FILE = 'monitor_config.ini'

# Configure logging
logging.basicConfig(filename='server_monitor.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Global variable to control the monitoring loop
running = True

def load_config():
    """Load configuration from file."""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    cpu_threshold = int(config.get('Thresholds', 'cpu_threshold', fallback=80))
    memory_threshold = int(config.get('Thresholds', 'memory_threshold', fallback=80))
    disk_threshold = int(config.get('Thresholds', 'disk_threshold', fallback=80))
    network_threshold = int(config.get('Thresholds', 'network_threshold', fallback=1000))  # in KB/s
    temperature_threshold = int(config.get('Thresholds', 'temperature_threshold', fallback=70))  # in degrees Celsius
    io_wait_threshold = int(config.get('Thresholds', 'io_wait_threshold', fallback=10))  # in percent
    return cpu_threshold, memory_threshold, disk_threshold, network_threshold, temperature_threshold, io_wait_threshold

def get_system_metrics():
    """Retrieve CPU, memory, disk, network, temperature, and I/O wait time usage metrics."""
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()
    disk_usage = psutil.disk_usage('/').percent

    net_io = psutil.net_io_counters()
    network_usage = (net_io.bytes_sent + net_io.bytes_recv) / 1024  # Convert to KB

    temperature = "N/A"
    if hasattr(psutil, 'sensors_temperatures'):
        temperature_info = psutil.sensors_temperatures()
        if temperature_info:
            # Assume the first sensor and the first reading for simplicity
            temperature = list(temperature_info.values())[0][0].current
        else:
            logging.info("Temperature sensor data not available.")

    cpu_times = psutil.cpu_times_percent(interval=1)
    io_wait = getattr(cpu_times, 'iowait', 0)  # Use 0 if iowait is not available

    return {
        "CPU Usage": f"{cpu_usage:.2f}%",
        "Memory Usage": f"{memory_info.percent}%",
        "Disk Usage": f"{disk_usage:.2f}%",
        "Network Usage": f"{network_usage:.2f} KB/s",
        "Temperature": f"{temperature:.2f}°C" if temperature != "N/A" else "N/A",
        "I/O Wait Time": f"{io_wait:.2f}%"
    }

def log_metrics(metrics):
    """Log metrics to the file."""
    for key, value in metrics.items():
        logging.info(f"{key}: {value}")

def check_alerts(metrics, cpu_threshold, memory_threshold, disk_threshold, network_threshold, temperature_threshold, io_wait_threshold):
    """Check if metrics exceed threshold values and log warnings."""
    try:
        cpu_usage = float(metrics["CPU Usage"].rstrip('%'))
        memory_usage = float(metrics["Memory Usage"].rstrip('%'))
        disk_usage = float(metrics["Disk Usage"].rstrip('%'))
        network_usage = float(metrics["Network Usage"].rstrip(' KB/s'))
        temperature = float(metrics["Temperature"].rstrip('°C')) if metrics["Temperature"] != "N/A" else None
        io_wait = float(metrics["I/O Wait Time"].rstrip('%'))

        if cpu_usage > cpu_threshold:
            logging.warning(f"High CPU Usage Alert: {cpu_usage:.2f}%")

        if memory_usage > memory_threshold:
            logging.warning(f"High Memory Usage Alert: {memory_usage:.2f}%")

        if disk_usage > disk_threshold:
            logging.warning(f"High Disk Usage Alert: {disk_usage:.2f}%")

        if network_usage > network_threshold:
            logging.warning(f"High Network Usage Alert: {network_usage:.2f} KB/s")

        if temperature is not None and temperature > temperature_threshold:
            logging.warning(f"High Temperature Alert: {temperature:.2f}°C")

        if io_wait > io_wait_threshold:
            logging.warning(f"High I/O Wait Time Alert: {io_wait:.2f}%")

    except ValueError as e:
        logging.error(f"Error processing metrics: {e}")

def monitor_server(cpu_threshold, memory_threshold, disk_threshold, network_threshold, temperature_threshold, io_wait_threshold):
    """Monitor the system metrics and log them at intervals."""
    logging.info("Starting server monitoring...")
    while running:
        metrics = get_system_metrics()
        log_metrics(metrics)
        check_alerts(metrics, cpu_threshold, memory_threshold, disk_threshold, network_threshold, temperature_threshold, io_wait_threshold)
        print("System Metrics:")
        for key, value in metrics.items():
            print(f"{key}: {value}")
        print("-" * 30)
        time.sleep(10)  # Monitor every 10 seconds

def signal_handler(sig, frame):
    """Handle termination signals."""
    global running
    print("Shutting down gracefully...")
    running = False

def main():
    """Parse arguments and start monitoring."""
    parser = argparse.ArgumentParser(description='Monitor system metrics and log to a file.')
    args = parser.parse_args()

    # Load configuration
    cpu_threshold, memory_threshold, disk_threshold, network_threshold, temperature_threshold, io_wait_threshold = load_config()
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    monitor_server(cpu_threshold, memory_threshold, disk_threshold, network_threshold, temperature_threshold, io_wait_threshold)

if __name__ == "__main__":
    main()
