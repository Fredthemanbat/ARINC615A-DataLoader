import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import paramiko
import zlib
import os
from pathlib import Path
import threading


TARGET_IP = 0
SSH_USER = 0
SSH_PASSWORD = 0
LOCAL_FILE = 0
REMOTE_FILE =0
FOLDER = 0
REMOTE_FOLDER =0

class Arinc615(paramiko.SSHClient):
    def __init__(self, username, password, hostname, port=22):
        super().__init__()
        self.username = username
        self.password = password
        self.hostname = hostname
        self.port = port
        self.sftp = None
        self.is_connected = False 

    def connect_to_host(self):
        try:
            self.load_system_host_keys()
            self.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.connect(self.hostname, username=self.username, password=self.password, port=self.port, timeout=10) 
            self.sftp = self.open_sftp()
            print(f"Connected to {self.hostname}")
            self.is_connected = True
            return True 
        except Exception as e:
            print(f"Failed to connect: {e}")
            self.is_connected = False
            return False

    def close_connection(self):
        try:
            if self.is_connected:
                self.close()
                self.is_connected = False
                print("Connection closed")
            else:
                print("No connection to close.")
        except Exception as e:
            print(f"Error closing connection: {e}")

    def calculate_crc32(self, filename):
        try:
            with open(filename, 'rb') as f:
                data = f.read()
            return zlib.crc32(data)
        except Exception as e:
            print(f"Error calculating CRC32 for {filename}: {e}")

    def get_remote_file_crc32(self, remote_filepath):
        try:
            stdin, stdout, stderr = self.exec_command(f"crc32 {remote_filepath}", timeout=10) # allows terminal commands to be run on the ACC
            crc32_str = stdout.read().decode().strip()
            error = stderr.read().decode().strip()
            if error:
                print(f"Error from server: {error}")
            try:
                i = int(crc32_str, 16)
                return i
            except ValueError:
                print(f"Invalid CRC32 response: {crc32_str}")

        except Exception as e:
            print(f"Error getting remote CRC32 for {remote_filepath}: {e}")

    def transfer_folder(self, dir_path, local_dir, log_callback):
        try:
            self.sftp.stat(dir_path) 
        except FileNotFoundError:
            self.sftp.mkdir(dir_path) 

        try:
            files = os.listdir(local_dir) 
            total_files = len(files)
            for i, file in enumerate(files):
                file_path = Path(local_dir) / file
                log_callback(f"Processing: {file} ({i + 1}/{total_files})")

                if file_path.is_dir():  
                    remote_dir_path = f"{dir_path}/{file}" 
                    self.transfer_folder(remote_dir_path, file_path, log_callback)
                else:
                    local_file_crc32 = self.calculate_crc32(file_path)
                    if local_file_crc32 is None:
                        print(f"Skipping {file} due to CRC calculation error.")

                    print(f"Local crc32: {local_file_crc32}")
                    remote_path = f"{dir_path}/{file}" 
                    try:
                        self.sftp.put(file_path, remote_path)
                        print(f"Successfully transferred {file}")
                        log_callback(f"Successfully transferred {file}")
                    except Exception as e:
                        print(f"Error transferring {file}: {e}")
                        log_callback(f"Unable to transfer {file}: {e}")

                    remote_file_crc32 = self.get_remote_file_crc32(remote_path)
                    if remote_file_crc32 is None:
                        print("Unable to calculate CRC32 for remote file.")

                    print(f"Remote crc32: {remote_file_crc32}")

                    if local_file_crc32 == remote_file_crc32:
                        print(f'{file}: CRC32 matches')
                        log_callback(f'{file}: CRC32 matches')
                    else:
                        print(f'{file}: CRC32 mismatch')
                        log_callback(f'{file}: CRC32 mismatch')

        except Exception as e:
            print(f"Error: {e}")

    def get_folder(self, remote_path, local_dir, log_callback):
        try:
            os.makedirs(local_dir, exist_ok=True)
            files = self.sftp.listdir(remote_path)
            total_files = len(files)
            for i, filename in enumerate(files):
                remote_filepath = f"{remote_path}/{filename}"
                local_filepath = os.path.join(local_dir, filename)
                log_callback(f"Downloading: {filename} ({i + 1}/{total_files})")

                try:
                    if self.sftp.isdir(remote_filepath):
                        os.makedirs(local_filepath, exist_ok=True)
                        self.get_folder(remote_filepath, local_filepath, log_callback)
                    else:
                        self.sftp.get(remote_filepath, local_filepath)
                        print(f"Downloaded {filename} to {local_filepath}")

                except Exception as e:
                    print(f"Error downloading {filename}: {e}")
                
                local_file_crc32 = self.calculate_crc32(local_filepath)
                if local_file_crc32 is None:
                    print(f"Skipping {local_filepath} due to CRC calculation error.")

                print(f"Local crc32: {local_file_crc32}")

                remote_file_crc32 = self.get_remote_file_crc32(remote_filepath)
                if remote_file_crc32 is None:
                    print("Unable to calculate CRC32 for remote file.")

                print(f"Remote crc32: {remote_file_crc32}")

                if local_file_crc32 == remote_file_crc32:
                    print(f'{filename}: CRC32 matches')
                    log_callback(f'{filename}: CRC32 matches')
                else:
                    print(f'{filename}: CRC32 mismatch')
                    log_callback(f'{filename}: CRC32 mismatch')

            log_callback(f"Successfully downloaded {remote_path} to {local_dir}")

        except Exception as e:
            print(f"Error: {e}")

    def send_file(self, acc_path, local_path, log_callback):
        try:
            log_callback(f"Sending {local_path} to {acc_path}")
            self.sftp.put(local_path, acc_path)
            local_file_crc32 = self.calculate_crc32(local_path)
            if local_file_crc32 is None:
                print(f"Skipping CRC check for {local_path} due to error.")

            print(f"Local crc32: {local_file_crc32}")

            remote_file_crc32 = self.get_remote_file_crc32(acc_path)
            if remote_file_crc32 is None:
                print(f"Skipping CRC check for {acc_path} due to error.")

            print(f"Remote crc32: {remote_file_crc32}")

            if local_file_crc32 == remote_file_crc32:
                print(f'{local_path}: crc32 looks the same')
                log_callback(f'{Path(local_path).name}: crc32 matches')
                log_callback(f"Successfully transfered {local_path} to {acc_path}")
            else:
                print(f'{local_path}: crc32 there is a mismatch')
                log_callback(f'{Path(local_path).name}: crc32 mismatch')
                log_callback(f"Unable to transfer {local_path} to {acc_path}")

        except Exception as e:
            print(f"Error sending file: {e}")

    def get_file(self, acc_path, local_path, log_callback):
        try:
            log_callback(f"Downloading {acc_path} to {local_path}")
            self.sftp.get(acc_path, local_path)
            local_file_crc32 = self.calculate_crc32(local_path)
            if local_file_crc32 is None:
                print(f"Skipping CRC check for {local_path} due to error.")

            print(f"Local crc32: {local_file_crc32}")

            remote_file_crc32 = self.get_remote_file_crc32(acc_path)
            if remote_file_crc32 is None:
                print(f"Skipping CRC check for {acc_path} due to error.")

            print(f"Remote crc32: {remote_file_crc32}")

            if local_file_crc32 == remote_file_crc32:
                print(f'{local_path}: crc32 looks the same')
                log_callback(f'{Path(local_path).name}: crc32 matches')
                log_callback(f"Successfully transfered {acc_path} to {local_path}")
            else:
                print(f'{local_path}: crc32 there is a mismatch')
                log_callback(f'{Path(local_path).name}: crc32 mismatch')
                log_callback(f"Unable to transfer {acc_path} to {local_path}")

        except Exception as e:
            print(f"Error getting file: {e}")
    
    def delete_folder(self, dir_path, log_callback):
        try:
            cmd = "rm -r "  + dir_path
            stdin, stdout, stderr = self.exec_command(cmd, timeout=10)
            error = stderr.read().decode()
            if error:
                print(f"Error removing folder: {error}")
                log_callback(f"Unable to delete {dir_path}: {error}")
            else:
                print(f"{dir_path} has been deleted")
                log_callback(f"Successfully deleted {dir_path}")
        except Exception as e:
            print(f"Error deleting folder: {e}")

    def delete_file(self, file_path, log_callback):
        try:
            cmd = "rm " + file_path
            stdin,stdout,stderr = self.exec_command(cmd, timeout=10)
            error = stderr.read().decode()
            if error:
                print(f"Error removing file: {error}")
                log_callback(f"Unable to delete {file_path}: {error}")
            else:
                print(f"{file_path} has been deleted")
                log_callback(f"Successfully deleted {file_path}")
        except Exception as e:
            print(f"Error deleting file: {e}")
    
    def check_crc(self):
        try:
            cmd = "bash " + '/home/merlin/Desktop/crc32.sh'
            stdin,stdout,stderr = self.exec_command(cmd)
            error = stderr.read().decode()
            if error:
                print(f"Error calculating CRC")
                return error
            else:
                crc32_str = stdout.read().decode().strip()
                print(crc32_str)
                return crc32_str
        except Exception as e:
            print(f"Error calculating CRC of ACC: {e}")
  


