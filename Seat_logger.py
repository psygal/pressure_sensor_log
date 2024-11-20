import time
import numpy as np
import serial
from datetime import datetime
import csv
import os
import json
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from scipy.ndimage import zoom
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sys
import threading

# MATRIX FOR THE PRESSURE DATA
COLS = 20
ROWS = 20
NEW_COLS = 60
NEW_ROWS = 60
Values = np.zeros((ROWS, COLS))

ser = serial.Serial(
    port='COM3',
    baudrate=115200,
    timeout=0.05
)

time.sleep(0.5)
ser.write("S".encode())

# Generate a unique timestamp for the CSV file
timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
csv_file = f'logged_pressure_{timestamp}.csv'

# Create the CSV file with a header if it doesn't exist
if not os.path.exists(csv_file):
    with open(csv_file, mode='w', newline='') as f:
        writer = csv.writer(f)
        header = ['Timestamp'] + [f'Pressure_{i+1}_{j+1}' for i in range(ROWS) for j in range(COLS)]
        writer.writerow(header)

collecting_data = False
csv_file_handle = open(csv_file, mode='a', newline='')
csv_writer = csv.writer(csv_file_handle)

def log_message(message):
    """Display messages in the GUI log box."""
    log_text.config(state=tk.NORMAL)
    log_text.insert(tk.END, f"{message}\n")
    log_text.see(tk.END)
    log_text.config(state=tk.DISABLED)

def ReceiveRow(i):
    x = 0
    while x < ROWS:
        HighByte = ser.read()
        LowByte = ser.read()
        high = int.from_bytes(HighByte, 'big')
        low = int.from_bytes(LowByte, 'big')
        val = 4096 - ((low << 8) + high)
        Values[x][i] = np.clip(val, 0, 300)
        x += 1
    xbyte = ser.read().decode('utf-8')
    if xbyte != "\n":
        log_message('Communication Error')

def ReceiveMap():
    y = 0
    while y < COLS:
        xbyte = ser.read().decode('utf-8')
        if xbyte == 'M':
            xbyte = ser.read()
            xint = int.from_bytes(xbyte, 'big')
            if xint == ROWS:
                xbyte = ser.read()
                xint = int.from_bytes(xbyte, 'big')
                ReceiveRow(xint)
        y += 1

def request_new_data():
    ser.write("S".encode())

def log_data():
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    bValues = Values.tolist()
    row_data = [timestamp] + [item for sublist in bValues for item in sublist]
    csv_writer.writerow(row_data)
    csv_file_handle.flush()
    log_message(f"Data logged at {timestamp}")

def update_heatmap(frame):
    global Values, collecting_data

    if not collecting_data:
        return

    resized_values = zoom(Values, (NEW_ROWS / ROWS, NEW_COLS / COLS), order=1)
    heatmap.set_data(resized_values)
    canvas.draw()

def start_collection():
    global collecting_data
    if not collecting_data:
        collecting_data = True
        log_message("Data collection started.")
        threading.Thread(target=receive_data_thread).start()

def stop_collection():
    global collecting_data
    collecting_data = False
    log_message("Data collection stopped.")

def exit_program():
    global collecting_data
    collecting_data = False

    try:
        # Close the serial connection and CSV file
        ser.close()
        csv_file_handle.close()
        log_message("Serial connection closed and CSV file saved.")

        # Close the Matplotlib plot
        plt.close('all')

        # Exit the Tkinter main loop
        root.quit()

        # Restore terminal settings (for UNIX-based systems)
        if os.name != 'nt':  # Only needed for non-Windows systems
            import termios
            import tty
            tty.setcbreak(sys.stdin.fileno())
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, termios.tcgetattr(sys.stdin))
    except Exception as e:
        log_message(f"Error during exit: {e}")

    # Exit the script
    sys.exit(0)

def receive_data_thread():
    while collecting_data:
        while ser.in_waiting > 0:
            xbyte = ser.read().decode('utf-8')
            if xbyte == 'H':
                ser.read()
                ser.read().decode('utf-8')
                ReceiveMap()
                log_data()
                request_new_data()
        time.sleep(0.05)  # Adjust sleep to control the polling frequency

root = tk.Tk()
root.title("Pressure Sensor Data Logger")

fig, ax = plt.subplots(figsize=(8, 6))
heatmap = ax.imshow(np.zeros((NEW_ROWS, NEW_COLS)), cmap='viridis', interpolation='nearest', vmin=0, vmax=300)
ax.set_title("Live Pressure Data Heatmap")
fig.colorbar(heatmap, ax=ax)

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack()

start_button = tk.Button(root, text="Start", command=start_collection)
start_button.pack(pady=10)

stop_button = tk.Button(root, text="Stop", command=stop_collection)
stop_button.pack(pady=10)

exit_button = tk.Button(root, text="Exit", command=exit_program)
exit_button.pack(pady=10)

# Text widget for displaying log messages
log_text = tk.Text(root, height=10, state=tk.DISABLED)
log_text.pack(pady=10)

ani = animation.FuncAnimation(fig, update_heatmap, interval=10, cache_frame_data=False)

root.mainloop()
