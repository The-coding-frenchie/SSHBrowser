import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import paramiko
import threading
import os
from datetime import datetime

class SSHFileBrowser:
    def __init__(self, root):
        self.root = root
        self.root.title("SSH Bestandsverkenner")
        self.root.geometry("900x600")

        # SSH client en SFTP sessie
        self.ssh = None
        self.sftp = None
        self.current_path = "/"
        self.connected = False

        # Verbindingsframe
        conn_frame = ttk.LabelFrame(root, text="Verbinding", padding=10)
        conn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, sticky="w")
        self.host_entry = ttk.Entry(conn_frame, width=20)
        self.host_entry.grid(row=0, column=1, padx=5)
        self.host_entry.insert(0, "example.com")

        ttk.Label(conn_frame, text="Poort:").grid(row=0, column=2, sticky="w", padx=(10,0))
        self.port_entry = ttk.Entry(conn_frame, width=6)
        self.port_entry.grid(row=0, column=3, padx=5)
        self.port_entry.insert(0, "22")

        ttk.Label(conn_frame, text="Gebruiker:").grid(row=0, column=4, sticky="w", padx=(10,0))
        self.user_entry = ttk.Entry(conn_frame, width=15)
        self.user_entry.grid(row=0, column=5, padx=5)
        self.user_entry.insert(0, "root")

        ttk.Label(conn_frame, text="Wachtwoord:").grid(row=0, column=6, sticky="w", padx=(10,0))
        self.pass_entry = ttk.Entry(conn_frame, width=15, show="*")
        self.pass_entry.grid(row=0, column=7, padx=5)

        self.connect_btn = ttk.Button(conn_frame, text="Verbinden", command=self.connect_ssh)
        self.connect_btn.grid(row=0, column=8, padx=10)

        self.disconnect_btn = ttk.Button(conn_frame, text="Verbreken", command=self.disconnect_ssh, state="disabled")
        self.disconnect_btn.grid(row=0, column=9)

        # Pad en navigatie
        nav_frame = ttk.Frame(root)
        nav_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(nav_frame, text="Pad:").pack(side="left")
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(nav_frame, textvariable=self.path_var)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=5)

        self.go_btn = ttk.Button(nav_frame, text="Ga naar", command=self.navigate_to_path, state="disabled")
        self.go_btn.pack(side="left", padx=2)

        self.back_btn = ttk.Button(nav_frame, text="⬅ Terug", command=self.go_back, state="disabled")
        self.back_btn.pack(side="left", padx=2)

        self.home_btn = ttk.Button(nav_frame, text="🏠 Home", command=self.go_home, state="disabled")
        self.home_btn.pack(side="left", padx=2)

        # Boomweergave (tabel)
        tree_frame = ttk.Frame(root)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("naam", "grootte", "type", "gewijzigd")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings")
        self.tree.heading("#0", text="")
        self.tree.heading("naam", text="Naam")
        self.tree.heading("grootte", text="Grootte (bytes)")
        self.tree.heading("type", text="Type")
        self.tree.heading("gewijzigd", text="Laatst gewijzigd")

        self.tree.column("#0", width=30, stretch=False)
        self.tree.column("naam", width=300)
        self.tree.column("grootte", width=100)
        self.tree.column("type", width=80)
        self.tree.column("gewijzigd", width=150)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Dubbelklik op item
        self.tree.bind("<Double-1>", self.on_double_click)

        # Statusbalk
        self.status_var = tk.StringVar()
        self.status_var.set("Niet verbonden")
        status_bar = ttk.Label(root, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(fill="x", padx=10, pady=5)

        # Afsluiten netjes
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # -------------------- Verbindingsmethoden --------------------
    def connect_ssh(self):
        if self.connected:
            return
        host = self.host_entry.get().strip()
        port = int(self.port_entry.get().strip() or 22)
        user = self.user_entry.get().strip()
        password = self.pass_entry.get()

        if not host or not user:
            messagebox.showerror("Fout", "Host en gebruikersnaam zijn verplicht.")
            return

        self.status_var.set("Verbinden...")
        self.connect_btn.config(state="disabled")

        # Verbinden in aparte thread
        thread = threading.Thread(target=self._connect_thread, args=(host, port, user, password), daemon=True)
        thread.start()

    def _connect_thread(self, host, port, user, password):
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(hostname=host, port=port, username=user, password=password, timeout=10)
            self.sftp = self.ssh.open_sftp()
            self.connected = True

            # Schakel UI-elementen in
            self.root.after(0, self._on_connect_success)
        except Exception as e:
            self.root.after(0, self._on_connect_error, str(e))

    def _on_connect_success(self):
        self.status_var.set(f"Verbonden als {self.user_entry.get()}@{self.host_entry.get()}")
        self.connect_btn.config(state="disabled")
        self.disconnect_btn.config(state="normal")
        self.go_btn.config(state="normal")
        self.back_btn.config(state="normal")
        self.home_btn.config(state="normal")
        self.current_path = "/"
        self.path_var.set("/")
        self.refresh_directory()

    def _on_connect_error(self, error):
        self.status_var.set(f"Fout: {error}")
        self.connect_btn.config(state="normal")
        self.ssh = None
        self.sftp = None
        self.connected = False
        messagebox.showerror("Verbindingsfout", f"Kan geen verbinding maken:\n{error}")

    def disconnect_ssh(self):
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
        self.connected = False
        self.ssh = None
        self.sftp = None
        self.tree.delete(*self.tree.get_children())
        self.path_var.set("")
        self.status_var.set("Niet verbonden")
        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
        self.go_btn.config(state="disabled")
        self.back_btn.config(state="disabled")
        self.home_btn.config(state="disabled")

    # -------------------- Bestandsnavigatie --------------------
    def refresh_directory(self, path=None):
        if not self.connected or not self.sftp:
            return
        if path is None:
            path = self.current_path
        # Weergave leegmaken
        self.tree.delete(*self.tree.get_children())

        try:
            # Lijst van items ophalen
            items = self.sftp.listdir_attr(path)
            # Sorteren: mappen eerst, daarna bestanden
            dirs = []
            files = []
            for item in items:
                if item.filename in (".", ".."):
                    continue
                if item.st_mode & 0o40000:  # directory
                    dirs.append(item)
                else:
                    files.append(item)
            dirs.sort(key=lambda x: x.filename.lower())
            files.sort(key=lambda x: x.filename.lower())
            all_items = dirs + files

            for item in all_items:
                is_dir = item.st_mode & 0o40000
                # Icoon (folder of bestand)
                icon = "📁 " if is_dir else "📄 "
                # Grootte
                size = item.st_size if not is_dir else ""
                # Type
                file_type = "map" if is_dir else "bestand"
                # Tijd
                mtime = datetime.fromtimestamp(item.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                # Invoegen in boom
                self.tree.insert("", "end", text=icon, values=(item.filename, size, file_type, mtime),
                                 tags=("dir" if is_dir else "file"))

            self.path_var.set(path)
            self.current_path = path
            self.status_var.set(f"{len(all_items)} items in {path}")

        except Exception as e:
            messagebox.showerror("Fout", f"Kan map niet lezen:\n{e}")
            self.status_var.set(f"Fout: {e}")

    def navigate_to_path(self):
        if not self.connected:
            return
        new_path = self.path_var.get().strip()
        if not new_path:
            return
        # Controleer of pad bestaat en een map is
        try:
            attrs = self.sftp.stat(new_path)
            if attrs.st_mode & 0o40000:
                self.refresh_directory(new_path)
            else:
                messagebox.showerror("Fout", "Het opgegeven pad is geen map.")
        except Exception as e:
            messagebox.showerror("Fout", f"Pad bestaat niet of is niet toegankelijk:\n{e}")

    def go_back(self):
        if not self.connected:
            return
        parent = os.path.dirname(self.current_path.rstrip("/"))
        if not parent:
            parent = "/"
        self.refresh_directory(parent)

    def go_home(self):
        if not self.connected:
            return
        home = "/home/" + self.user_entry.get().strip()
        # Probeer home, anders root
        try:
            self.sftp.stat(home)
            self.refresh_directory(home)
        except:
            self.refresh_directory("/")

    def on_double_click(self, event):
        if not self.connected:
            return
        item = self.tree.selection()[0] if self.tree.selection() else None
        if not item:
            return
        values = self.tree.item(item, "values")
        if not values:
            return
        name = values[0]
        # Bepaal of het een map is
        # We kunnen de tags gebruiken of opnieuw stat doen
        tags = self.tree.item(item, "tags")
        if "dir" in tags:
            new_path = os.path.join(self.current_path, name).replace("\\", "/")
            self.refresh_directory(new_path)
        else:
            # Bestand - toon informatie of download
            if messagebox.askyesno("Bestand", f"Wil je '{name}' downloaden naar de huidige map?"):
                self.download_file(name)

    def download_file(self, filename):
        if not self.connected:
            return
        remote_path = os.path.join(self.current_path, filename).replace("\\", "/")
        local_path = filedialog.asksaveasfilename(initialfile=filename, title="Opslaan als")
        if not local_path:
            return
        try:
            self.sftp.get(remote_path, local_path)
            messagebox.showinfo("Succes", f"Bestand gedownload naar {local_path}")
        except Exception as e:
            messagebox.showerror("Fout", f"Download mislukt:\n{e}")

    # -------------------- Afsluiten --------------------
    def on_closing(self):
        self.disconnect_ssh()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SSHFileBrowser(root)
    root.mainloop()