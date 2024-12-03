import customtkinter as ctk
import serial
import time
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import serial.tools.list_ports

arduino = None
connected = False

def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def connect_port():
    global arduino, connected
    selected_port = cb.get()
    try:
        arduino = serial.Serial(port=selected_port, baudrate=9600, timeout=1)
        connected = True
        update_led()
    except Exception as e:
        print(f"Error connecting to {selected_port}: {e}")

def disconnect_port():
    global arduino, connected
    if arduino is not None:
        arduino.close()
        connected = False
        update_led()

def update_port():
    ports = list_serial_ports()  # Get the updated list of ports
    cb['values'] = ports  # Update the combobox with new port values
    if ports:
        cb.current(0)  # Set the first port as the current selection
    else:
        cb.set('No ports available')  # Set a message if no ports are found

def update_led():
    if connected:
        led_label.configure(fg_color="green")  # Update LED color
    else:
        led_label.configure(fg_color="red")    # Update LED color

rpm_data = []
time_data = []

def send_command(command):
    if arduino.is_open:
        arduino.write((command + '\n').encode('utf-8'))
        time.sleep(0.1)

def update_pid():
    kp = kp_entry.get()
    ki = ki_entry.get()
    kd = kd_entry.get()
    send_command(f"Kp={kp}")
    send_command(f"Ki={ki}")
    send_command(f"Kd={kd}")

def set_rpm():
    rpm = rpm_entry.get()
    send_command(f"R={rpm}")

def set_direction():
    direction = direction_var.get()
    send_command(f"D={direction}")

def start_motor():
    send_command("C=GO")
    start_data_collection()

def stop_motor():
    send_command("C=STOP")
    stop_data_collection()

def collect_data():
    while True:
        if arduino.is_open:
            line = arduino.readline().decode('utf-8').strip()
            if line.startswith("RPM"):
                try:
                    parts = line.split(':')
                    if len(parts) == 2:
                        rpm = int(parts[1])
                        current_time = time.time() - start_time
                        rpm_data.append(rpm)
                        time_data.append(current_time)
                except ValueError:
                    print(f"ValueError: Unable to convert RPM value: {line}")
                except Exception as e:
                    print(f"Unexpected error: {e}")
            elif line.startswith("Dir"):
                try:
                    parts = line.split(':')
                    if len(parts) == 2:
                        direction = int(parts[1].strip())
                        direction_value.configure(text="Clockwise (CW)" if direction == -1 else "Counter-Clockwise (CCW)")
                except ValueError:
                    print(f"ValueError: Unable to convert direction value: {line}")
                except Exception as e:
                    print(f"Unexpected error: {e}")

def start_data_collection():
    global start_time
    start_time = time.time()
    threading.Thread(target=collect_data, daemon=True).start()
    update_plot()

def stop_data_collection():
    global rpm_data, time_data
    rpm_data = []
    time_data = []

def reset_plot():
    global rpm_data, time_data
    rpm_data = []
    time_data = []
    ax.clear()
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('RPM / Error')
    ax.set_title('RPM vs Time and Error')
    canvas.draw()

def update_plot():
    ax.clear()
    if time_data:
        ax.plot(time_data, rpm_data, label='RPM', color='blue')
        target_rpm = float(rpm_entry.get()) if rpm_entry.get() else 0
        error_data = [target_rpm - rpm for rpm in rpm_data]
        ax.plot(time_data, error_data, label='Error', color='red')
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('RPM / Error')
        ax.set_title('RPM vs Time and Error')
        ax.legend()

        ax.text(0.95, 0.95, f'Current RPM: {rpm_data[-1] if rpm_data else 0}', 
                verticalalignment='top', horizontalalignment='right', 
                transform=ax.transAxes, fontsize=10, bbox=dict(facecolor='white', alpha=0.5))
        ax.text(0.95, 0.90, f'Direction: {direction_var.get()}', 
                verticalalignment='top', horizontalalignment='right', 
                transform=ax.transAxes, fontsize=10, bbox=dict(facecolor='white', alpha=0.5))

    canvas.draw()
    root.after(1000, update_plot)

def update_metrics():
    if rpm_data:
        target_rpm = float(rpm_entry.get())
        steady_state_error = abs(target_rpm - rpm_data[-1])
        sampling_time = time_data[-1] - time_data[0] if len(time_data) > 1 else 0
        peak_time = time_data[rpm_data.index(max(rpm_data))] if rpm_data else 0
        rise_time = 0
        if rpm_data:
            for i in range(len(rpm_data)):
                if rpm_data[i] >= 0.9 * target_rpm:
                    rise_time = time_data[i]
                    break
        overshoot = (max(rpm_data) - target_rpm) if rpm_data else 0

        steady_state_error_value.configure(text=f"{steady_state_error:.2f}")
        sampling_time_value.configure(text=f"{sampling_time:.2f}")
        peak_time_value.configure(text=f"{peak_time:.2f}")
        rise_time_value.configure(text=f"{rise_time:.2f}")
        overshoot_value.configure(text=f"{overshoot:.2f}")
        rpm_value.configure(text=f"{rpm_data[-1]}")  # Latest RPM
        direction_value.configure(text=direction_var.get())  # Current direction

    root.after(1000, update_metrics)  # Update every second

# Set up main window
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("dark-blue")

root = ctk.CTk()
root.title("Arduino Motor Control GUI")
root.geometry("1200x700")

# Frame for controls on the left
control_frame = ctk.CTkFrame(root)
control_frame.pack(side="left", fill="y", padx=10, pady=10)

# Serial port selection

