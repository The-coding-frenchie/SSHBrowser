import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import paramiko
import threading
import os
import shutil
from datetime import datetime

class SSHFileBrowser:
    def __init__(self, root):
        self.root = root
        self.root.title("SSH Bestandsverkenner (FileZilla-achtig)")
        self.root.geometry("1200x800")

        # SSH client en SFTP sessie
        self.ssh = None
        self.sftp = None
        self.remote_path = "/"
        self.local_path = os.path.expanduser("~")
        self.connected = False

        # -------------------- Verbindingsframe --------------------
        conn_frame = ttk.LabelFrame(root, text="Verbinding", padding=10)
        conn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, sticky="w")
        self.host_entry = ttk.Entry(conn_frame, width=20)
        self.host_entry.grid(row=0, column=1, padx=5)
        self.host_entry.insert(0, "192.168.2.38")

        ttk.Label(conn_frame, text="Poort:").grid(row=0, column=2, sticky="w", padx=(10,0))
        self.port_entry = ttk.Entry(conn_frame, width=6)
        self.port_entry.grid(row=0, column=3, padx=5)
        self.port_entry.insert(0, "22")

        ttk.Label(conn_frame, text="Gebruiker:").grid(row=0, column=4, sticky="w", padx=(10,0))
        self.user_entry = ttk.Entry(conn_frame, width=15)
        self.user_entry.grid(row=0, column=5, padx=5)
        self.user_entry.insert(0, "dylan")

        ttk.Label(conn_frame, text="Wachtwoord:").grid(row=0, column=6, sticky="w", padx=(10,0))
        self.pass_entry = ttk.Entry(conn_frame, width=15, show="*")
        self.pass_entry.grid(row=0, column=7, padx=5)

        self.connect_btn = ttk.Button(conn_frame, text="Verbinden", command=self.connect_ssh)
        self.connect_btn.grid(row=0, column=8, padx=10)

        self.disconnect_btn = ttk.Button(conn_frame, text="Verbreken", command=self.disconnect_ssh, state="disabled")
        self.disconnect_btn.grid(row=0, column=9)

        # -------------------- Hoofdframe met twee panelen --------------------
        main_frame = ttk.Frame(root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Linker paneel (lokaal)
        left_frame = ttk.LabelFrame(main_frame, text="Lokaal", padding=5)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0,5))

        # Rechter paneel (remote)
        right_frame = ttk.LabelFrame(main_frame, text="Remote", padding=5)
        right_frame.grid(row=0, column=2, sticky="nsew", padx=(5,0))

        # Middelste paneel met actieknoppen
        center_frame = ttk.Frame(main_frame, padding=5)
        center_frame.grid(row=0, column=1, sticky="ns", padx=5)

        # Gewichten voor schalen
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(2, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        # -------------------- Lokaal paneel --------------------
        # Navigatiebalk lokaal
        local_nav = ttk.Frame(left_frame)
        local_nav.pack(fill="x", pady=2)

        ttk.Label(local_nav, text="Pad:").pack(side="left")
        self.local_path_var = tk.StringVar()
        self.local_path_entry = ttk.Entry(local_nav, textvariable=self.local_path_var)
        self.local_path_entry.pack(side="left", fill="x", expand=True, padx=5)

        self.local_go_btn = ttk.Button(local_nav, text="Ga naar", command=self.navigate_local_to_path)
        self.local_go_btn.pack(side="left", padx=2)

        self.local_back_btn = ttk.Button(local_nav, text="⬅ Terug", command=self.local_go_back)
        self.local_back_btn.pack(side="left", padx=2)

        self.local_home_btn = ttk.Button(local_nav, text="🏠 Home", command=self.local_go_home)
        self.local_home_btn.pack(side="left", padx=2)

        self.local_refresh_btn = ttk.Button(local_nav, text="↻ Vernieuw", command=self.refresh_local)
        self.local_refresh_btn.pack(side="left", padx=2)

        # Boomweergave lokaal
        local_tree_frame = ttk.Frame(left_frame)
        local_tree_frame.pack(fill="both", expand=True)

        columns = ("naam", "grootte", "type", "gewijzigd")
        self.local_tree = ttk.Treeview(local_tree_frame, columns=columns, show="tree headings")
        self.local_tree.heading("#0", text="")
        self.local_tree.heading("naam", text="Naam")
        self.local_tree.heading("grootte", text="Grootte (bytes)")
        self.local_tree.heading("type", text="Type")
        self.local_tree.heading("gewijzigd", text="Laatst gewijzigd")

        self.local_tree.column("#0", width=30, stretch=False)
        self.local_tree.column("naam", width=250)
        self.local_tree.column("grootte", width=100)
        self.local_tree.column("type", width=80)
        self.local_tree.column("gewijzigd", width=150)

        vsb_l = ttk.Scrollbar(local_tree_frame, orient="vertical", command=self.local_tree.yview)
        hsb_l = ttk.Scrollbar(local_tree_frame, orient="horizontal", command=self.local_tree.xview)
        self.local_tree.configure(yscrollcommand=vsb_l.set, xscrollcommand=hsb_l.set)

        self.local_tree.grid(row=0, column=0, sticky="nsew")
        vsb_l.grid(row=0, column=1, sticky="ns")
        hsb_l.grid(row=1, column=0, sticky="ew")
        local_tree_frame.grid_rowconfigure(0, weight=1)
        local_tree_frame.grid_columnconfigure(0, weight=1)

        self.local_tree.bind("<Double-1>", self.on_local_double_click)

        # -------------------- Remote paneel --------------------
        # Navigatiebalk remote
        remote_nav = ttk.Frame(right_frame)
        remote_nav.pack(fill="x", pady=2)

        ttk.Label(remote_nav, text="Pad:").pack(side="left")
        self.remote_path_var = tk.StringVar()
        self.remote_path_entry = ttk.Entry(remote_nav, textvariable=self.remote_path_var)
        self.remote_path_entry.pack(side="left", fill="x", expand=True, padx=5)

        self.remote_go_btn = ttk.Button(remote_nav, text="Ga naar", command=self.navigate_remote_to_path, state="disabled")
        self.remote_go_btn.pack(side="left", padx=2)

        self.remote_back_btn = ttk.Button(remote_nav, text="⬅ Terug", command=self.remote_go_back, state="disabled")
        self.remote_back_btn.pack(side="left", padx=2)

        self.remote_home_btn = ttk.Button(remote_nav, text="🏠 Home", command=self.remote_go_home, state="disabled")
        self.remote_home_btn.pack(side="left", padx=2)

        self.remote_refresh_btn = ttk.Button(remote_nav, text="↻ Vernieuw", command=self.refresh_remote, state="disabled")
        self.remote_refresh_btn.pack(side="left", padx=2)

        # Boomweergave remote
        remote_tree_frame = ttk.Frame(right_frame)
        remote_tree_frame.pack(fill="both", expand=True)

        self.remote_tree = ttk.Treeview(remote_tree_frame, columns=columns, show="tree headings")
        self.remote_tree.heading("#0", text="")
        self.remote_tree.heading("naam", text="Naam")
        self.remote_tree.heading("grootte", text="Grootte (bytes)")
        self.remote_tree.heading("type", text="Type")
        self.remote_tree.heading("gewijzigd", text="Laatst gewijzigd")

        self.remote_tree.column("#0", width=30, stretch=False)
        self.remote_tree.column("naam", width=250)
        self.remote_tree.column("grootte", width=100)
        self.remote_tree.column("type", width=80)
        self.remote_tree.column("gewijzigd", width=150)

        vsb_r = ttk.Scrollbar(remote_tree_frame, orient="vertical", command=self.remote_tree.yview)
        hsb_r = ttk.Scrollbar(remote_tree_frame, orient="horizontal", command=self.remote_tree.xview)
        self.remote_tree.configure(yscrollcommand=vsb_r.set, xscrollcommand=hsb_r.set)

        self.remote_tree.grid(row=0, column=0, sticky="nsew")
        vsb_r.grid(row=0, column=1, sticky="ns")
        hsb_r.grid(row=1, column=0, sticky="ew")
        remote_tree_frame.grid_rowconfigure(0, weight=1)
        remote_tree_frame.grid_columnconfigure(0, weight=1)

        self.remote_tree.bind("<Double-1>", self.on_remote_double_click)

        # -------------------- Actieknoppen (midden) --------------------
        ttk.Button(center_frame, text="⬆ Upload", command=self.upload_selected, width=12).pack(pady=5)
        ttk.Button(center_frame, text="⬇ Download", command=self.download_selected, width=12).pack(pady=5)
        ttk.Button(center_frame, text="❌ Verwijder (remote)", command=self.delete_remote_selected, width=12).pack(pady=5)
        ttk.Button(center_frame, text="📁 Nieuwe map (remote)", command=self.create_remote_dir, width=12).pack(pady=5)

        # -------------------- Overdrachtsqueue (FileZilla-stijl) --------------------
        transfer_frame = ttk.LabelFrame(root, text="Overdrachten", padding=5)
        transfer_frame.pack(fill="x", padx=10, pady=5)

        # Kolommen: Bestand, Richting, Grootte, Voortgang, Status
        transfer_columns = ("bestand", "richting", "grootte", "voortgang", "status")
        self.transfer_tree = ttk.Treeview(transfer_frame, columns=transfer_columns, show="headings", height=6)
        self.transfer_tree.heading("bestand", text="Bestand")
        self.transfer_tree.heading("richting", text="Richting")
        self.transfer_tree.heading("grootte", text="Grootte (bytes)")
        self.transfer_tree.heading("voortgang", text="Voortgang")
        self.transfer_tree.heading("status", text="Status")

        self.transfer_tree.column("bestand", width=250)
        self.transfer_tree.column("richting", width=80)
        self.transfer_tree.column("grootte", width=100)
        self.transfer_tree.column("voortgang", width=100)
        self.transfer_tree.column("status", width=120)

        # Scrollbar voor transfer tree
        vsb_t = ttk.Scrollbar(transfer_frame, orient="vertical", command=self.transfer_tree.yview)
        hsb_t = ttk.Scrollbar(transfer_frame, orient="horizontal", command=self.transfer_tree.xview)
        self.transfer_tree.configure(yscrollcommand=vsb_t.set, xscrollcommand=hsb_t.set)

        self.transfer_tree.grid(row=0, column=0, sticky="nsew")
        vsb_t.grid(row=0, column=1, sticky="ns")
        hsb_t.grid(row=1, column=0, sticky="ew")
        transfer_frame.grid_rowconfigure(0, weight=1)
        transfer_frame.grid_columnconfigure(0, weight=1)

        # -------------------- Statusbalk --------------------
        self.status_var = tk.StringVar()
        self.status_var.set("Niet verbonden")
        status_bar = ttk.Label(root, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(fill="x", padx=10, pady=5)

        # Initialiseer lokale weergave
        self.refresh_local()

        # Afsluiten netjes
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # -------------------- Interne variabelen voor transfers --------------------
        self.transfer_counter = 0  # voor unieke ID's

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

        thread = threading.Thread(target=self._connect_thread, args=(host, port, user, password), daemon=True)
        thread.start()

    def _connect_thread(self, host, port, user, password):
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(hostname=host, port=port, username=user, password=password, timeout=10)
            self.sftp = self.ssh.open_sftp()
            self.connected = True
            self.root.after(0, self._on_connect_success)
        except Exception as e:
            self.root.after(0, self._on_connect_error, str(e))

    def _on_connect_success(self):
        self.status_var.set(f"Verbonden als {self.user_entry.get()}@{self.host_entry.get()}")
        self.connect_btn.config(state="disabled")
        self.disconnect_btn.config(state="normal")
        self.remote_go_btn.config(state="normal")
        self.remote_back_btn.config(state="normal")
        self.remote_home_btn.config(state="normal")
        self.remote_refresh_btn.config(state="normal")
        self.remote_path = "/"
        self.remote_path_var.set("/")
        self.refresh_remote()

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
        self.remote_tree.delete(*self.remote_tree.get_children())
        self.remote_path_var.set("")
        self.status_var.set("Niet verbonden")
        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
        self.remote_go_btn.config(state="disabled")
        self.remote_back_btn.config(state="disabled")
        self.remote_home_btn.config(state="disabled")
        self.remote_refresh_btn.config(state="disabled")

    # -------------------- Lokale bestandsnavigatie --------------------
    def refresh_local(self, path=None):
        if path is None:
            path = self.local_path
        self.local_tree.delete(*self.local_tree.get_children())
        try:
            items = os.listdir(path)
            dirs = []
            files = []
            for name in items:
                full = os.path.join(path, name)
                if os.path.isdir(full):
                    dirs.append(name)
                else:
                    files.append(name)
            dirs.sort(key=str.lower)
            files.sort(key=str.lower)
            for name in dirs + files:
                full = os.path.join(path, name)
                is_dir = os.path.isdir(full)
                icon = "📁 " if is_dir else "📄 "
                size = os.path.getsize(full) if not is_dir else ""
                file_type = "map" if is_dir else "bestand"
                mtime = datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d %H:%M:%S")
                self.local_tree.insert("", "end", text=icon, values=(name, size, file_type, mtime),
                                       tags=("dir" if is_dir else "file"))
            self.local_path_var.set(path)
            self.local_path = path
            self.status_var.set(f"Lokaal: {len(dirs)+len(files)} items in {path}")
        except Exception as e:
            messagebox.showerror("Fout", f"Kan lokale map niet lezen:\n{e}")
            self.status_var.set(f"Fout: {e}")

    def navigate_local_to_path(self):
        new_path = self.local_path_var.get().strip()
        if not new_path:
            return
        if os.path.isdir(new_path):
            self.refresh_local(new_path)
        else:
            messagebox.showerror("Fout", "Het opgegeven pad is geen map.")

    def local_go_back(self):
        parent = os.path.dirname(self.local_path.rstrip("/"))
        if not parent:
            parent = "/"
        self.refresh_local(parent)

    def local_go_home(self):
        self.refresh_local(os.path.expanduser("~"))

    def on_local_double_click(self, event):
        item = self.local_tree.selection()[0] if self.local_tree.selection() else None
        if not item:
            return
        values = self.local_tree.item(item, "values")
        if not values:
            return
        name = values[0]
        tags = self.local_tree.item(item, "tags")
        if "dir" in tags:
            new_path = os.path.join(self.local_path, name)
            self.refresh_local(new_path)

    # -------------------- Remote bestandsnavigatie --------------------
    def refresh_remote(self, path=None):
        if not self.connected or not self.sftp:
            return
        if path is None:
            path = self.remote_path
        self.remote_tree.delete(*self.remote_tree.get_children())
        try:
            items = self.sftp.listdir_attr(path)
            dirs = []
            files = []
            for item in items:
                if item.filename in (".", ".."):
                    continue
                if item.st_mode & 0o40000:
                    dirs.append(item)
                else:
                    files.append(item)
            dirs.sort(key=lambda x: x.filename.lower())
            files.sort(key=lambda x: x.filename.lower())
            for item in dirs + files:
                is_dir = item.st_mode & 0o40000
                icon = "📁 " if is_dir else "📄 "
                size = item.st_size if not is_dir else ""
                file_type = "map" if is_dir else "bestand"
                mtime = datetime.fromtimestamp(item.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                self.remote_tree.insert("", "end", text=icon, values=(item.filename, size, file_type, mtime),
                                        tags=("dir" if is_dir else "file"))
            self.remote_path_var.set(path)
            self.remote_path = path
            self.status_var.set(f"Remote: {len(dirs)+len(files)} items in {path}")
        except Exception as e:
            messagebox.showerror("Fout", f"Kan remote map niet lezen:\n{e}")
            self.status_var.set(f"Fout: {e}")

    def navigate_remote_to_path(self):
        if not self.connected:
            return
        new_path = self.remote_path_var.get().strip()
        if not new_path:
            return
        try:
            attrs = self.sftp.stat(new_path)
            if attrs.st_mode & 0o40000:
                self.refresh_remote(new_path)
            else:
                messagebox.showerror("Fout", "Het opgegeven pad is geen map.")
        except Exception as e:
            messagebox.showerror("Fout", f"Pad bestaat niet of is niet toegankelijk:\n{e}")

    def remote_go_back(self):
        if not self.connected:
            return
        parent = os.path.dirname(self.remote_path.rstrip("/"))
        if not parent:
            parent = "/"
        self.refresh_remote(parent)

    def remote_go_home(self):
        if not self.connected:
            return
        home = "/home/" + self.user_entry.get().strip()
        try:
            self.sftp.stat(home)
            self.refresh_remote(home)
        except:
            self.refresh_remote("/")

    def on_remote_double_click(self, event):
        if not self.connected:
            return
        item = self.remote_tree.selection()[0] if self.remote_tree.selection() else None
        if not item:
            return
        values = self.remote_tree.item(item, "values")
        if not values:
            return
        name = values[0]
        tags = self.remote_tree.item(item, "tags")
        if "dir" in tags:
            new_path = os.path.join(self.remote_path, name).replace("\\", "/")
            self.refresh_remote(new_path)
        else:
            if messagebox.askyesno("Download", f"Wil je '{name}' downloaden naar de huidige lokale map?"):
                self.download_file(name)

    # -------------------- Overdrachtsqueue functies --------------------
    def add_transfer(self, filename, direction, total_size):
        """Voeg een overdracht toe aan de queue en geef een uniek ID terug."""
        self.transfer_counter += 1
        transfer_id = f"T{self.transfer_counter}"
        # Voeg rij toe
        item = self.transfer_tree.insert("", "end", iid=transfer_id,
                                         values=(filename, direction, total_size, "0%", "Bezig"))
        # Zorg dat de queue zichtbaar is (scroll naar beneden)
        self.transfer_tree.see(item)
        return transfer_id

    def update_transfer_progress(self, transfer_id, transferred, total):
        """Update de voortgang van een transfer (wordt aangeroepen vanuit callback)."""
        if total <= 0:
            percent = 0
        else:
            percent = int((transferred / total) * 100)
        self.transfer_tree.item(transfer_id, values=(
            self.transfer_tree.item(transfer_id, "values")[0],  # bestand
            self.transfer_tree.item(transfer_id, "values")[1],  # richting
            total,
            f"{percent}%",
            "Bezig"
        ))
        # Eventueel statusbalk bijwerken
        self.status_var.set(f"Overdracht {transfer_id}: {percent}% voltooid")

    def set_transfer_done(self, transfer_id, success=True):
        """Markeer een transfer als voltooid of mislukt."""
        status = "Voltooid" if success else "Mislukt"
        values = list(self.transfer_tree.item(transfer_id, "values"))
        values[4] = status
        self.transfer_tree.item(transfer_id, values=values)
        if success:
            self.status_var.set(f"Transfer {transfer_id} voltooid.")
        else:
            self.status_var.set(f"Transfer {transfer_id} mislukt.")

    # -------------------- Upload / Download --------------------
    def upload_selected(self):
        if not self.connected:
            messagebox.showerror("Fout", "Niet verbonden met een server.")
            return
        item = self.local_tree.selection()
        if not item:
            messagebox.showinfo("Info", "Selecteer eerst een lokaal bestand.")
            return
        values = self.local_tree.item(item[0], "values")
        if not values:
            return
        name = values[0]
        local_full = os.path.join(self.local_path, name)
        if os.path.isdir(local_full):
            messagebox.showinfo("Info", "Uploaden van mappen wordt nog niet ondersteund.")
            return
        remote_full = os.path.join(self.remote_path, name).replace("\\", "/")
        # Check of remote bestaat
        try:
            self.sftp.stat(remote_full)
            overwrite = messagebox.askyesno("Overschrijven", f"Bestand '{name}' bestaat al op de server. Overschrijven?")
            if not overwrite:
                return
        except:
            pass

        # Voeg transfer toe aan queue
        total_size = os.path.getsize(local_full)
        transfer_id = self.add_transfer(name, "Upload ⬆", total_size)

        # Start upload thread met callback
        threading.Thread(target=self._upload_thread,
                         args=(local_full, remote_full, transfer_id, total_size),
                         daemon=True).start()

    def _upload_thread(self, local_path, remote_path, transfer_id, total_size):
        try:
            # Callback voor voortgang
            def progress_callback(transferred, total):
                # total is hetzelfde als total_size, maar we gebruiken de meegegeven waarde
                self.root.after(0, self.update_transfer_progress, transfer_id, transferred, total_size)

            self.sftp.put(local_path, remote_path, callback=progress_callback)
            self.root.after(0, self.set_transfer_done, transfer_id, True)
            self.root.after(0, self.refresh_remote)  # Vernieuw remote weergave
        except Exception as e:
            self.root.after(0, self.set_transfer_done, transfer_id, False)
            self.root.after(0, messagebox.showerror, "Fout", f"Upload mislukt:\n{e}")

    def download_selected(self):
        if not self.connected:
            messagebox.showerror("Fout", "Niet verbonden met een server.")
            return
        item = self.remote_tree.selection()
        if not item:
            messagebox.showinfo("Info", "Selecteer eerst een remote bestand.")
            return
        values = self.remote_tree.item(item[0], "values")
        if not values:
            return
        name = values[0]
        tags = self.remote_tree.item(item[0], "tags")
        if "dir" in tags:
            messagebox.showinfo("Info", "Downloaden van mappen wordt nog niet ondersteund.")
            return
        remote_full = os.path.join(self.remote_path, name).replace("\\", "/")
        local_full = os.path.join(self.local_path, name)
        if os.path.exists(local_full):
            overwrite = messagebox.askyesno("Overschrijven", f"Bestand '{name}' bestaat al lokaal. Overschrijven?")
            if not overwrite:
                return

        # Haal grootte op van remote bestand
        total_size = self.sftp.stat(remote_full).st_size
        transfer_id = self.add_transfer(name, "Download ⬇", total_size)

        threading.Thread(target=self._download_thread,
                         args=(remote_full, local_full, transfer_id, total_size),
                         daemon=True).start()

    def _download_thread(self, remote_path, local_path, transfer_id, total_size):
        try:
            def progress_callback(transferred, total):
                self.root.after(0, self.update_transfer_progress, transfer_id, transferred, total_size)

            self.sftp.get(remote_path, local_path, callback=progress_callback)
            self.root.after(0, self.set_transfer_done, transfer_id, True)
            self.root.after(0, self.refresh_local)  # Vernieuw lokale weergave
        except Exception as e:
            self.root.after(0, self.set_transfer_done, transfer_id, False)
            self.root.after(0, messagebox.showerror, "Fout", f"Download mislukt:\n{e}")

    # -------------------- Overige remote acties --------------------
    def delete_remote_selected(self):
        if not self.connected:
            messagebox.showerror("Fout", "Niet verbonden met een server.")
            return
        item = self.remote_tree.selection()
        if not item:
            messagebox.showinfo("Info", "Selecteer eerst een remote item.")
            return
        values = self.remote_tree.item(item[0], "values")
        if not values:
            return
        name = values[0]
        tags = self.remote_tree.item(item[0], "tags")
        remote_full = os.path.join(self.remote_path, name).replace("\\", "/")
        if not messagebox.askyesno("Verwijderen", f"Weet je zeker dat je '{name}' wilt verwijderen?"):
            return
        try:
            if "dir" in tags:
                self._delete_remote_dir(remote_full)
            else:
                self.sftp.remove(remote_full)
            self.refresh_remote()
            self.status_var.set(f"'{name}' verwijderd.")
        except Exception as e:
            messagebox.showerror("Fout", f"Verwijderen mislukt:\n{e}")

    def _delete_remote_dir(self, path):
        for item in self.sftp.listdir_attr(path):
            if item.filename in (".", ".."):
                continue
            full = os.path.join(path, item.filename).replace("\\", "/")
            if item.st_mode & 0o40000:
                self._delete_remote_dir(full)
            else:
                self.sftp.remove(full)
        self.sftp.rmdir(path)

    def create_remote_dir(self):
        if not self.connected:
            messagebox.showerror("Fout", "Niet verbonden met een server.")
            return
        name = simpledialog.askstring("Nieuwe map", "Voer de naam van de nieuwe map in:")
        if not name:
            return
        new_path = os.path.join(self.remote_path, name).replace("\\", "/")
        try:
            self.sftp.mkdir(new_path)
            self.refresh_remote()
            self.status_var.set(f"Map '{name}' aangemaakt.")
        except Exception as e:
            messagebox.showerror("Fout", f"Kan map niet aanmaken:\n{e}")

    # -------------------- Afsluiten --------------------
    def on_closing(self):
        self.disconnect_ssh()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SSHFileBrowser(root)
    root.mainloop()