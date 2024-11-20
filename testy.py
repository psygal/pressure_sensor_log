import numpy as np
import serial
import time
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import csv
from datetime import datetime
import tkinter as tk
from tkinter import scrolledtext
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# This connects to serial
ser = serial.Serial(
    # You might change the PORT corresponding to the assigned by Operative System
    'COM6',  # raspberry: '/dev/ttyUSB1'
    baudrate=115200,
    timeout=0.05
)

# Default parameters
ROWS = 48  # Rows of the sensor
COLS = 48  # Columns of the sensor

# Variable declaration
Values = np.zeros((ROWS, COLS))

# Create a unique CSV file for logging data
def create_csv_filename():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"pressure_data_{timestamp}.csv"

# Function to log data to a CSV file with a timestamp
def log_data_to_csv(data, filename):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp] + data.flatten().tolist())

def RequestPressureMap():
    data = "R"
    ser.write(data.encode())

def activePointsReceiveMap():
    global Values
    matrix = np.zeros((ROWS, COLS), dtype=int)

    xbyte = ser.read().decode('utf-8')

    HighByte = ser.read()
    LowByte = ser.read()
    high = int.from_bytes(HighByte, 'big')
    low = int.from_bytes(LowByte, 'big')
    nPoints = ((high << 8) | low)

    xbyte = ser.read().decode('utf-8')
    xbyte = ser.read().decode('utf-8')
    x = 0
    y = 0
    n = 0
    while(n < nPoints):
        x = ser.read()
        y = ser.read()
        x = int.from_bytes(x, 'big')
        y = int.from_bytes(y, 'big')
        HighByte = ser.read()
        LowByte = ser.read()
        high = int.from_bytes(HighByte, 'big')
        low = int.from_bytes(LowByte, 'big')
        val = ((high << 8) | low)
        matrix[y][x] = val
        n += 1
    Values = matrix

def activePointsGetMap():
    xbyte = ''
    if ser.in_waiting > 0:
        try:
            xbyte = ser.read().decode('utf-8')
        except Exception:
            print("Exception")
        if(xbyte == 'N'):
            activePointsReceiveMap()
        else:
            ser.flush()

class Null:
    def write(self, text):
        pass

    def flush(self):
        pass

def getMatrix():
    RequestPressureMap()
    activePointsGetMap()

# Function to update the heatmap in real-time
def update_heatmap(frame):
    getMatrix()  # This function requests and parses a pressure map in the variable Values
    heatmap.set_array(Values)  # Update the heatmap data

    # Log the data to CSV each time the heatmap updates
    log_data_to_csv(Values, csv_filename)

    # Add log entry to the log section
    log_section.insert(tk.END, f"Data captured at {datetime.now().strftime('%H:%M:%S')}\n")
    log_section.yview(tk.END)  # Scroll to the bottom

    return [heatmap]

# GUI Setup using Tkinter
def start_animation():
    global ani
    # Create the heatmap animation
    ani = animation.FuncAnimation(fig, update_heatmap, blit=True, interval=100)  # Update every 100ms
    canvas.draw()

def stop_animation():
    global ani
    ani.event_source.stop()
    log_section.insert(tk.END, f"Animation stopped at {datetime.now().strftime('%H:%M:%S')}\n")
    log_section.yview(tk.END)

def exit_app():
    root.quit()

# Set up the root Tkinter window
root = tk.Tk()
root.title("Pressure Sensor Heatmap")

# Create a unique CSV filename for logging
csv_filename = create_csv_filename()

# Setup the plot for real-time update in Tkinter
fig, ax = plt.subplots()
heatmap = ax.imshow(Values, cmap='hot', interpolation='nearest')
plt.colorbar(heatmap, ax=ax)
plt.title("Pressure Map Heatmap")
plt.xlabel("Columns")
plt.ylabel("Rows")

# Embed the Matplotlib figure in Tkinter window
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack()

# Create buttons for starting, stopping, and exiting
frame_buttons = tk.Frame(root)
frame_buttons.pack(pady=10)

btn_start = tk.Button(frame_buttons, text="Start", command=start_animation)
btn_start.grid(row=0, column=0, padx=5)

btn_stop = tk.Button(frame_buttons, text="Stop", command=stop_animation)
btn_stop.grid(row=0, column=1, padx=5)

btn_exit = tk.Button(frame_buttons, text="Exit", command=exit_app)
btn_exit.grid(row=0, column=2, padx=5)

# Log Section (ScrolledText Widget)
log_section = scrolledtext.ScrolledText(root, width=60, height=10, wrap=tk.WORD)
log_section.pack(pady=10)
log_section.insert(tk.END, "Log Section\n")

# Write headers to CSV (optional, only the first time)
with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Timestamp'] + [f"Column {i}" for i in range(COLS)] + [f"Row {i}" for i in range(ROWS)])

# Start the Tkinter event loop
root.mainloop()