cb = ctk.CTkComboBox(control_frame, values=list_serial_ports())
cb.pack(side="top", pady=5)

connect_button = ctk.CTkButton(control_frame, text="Connect", command=connect_port)
connect_button.pack(side="top", padx=5, pady=5)

disconnect_button = ctk.CTkButton(control_frame, text="Disconnect", command=disconnect_port)
disconnect_button.pack(side="top", padx=5, pady=5)

led_label = ctk.CTkLabel(control_frame, text="Connection Status", width=20, height=2)
led_label.pack(pady=10)
update_led()

update_port_button = ctk.CTkButton(control_frame, text="Update Port", command=update_port)
update_port_button.pack(side="top", padx=5, pady=5)

# PID parameters
ctk.CTkLabel(control_frame, text="Kp:").pack(side="top", anchor="w")
kp_entry = ctk.CTkEntry(control_frame)
kp_entry.pack(side="top", pady=5)

ctk.CTkLabel(control_frame, text="Ki:").pack(side="top", anchor="w")
ki_entry = ctk.CTkEntry(control_frame)
ki_entry.pack(side="top", pady=5)

ctk.CTkLabel(control_frame, text="Kd:").pack(side="top", anchor="w")
kd_entry = ctk.CTkEntry(control_frame)
kd_entry.pack(side="top", pady=5)

update_pid_button = ctk.CTkButton(control_frame, text="Set PID", command=update_pid)
update_pid_button.pack(side="top", pady=5)

# RPM settings
ctk.CTkLabel(control_frame, text="RPM:").pack(side="top", anchor="w")
rpm_entry = ctk.CTkEntry(control_frame)
rpm_entry.pack(side="top", pady=5)

set_rpm_button = ctk.CTkButton(control_frame, text="Set RPM", command=set_rpm)
set_rpm_button.pack(side="top", pady=5)

# Direction settings
direction_var = ctk.StringVar(value="CW")
ctk.CTkRadioButton(control_frame, text="Clockwise (CW)", variable=direction_var, value="CW").pack(side="top", anchor="w")
ctk.CTkRadioButton(control_frame, text="Counter-Clockwise (CCW)", variable=direction_var, value="CCW").pack(side="top", anchor="w")

set_direction_button = ctk.CTkButton(control_frame, text="Set Direction", command=set_direction)
set_direction_button.pack(side="top", pady=5, padx=5)

start_button = ctk.CTkButton(control_frame, text="Start", command=start_motor)
start_button.pack(side="top", padx=5)

stop_button = ctk.CTkButton(control_frame, text="Stop", command=stop_motor)
stop_button.pack(side="top", padx=5)

reset_button = ctk.CTkButton(control_frame, text="Reset Plot", command=reset_plot)
reset_button.pack(side="top", padx=5)

# Frame for plotting
plot_frame = ctk.CTkFrame(root)
plot_frame.pack(fill="both", expand=True, padx=5, pady=5)

fig, ax = plt.subplots()
canvas = FigureCanvasTkAgg(fig, master=plot_frame)
canvas.get_tk_widget().pack(fill="both", expand=True)

# Frame for performance metrics
metrics_frame = ctk.CTkFrame(root)
metrics_frame.pack(fill="x", padx=10, pady=5)

steady_state_error_label = ctk.CTkLabel(metrics_frame, text="Steady State Error:")
steady_state_error_label.grid(row=0, column=0, sticky="w")

steady_state_error_value = ctk.CTkLabel(metrics_frame, text="0")  # Placeholder for value
steady_state_error_value.grid(row=0, column=2, sticky="w")

sampling_time_label = ctk.CTkLabel(metrics_frame, text="Sampling Time:")
sampling_time_label.grid(row=1, column=0, sticky="w")

sampling_time_value = ctk.CTkLabel(metrics_frame, text="0")  # Placeholder for value
sampling_time_value.grid(row=1, column=2, sticky="w")

peak_time_label = ctk.CTkLabel(metrics_frame, text="Peak Time:")
peak_time_label.grid(row=2, column=0, sticky="w")

peak_time_value = ctk.CTkLabel(metrics_frame, text="0")  # Placeholder for value
peak_time_value.grid(row=2, column=2, sticky="w")

rise_time_label = ctk.CTkLabel(metrics_frame, text="Rise Time:")
rise_time_label.grid(row=3, column=0, sticky="w")

rise_time_value = ctk.CTkLabel(metrics_frame, text="0")  # Placeholder for value
rise_time_value.grid(row=3, column=2, sticky="w")

overshoot_label = ctk.CTkLabel(metrics_frame, text="Overshoot:")
overshoot_label.grid(row=4, column=0, sticky="w")

overshoot_value = ctk.CTkLabel(metrics_frame, text="0")  # Placeholder for value
overshoot_value.grid(row=4, column=2, sticky="w")

rpm_label = ctk.CTkLabel(metrics_frame, text="Current RPM:")
rpm_label.grid(row=5, column=0, sticky="w")

rpm_value = ctk.CTkLabel(metrics_frame, text="0")  # Placeholder for value
rpm_value.grid(row=5, column=2, sticky="w")

direction_label = ctk.CTkLabel(metrics_frame, text="Motor Direction:")
direction_label.grid(row=6, column=0, sticky="w")

direction_value = ctk.CTkLabel(metrics_frame, text="CW")  # Placeholder for value
direction_value.grid(row=6, column=2, sticky="w")

# Start updating metrics when the application starts
update_metrics()

# Run the GUI
root.mainloop()

# Close serial communication when the application exits
if arduino is not None:
    arduino.close()