class Arinc615App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ARINC615 File Transfer")

        self.arinc = None
        self.action_type = tk.StringVar(value="folder")

        # UI elements
        self.status_label = ttk.Label(self, text="Not Connected", foreground="red")
        self.status_label.grid(row=0, column=0, columnspan=2, pady=5)

        # Action Selection
        ttk.Label(self, text="Action Type:").grid(row=1, column=0, sticky=tk.E, padx=5, pady=2)
        self.action_combo = ttk.Combobox(self, textvariable=self.action_type, values=["folder", "file"], state="readonly")
        self.action_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        self.action_combo.bind("<<ComboboxSelected>>", self.browse_mode)

        ttk.Label(self, text="Remote Path:").grid(row=2, column=0, sticky=tk.E, padx=5, pady=2)
        self.remote_path_entry = ttk.Entry(self, width=40)
        self.remote_path_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(self, text="Local Path:").grid(row=3, column=0, sticky=tk.E, padx=5, pady=2)
        self.local_path_entry = ttk.Entry(self, width=40)
        self.local_path_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)

        self.local_path_button = ttk.Button(self, text="Browse", command=self.browse_local_path)
        self.local_path_button.grid(row=3, column=2, padx=5, pady=2)

        self.connect_button = ttk.Button(self, text="Connect", command=self.connect_ssh)
        self.connect_button.grid(row=4, column=0, columnspan=3, pady=10)

        self.transfer_button = ttk.Button(self, text="Transfer", command=self.transfer)
        self.transfer_button.grid(row=5, column=0, columnspan=3, pady=10)

        self.retrieve_button = ttk.Button(self, text="Retrieve", command=self.retrieve)
        self.retrieve_button.grid(row=6, column=0, columnspan=3, pady=10)

        self.delete_button = ttk.Button(self, text="Delete", command=self.delete)
        self.delete_button.grid(row=7, column=0, columnspan=3, pady=10)

        self.os_crc = ttk.Button(self, text="CRC of ACC", command=self.check_crc)
        self.os_crc.grid(row=4, column=2, columnspan=3, pady=10)

        self.log_text = tk.Text(self, height=10, width=60)
        self.log_text.grid(row=8, column=0, columnspan=3, padx=5, pady=5)
        self.log_text.config(state=tk.DISABLED)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.periodic_check_connection()

    def connect_ssh(self):
        """Connects to the SSH server (ACC)"""
        self.update_status("Connecting...", "blue")
        threading.Thread(target=self.connect_ssh_thread, daemon=True).start()

    def connect_ssh_thread(self):
        """The actual SSH connection logic"""
        try:
            self.arinc = Arinc615(username=SSH_USER, password=SSH_PASSWORD, hostname=TARGET_IP)
            if self.arinc.connect_to_host(): 
                self.update_status("Connected", "green")
                self.log("Successfully connected to the host.")
            else:
                self.update_status("Connection Failed", "red")
                self.log("Failed to connect to the host.")
        except Exception as e:
            self.update_status("Connection Error", "red")
            self.log(f"An error occurred during connection: {e}")

    def disconnect_ssh(self):
        """Disconnects the SSH connection"""
        if self.arinc:
            self.arinc.close_connection()
            self.arinc = None
            self.update_status("Disconnected", "red")
            self.log("Disconnected from the host.")

    def browse_local_path(self):
        """Opens a directory or file selection based on the type."""
        if self.action_type.get() == "folder":
            directory = filedialog.askdirectory()
            if directory:
                self.local_path_entry.delete(0, tk.END)
                self.local_path_entry.insert(0, directory)
        else:
            filepath = filedialog.askopenfilename()
            if filepath:
                self.local_path_entry.delete(0, tk.END)
                self.local_path_entry.insert(0, filepath)

    def browse_mode(self, event=None):
        """Updates the browse mode based on the selected type."""
        action = self.action_type.get()
        if action == "folder":
            self.local_path_button.config(text="Browse Folder")
        else:
            self.local_path_button.config(text="Browse File")

    def transfer(self):
        """Transfers either a folder or a file based on the type."""
        action = self.action_type.get()
        remote_path = self.remote_path_entry.get()
        local_path = self.local_path_entry.get()

        if not remote_path or not local_path:
            messagebox.showerror("Error", "Remote and local paths are required.")

        if not self.arinc or not self.arinc.is_connected:
            messagebox.showerror("Error", "Not connected to the SSH server.")

        if action == "folder":
            self.arinc.transfer_folder(remote_path, local_path, self.log)
        else:
            self.arinc.send_file(remote_path, local_path, self.log)

    def retrieve(self):
        """Retrieves either a folder or a file based on the type."""
        action = self.action_type.get()
        remote_path = self.remote_path_entry.get()
        local_path = self.local_path_entry.get()

        if not remote_path or not local_path:
            messagebox.showerror("Error", "Remote and local paths are required.")

        if not self.arinc or not self.arinc.is_connected:
            messagebox.showerror("Error", "Not connected to the SSH server.")

        if action == "folder":
            self.arinc.get_folder(remote_path, local_path, self.log)
        else:
            self.arinc.get_file(remote_path, local_path, self.log)
    
    def check_crc(self):
        if self.arinc:
            self.arinc.send_file("","", self.log)
            crc = self.arinc.check_crc()
            self.log(crc)
            self.arinc.delete_file("", self.log)
        else:
            messagebox.showerror("Error", "Not connected to the SSH server.")

    def delete(self):
        action = self.action_type.get()
        remote_path = self.remote_path_entry.get()

        if not remote_path:
            messagebox.showerror("Error", "Remote path is required.")

        if not self.arinc or not self.arinc.is_connected:
            messagebox.showerror("Error", "Not connected to the SSH server.")

        if action == "folder":
            self.arinc.delete_folder(remote_path, self.log)
        else:
            self.arinc.delete_file(remote_path, self.log)
            
    def update_status(self, message, color):
        """Updates the status label"""
        self.after(0, lambda: self.status_label.config(text=message, foreground=color))

    def log(self, message):
        """Logs a message to update the text area"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)

    def on_closing(self):
        """Handles the window closing event"""
        self.disconnect_ssh()
        self.destroy()

    def check_connection(self):
        """Checks the SSH connection status"""
        if self.arinc:
            try:
                self.arinc.exec_command("pwd", timeout=5)
                if not self.arinc.is_connected:
                  self.update_status("Not Connected", "red")
                  self.log("Connection seems to be down. Attempting to reconnect...")
                  self.disconnect_ssh()
                  self.connect_ssh()
                else:
                  self.update_status("Connected", "green")

            except Exception as e:
                self.update_status("Not Connected", "red")
                self.log(f"Connection lost: {e}. Attempting to reconnect...")
                self.disconnect_ssh()
                self.connect_ssh()  

        else:
            self.update_status("Not Connected", "red")

    def periodic_check_connection(self):
        """Periodically checks the connection status."""
        self.check_connection()
        self.after(2500, self.periodic_check_connection)

if __name__ == "__main__":
    app = Arinc615App()
    app.mainloop()
