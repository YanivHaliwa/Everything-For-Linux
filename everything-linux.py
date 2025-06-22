#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import os
import threading
import time
from pathlib import Path
import re

#version 22.6.25

DEBUG = False

class EverythingLinux:
    def __init__(self, root):
        self.root = root
        self.root.title("Everything Linux")
        self.root.geometry("1000x700")
        self.root.configure(bg='#2b2b2b')
        
        self.center_window()
        
        self.search_delay = 0.03
        self.last_search_time = 0
        self.current_search_thread = None
        self.search_stop_event = threading.Event()
        self.search_timer = None
        
        self.search_location = tk.StringVar(value="/")
        self.exact_search = tk.BooleanVar(value=True)
        self.file_type = tk.StringVar(value="all")
        
        # Sorting state
        self.sort_column = None
        self.sort_reverse = False
        
        self.ignore_patterns = [
            r'\.git/',
            r'trash',
            r'tmp.*',
            r'/tmp',
            r'cache',
            r'/cache/',
            r'\.cache/'
        ]
        
        self.setup_ui()
        self.check_plocate()
        
    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        window_width = 1000
        window_height = 700
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        if DEBUG:
            print(f"Screen: {screen_width}x{screen_height}, Window centered at: {x},{y}")
        
    def setup_ui(self):
        main_frame = tk.Frame(self.root, bg='#2b2b2b')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        search_frame = tk.Frame(main_frame, bg='#2b2b2b')
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(search_frame, text="Search:", bg='#2b2b2b', fg='white', font=('Arial', 12)).pack(side=tk.LEFT)
        
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            search_frame, 
            textvariable=self.search_var,
            font=('Arial', 12),
            bg='#404040',
            fg='white',
            insertbackground='white'
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        self.search_entry.focus()
        
        self.search_var.trace('w', self.on_search_change)
        self.search_entry.bind('<Return>', self.on_enter_pressed)
        self.search_entry.bind('<Escape>', self.clear_search)
        
        options_frame = tk.Frame(main_frame, bg='#2b2b2b')
        options_frame.pack(fill=tk.X, pady=(5, 10))
        
        location_frame = tk.Frame(options_frame, bg='#2b2b2b')
        location_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        tk.Label(location_frame, text="Location:", bg='#2b2b2b', fg='white', font=('Arial', 10)).pack(side=tk.LEFT)
        
        self.location_entry = tk.Entry(
            location_frame,
            textvariable=self.search_location,
            width=30,
            font=('Arial', 10),
            bg='#404040',
            fg='white',
            insertbackground='white'
        )
        self.location_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        location_browse_btn = tk.Button(
            location_frame,
            text="Browse",
            command=self.browse_location,
            bg='#505050',
            fg='white',
            font=('Arial', 9),
            relief=tk.FLAT,
            cursor='hand2'
        )
        location_browse_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        exact_frame = tk.Frame(options_frame, bg='#2b2b2b')
        exact_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        self.exact_check = tk.Checkbutton(
            exact_frame,
            text="Exact",
            variable=self.exact_search,
            bg='#2b2b2b',
            fg='white',
            selectcolor='#404040',
            font=('Arial', 10),
            activebackground='#2b2b2b',
            activeforeground='white'
        )
        self.exact_check.pack(side=tk.LEFT)
        
        type_frame = tk.Frame(options_frame, bg='#2b2b2b')
        type_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        tk.Label(type_frame, text="Type:", bg='#2b2b2b', fg='white', font=('Arial', 10)).pack(side=tk.LEFT)
        
        self.type_combo = ttk.Combobox(
            type_frame,
            textvariable=self.file_type,
            values=["all", "file", "folder"],
            state="readonly",
            width=10,
            font=('Arial', 10)
        )
        self.type_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        update_frame = tk.Frame(options_frame, bg='#2b2b2b')
        update_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        self.update_btn = tk.Button(
            update_frame,
            text="Update DB",
            command=self.update_database_gui,
            bg='#606060',
            fg='white',
            font=('Arial', 10),
            relief=tk.FLAT,
            cursor='hand2',
            padx=10
        )
        self.update_btn.pack(side=tk.LEFT)
        
        ignore_frame = tk.Frame(options_frame, bg='#2b2b2b')
        ignore_frame.pack(side=tk.LEFT)
        
        self.ignore_btn = tk.Button(
            ignore_frame,
            text="Ignore Items",
            command=self.open_ignore_window,
            bg='#606060',
            fg='white',
            font=('Arial', 10),
            relief=tk.FLAT,
            cursor='hand2',
            padx=10
        )
        self.ignore_btn.pack(side=tk.LEFT)
        
        self.search_location.trace('w', self.on_options_change)
        self.exact_search.trace('w', self.on_options_change)
        self.file_type.trace('w', self.on_options_change)
        
        results_frame = tk.Frame(main_frame, bg='#2b2b2b')
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('name', 'path', 'size')
        self.tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=20)
        
        self.tree.heading('name', text='Name', command=lambda: self.sort_by_column('name'))
        self.tree.heading('path', text='Path', command=lambda: self.sort_by_column('path'))
        self.tree.heading('size', text='Size', command=lambda: self.sort_by_column('size'))
        
        self.tree.column('name', width=300, minwidth=200)
        self.tree.column('path', width=500, minwidth=300)
        self.tree.column('size', width=120, minwidth=100)
        
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<Double-1>', self.on_item_double_click)
        self.tree.bind('<Button-3>', self.on_right_click)  # Right-click context menu
        
        status_frame = tk.Frame(main_frame, bg='#2b2b2b')
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_label = tk.Label(
            status_frame, 
            text="Ready. Start typing to search...", 
            bg='#2b2b2b', 
            fg='#888888',
            font=('Arial', 10)
        )
        self.status_label.pack(side=tk.LEFT)
        
        self.results_count_label = tk.Label(
            status_frame,
            text="",
            bg='#2b2b2b',
            fg='#888888',
            font=('Arial', 10)
        )
        self.results_count_label.pack(side=tk.RIGHT)
        
        self.copyright_label = tk.Label(
            status_frame,
            text="© By Yaniv Haliwa",
            bg='#2b2b2b',
            fg='#666666',
            font=('Arial', 9)
        )
        self.copyright_label.pack(side=tk.RIGHT, padx=(10, 0))
        
    def check_plocate(self):
        try:
            result = subprocess.run(['which', 'plocate'], capture_output=True, text=True)
            if result.returncode != 0:
                messagebox.showerror("Error", "plocate not found! Please install it:\nsudo apt install plocate")
                self.root.quit()
                return
            
            result = subprocess.run(['plocate', '--version'], capture_output=True, text=True)
            if DEBUG:
                print(f"plocate version: {result.stdout.strip()}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check plocate: {e}")
            self.root.quit()
            
    def on_search_change(self, *args):
        self.search_stop_event.set()
        
        if hasattr(self, 'search_timer') and self.search_timer:
            self.root.after_cancel(self.search_timer)
        
        self.last_search_time = time.time()
        
        query = self.search_var.get().strip()
        
        if not query:
            self.clear_results()
            self.status_label.config(text="Ready. Start typing to search...")
            return
        
        if len(query) < 2:
            self.status_label.config(text="Type at least 2 characters...")
            self.clear_results()
            return
        
        if '*' in query or '?' in query or '[' in query or '(' in query:
            if self.exact_search.get():
                self.exact_search.set(False)
                if DEBUG:
                    print(f"[DEBUG] Auto-disabled exact mode - regex pattern detected: {query}")
        
        self.search_timer = self.root.after(300, self.debounced_search)
        
    def debounced_search(self):
        """Execute search after debounce delay"""
        query = self.search_var.get().strip()
        
        if len(query) < 2:
            return
        
        self.search_stop_event.clear()
        
        self.current_search_thread = threading.Thread(target=self.immediate_search)
        self.current_search_thread.daemon = True
        self.current_search_thread.start()
        
    def immediate_search(self):
        query = self.search_var.get().strip()
        
        if len(query) < 2:
            self.root.after(0, self.clear_results)
            self.root.after(0, lambda: self.status_label.config(text="Type at least 2 characters..."))
            return
            
        self.root.after(0, lambda: self.status_label.config(text="Searching..."))
        
        if DEBUG:
            print(f"[DEBUG] Starting search for: '{query}'")
        
        self.perform_search(query)
        
    def open_ignore_window(self):
        """Open window to manage ignore patterns"""
        ignore_window = tk.Toplevel(self.root)
        ignore_window.title("Ignore Items Configuration")
        ignore_window.geometry("600x400")
        ignore_window.configure(bg='#2b2b2b')
        ignore_window.transient(self.root)
        ignore_window.grab_set()
        
        ignore_window.update_idletasks()
        x = (ignore_window.winfo_screenwidth() - 600) // 2
        y = (ignore_window.winfo_screenheight() - 400) // 2
        ignore_window.geometry(f"600x400+{x}+{y}")
        
        main_frame = tk.Frame(ignore_window, bg='#2b2b2b')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title_label = tk.Label(
            main_frame,
            text="Ignore Patterns (Regex)",
            bg='#2b2b2b',
            fg='white',
            font=('Arial', 14, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        info_label = tk.Label(
            main_frame,
            text="Add regex patterns for files/folders to ignore during search:",
            bg='#2b2b2b',
            fg='#cccccc',
            font=('Arial', 10)
        )
        info_label.pack(pady=(0, 10))
        
        list_frame = tk.Frame(main_frame, bg='#2b2b2b')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.ignore_listbox = tk.Listbox(
            list_frame,
            bg='#404040',
            fg='white',
            font=('Arial', 10),
            selectbackground='#606060',
            yscrollcommand=scrollbar.set
        )
        self.ignore_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.ignore_listbox.yview)
        
        for pattern in self.ignore_patterns:
            self.ignore_listbox.insert(tk.END, pattern)
        
        entry_frame = tk.Frame(main_frame, bg='#2b2b2b')
        entry_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            entry_frame,
            text="New pattern:",
            bg='#2b2b2b',
            fg='white',
            font=('Arial', 10)
        ).pack(anchor=tk.W, pady=(0, 5))
        
        self.pattern_entry = tk.Entry(
            entry_frame,
            bg='#404040',
            fg='white',
            font=('Arial', 10),
            insertbackground='white'
        )
        self.pattern_entry.pack(fill=tk.X, expand=True)
        self.pattern_entry.bind('<Return>', lambda e: self.add_ignore_pattern())
        
        buttons_frame = tk.Frame(main_frame, bg='#2b2b2b')
        buttons_frame.pack(fill=tk.X)
        
        add_btn = tk.Button(
            buttons_frame,
            text="Add",
            command=self.add_ignore_pattern,
            bg='#505050',
            fg='white',
            font=('Arial', 10),
            relief=tk.FLAT,
            cursor='hand2',
            width=8
        )
        add_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        remove_btn = tk.Button(
            buttons_frame,
            text="Remove",
            command=self.remove_ignore_pattern,
            bg='#505050',
            fg='white',
            font=('Arial', 10),
            relief=tk.FLAT,
            cursor='hand2',
            width=8
        )
        remove_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        edit_btn = tk.Button(
            buttons_frame,
            text="Edit",
            command=self.edit_ignore_pattern,
            bg='#505050',
            fg='white',
            font=('Arial', 10),
            relief=tk.FLAT,
            cursor='hand2',
            width=8
        )
        edit_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        reset_btn = tk.Button(
            buttons_frame,
            text="Reset Defaults",
            command=self.reset_ignore_patterns,
            bg='#505050',
            fg='white',
            font=('Arial', 10),
            relief=tk.FLAT,
            cursor='hand2',
            width=12
        )
        reset_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        close_btn = tk.Button(
            buttons_frame,
            text="Close",
            command=lambda: self.close_ignore_window(ignore_window),
            bg='#606060',
            fg='white',
            font=('Arial', 10),
            relief=tk.FLAT,
            cursor='hand2',
            width=8
        )
        close_btn.pack(side=tk.RIGHT)
        
        self.current_ignore_window = ignore_window
        self.edit_entry = None
        self.edit_index = None
        
        self.ignore_listbox.bind('<Double-1>', lambda e: self.edit_ignore_pattern())
        
        self.pattern_entry.focus()
        
    def add_ignore_pattern(self):
        """Add new ignore pattern"""
        pattern = self.pattern_entry.get().strip()
        if pattern and pattern not in self.ignore_patterns:
            self.ignore_patterns.append(pattern)
            self.ignore_listbox.insert(tk.END, pattern)
            self.pattern_entry.delete(0, tk.END)
            if DEBUG:
                print(f"[DEBUG] Added ignore pattern: {pattern}")
        
    def remove_ignore_pattern(self):
        """Remove selected ignore pattern"""
        selection = self.ignore_listbox.curselection()
        if selection:
            index = selection[0]
            pattern = self.ignore_listbox.get(index)
            self.ignore_patterns.remove(pattern)
            self.ignore_listbox.delete(index)
            if DEBUG:
                print(f"[DEBUG] Removed ignore pattern: {pattern}")
                
    def reset_ignore_patterns(self):
        """Reset to default ignore patterns"""
        self.ignore_patterns = [
            r'\.git/',
            r'trash',
            r'tmp.*',
            r'/tmp',
            r'cache',
            r'/cache/',
            r'\.cache/'
        ]
        self.ignore_listbox.delete(0, tk.END)
        for pattern in self.ignore_patterns:
            self.ignore_listbox.insert(tk.END, pattern)
        if DEBUG:
            print("[DEBUG] Reset ignore patterns to defaults")
            
    def close_ignore_window(self, window):
        """Close ignore window and trigger new search"""
        window.destroy()
        current_query = self.search_var.get().strip()
        if len(current_query) >= 2:
            self.on_search_change()
            if DEBUG:
                print("[DEBUG] Triggered new search after closing ignore window")

    def should_ignore_path(self, path):
        """Check if path should be ignored based on patterns"""
        for pattern in self.ignore_patterns:
            try:
                if re.search(pattern, path, re.IGNORECASE):
                    if DEBUG:
                        print(f"[DEBUG] Ignoring {path} - matches pattern: {pattern}")
                    return True
            except re.error as e:
                if DEBUG:
                    print(f"[DEBUG] Invalid regex pattern '{pattern}': {e}")
                continue
        return False

    def on_options_change(self, *args):
        self.on_search_change()
        
    def browse_location(self):
        directory = filedialog.askdirectory(initialdir=self.search_location.get())
        if directory:
            self.search_location.set(directory)
            self.on_search_change()
        
    def delayed_search(self):
        time.sleep(self.search_delay)
        
        if time.time() - self.last_search_time < self.search_delay:
            return
            
        query = self.search_var.get().strip()
        if len(query) < 2:
            self.root.after(0, self.clear_results)
            return
            
        self.root.after(0, lambda: self.status_label.config(text="Searching..."))
        self.perform_search(query)
        
    def perform_search(self, query):
        try:
            if self.search_stop_event.is_set():
                if DEBUG:
                    print(f"[DEBUG] Search cancelled before starting for: '{query}'")
                return
                
            if DEBUG:
                print(f"[DEBUG] Searching for: '{query}'")
                print(f"[DEBUG] Location: {self.search_location.get()}")
                print(f"[DEBUG] Exact: {self.exact_search.get()}")
                print(f"[DEBUG] Type: {self.file_type.get()}")
                
            start_time = time.time()
                
            cmd = ['plocate', '--ignore-case']
            
            if self.file_type.get() == "file" and ('*' in query or '?' in query):
                base_terms = re.findall(r'[a-zA-Z0-9_]+', query)
                if base_terms:
                    search_term = max(base_terms, key=len)
                    cmd.append(f'*{search_term}*')
                    if DEBUG:
                        print(f"[DEBUG] File wildcard search - using broad term: {search_term}")
                        print(f"[DEBUG] Will apply exact pattern '{query}' to filenames in filter")
                else:
                    cmd.append(f'*{query}*')
            elif '*' in query or '?' in query:
                pattern = query
                if not pattern.startswith('*'):
                    pattern = f'*{pattern}'
                if not pattern.endswith('*'):
                    pattern = f'{pattern}*'
                cmd.append(pattern)
                if DEBUG:
                    print(f"[DEBUG] Using wildcard pattern: {pattern}")
            else:
                cmd.append(f'*{query}*')
            
            if DEBUG:
                print(f"[DEBUG] Running command: {' '.join(cmd)}")
            
            if self.search_stop_event.is_set():
                if DEBUG:
                    print(f"[DEBUG] Search cancelled before plocate for: '{query}'")
                return
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            
            end_time = time.time()
            search_time = end_time - start_time
            
            if DEBUG:
                print(f"[DEBUG] plocate completed in {search_time:.2f}s")
            
            # Check if search was cancelled after plocate finished
            if self.search_stop_event.is_set():
                if DEBUG:
                    print(f"[DEBUG] Search cancelled after plocate for: '{query}'")
                return
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if lines and lines[0]:
                    filtered_lines = self.filter_results(lines)
                    
                    if self.search_stop_event.is_set():
                        return
                        
                    if filtered_lines:
                        self.root.after(0, lambda: self.display_results(filtered_lines, query, search_time))
                    else:
                        self.root.after(0, lambda: self.display_no_results(query))
                else:
                    if not self.search_stop_event.is_set():
                        self.root.after(0, lambda: self.display_no_results(query))
            else:
                if DEBUG:
                    print(f"plocate error: {result.stderr}")
                if not self.search_stop_event.is_set():
                    self.root.after(0, lambda: self.display_no_results(query))
                
        except subprocess.TimeoutExpired:
            if DEBUG:
                print(f"[DEBUG] Search timed out after 3 seconds for: '{query}'")
            if not self.search_stop_event.is_set():
                self.root.after(0, lambda: self.status_label.config(text="Search timed out - try more specific query"))
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Search error: {e}")
            if not self.search_stop_event.is_set():
                self.root.after(0, lambda: self.status_label.config(text=f"Error: {e}"))
            
    def filter_results(self, paths):
        filtered = []
        location = self.search_location.get().rstrip('/')
        file_type = self.file_type.get()
        query = self.search_var.get().strip()
        
        if DEBUG:
            print(f"Filtering with location: '{location}', type: '{file_type}', exact: {self.exact_search.get()}")
            print(f"Total paths to filter: {len(paths)}")
        
        for path in paths:
            if not path.strip():
                continue
                
            if self.search_stop_event.is_set():
                return []
                
            if self.should_ignore_path(path):
                continue
                
            if location != "/":
                if not (path.startswith(location + "/") or path == location):
                    if DEBUG:
                        print(f"Skipping {path} - not in location {location}")
                    continue
            
            # Filter by type EARLY - before other checks
            try:
                if file_type != "all" and os.path.exists(path):
                    is_file = os.path.isfile(path)
                    is_dir = os.path.isdir(path)
                    
                    if file_type == "file" and not is_file:
                        if DEBUG:
                            print(f"Skipping {path} - not a file (type filter)")
                        continue
                    elif file_type == "folder" and not is_dir:
                        if DEBUG:
                            print(f"Skipping {path} - not a folder (type filter)")
                        continue
            except (OSError, PermissionError) as e:
                if DEBUG:
                    print(f"Permission/OS error checking type for {path}: {e}")
                continue
            
            # For file type filtering, ensure query matches filename only (not folder path)
            if file_type == "file":
                filename = os.path.basename(path)
                
                # Check if query appears in filename
                if self.exact_search.get() and '*' not in query and '?' not in query:
                    # For exact search, check if query is exact match (whole word) in filename
                    pattern = r'\b' + re.escape(query) + r'\b'
                    if not re.search(pattern, filename, re.IGNORECASE):
                        if DEBUG:
                            print(f"Skipping {path} - '{query}' not found as exact word in filename '{filename}'")
                        continue
                elif '*' in query or '?' in query:
                    # For wildcard searches, apply pattern matching to filename only
                    pattern = query.replace('*', '.*').replace('?', '.')
                    pattern = f'^{pattern}$'  # Match entire filename
                    try:
                        if not re.search(pattern, filename, re.IGNORECASE):
                            if DEBUG:
                                print(f"Skipping {path} - filename '{filename}' doesn't match pattern '{pattern}'")
                            continue
                    except re.error as e:
                        if DEBUG:
                            print(f"Invalid regex pattern '{pattern}': {e}")
                        continue
                else:
                    # For regular (non-exact, non-wildcard) search, check if query is in filename
                    if query.lower() not in filename.lower():
                        if DEBUG:
                            print(f"Skipping {path} - '{query}' not found in filename '{filename}'")
                        continue
            
            # For exact search on non-file types, do additional filename checking (only if not using wildcards)
            elif self.exact_search.get() and '*' not in query and '?' not in query:
                filename = os.path.basename(path)
                # Check if query is exact match (whole word) in filename
                pattern = r'\b' + re.escape(query) + r'\b'
                if not re.search(pattern, filename, re.IGNORECASE):
                    if DEBUG:
                        print(f"Skipping {path} - '{query}' not found as exact word in filename '{filename}'")
                    continue
            
            # For wildcard searches on non-file types, apply pattern matching
            elif '*' in query or '?' in query:
                filename = os.path.basename(path)
                # Convert simple wildcards to regex
                pattern = query.replace('*', '.*').replace('?', '.')
                pattern = f'^{pattern}$'  # Match entire filename
                try:
                    if not re.search(pattern, filename, re.IGNORECASE):
                        if DEBUG:
                            print(f"Skipping {path} - '{filename}' doesn't match pattern '{pattern}'")
                        continue
                except re.error as e:
                    if DEBUG:
                        print(f"Invalid regex pattern '{pattern}': {e}")
                    continue
                
            if DEBUG:
                print(f"Including: {path}")
            filtered.append(path)
                
        if DEBUG:
            print(f"Filtered {len(paths)} -> {len(filtered)} results")
                
        return filtered
            
    def display_results(self, paths, query, search_time=None):
        self.clear_results()
        
        count = 0
        for path in paths:
            if not path.strip():
                continue
                
            # Check if search was cancelled during display
            if self.search_stop_event.is_set():
                return
                
            try:
                path_obj = Path(path)
                name = path_obj.name
                directory = str(path_obj.parent)
                
                if os.path.exists(path):
                    try:
                        stat_info = os.stat(path)
                        size = self.format_size(stat_info.st_size)
                    except (OSError, PermissionError):
                        size = "N/A"
                else:
                    size = "N/A"
                    
                self.tree.insert('', 'end', values=(name, directory, size))
                count += 1
                
            except (OSError, PermissionError) as e:
                if DEBUG:
                    print(f"[DEBUG] Permission error processing {path}: {e}")
                continue
            except Exception as e:
                if DEBUG:
                    print(f"[DEBUG] Error processing {path}: {e}")
                continue
                
        # Only update status if search wasn't cancelled
        if not self.search_stop_event.is_set():
            time_text = f" in {search_time:.2f}s" if search_time else ""
            self.status_label.config(text=f"Found {count} results for '{query}'{time_text}")
            self.results_count_label.config(text=f"{count} items")
        
    def display_no_results(self, query):
        self.clear_results()
        self.status_label.config(text=f"No results found for '{query}'")
        self.results_count_label.config(text="0 items")
        
    def update_database_gui(self):
        """Update plocate database using GUI sudo prompt"""
        def run_update():
            try:
                self.update_btn.config(state='disabled', text='Updating...')
                self.status_label.config(text="Updating plocate database...")
                
                if DEBUG:
                    print("Starting database update with GUI sudo...")
                
                # Use pkexec for GUI sudo prompt
                result = subprocess.run(
                    ['pkexec', 'updatedb'], 
                    capture_output=True, 
                    text=True, 
                    timeout=120
                )
                
                if result.returncode == 0:
                    self.root.after(0, lambda: self.status_label.config(text="Database updated successfully!"))
                    self.root.after(0, lambda: messagebox.showinfo("Success", "Database updated successfully!"))
                    if DEBUG:
                        print("Database update completed successfully")
                    
                    # Re-run search if there's a current query
                    current_query = self.search_var.get().strip()
                    if current_query and len(current_query) >= 2:
                        if DEBUG:
                            print(f"Re-running search for: '{current_query}' after database update")
                        self.root.after(1000, self.debounced_search)  # Wait 1 second then re-search
                else:
                    error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                    if "cancelled" in error_msg.lower() or "dismissed" in error_msg.lower():
                        self.root.after(0, lambda: self.status_label.config(text="Database update cancelled"))
                        if DEBUG:
                            print("Database update cancelled by user")
                    else:
                        self.root.after(0, lambda: self.status_label.config(text="Failed to update database"))
                        self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to update database:\n{error_msg}"))
                        if DEBUG:
                            print(f"Database update failed: {error_msg}")
                        
            except subprocess.TimeoutExpired:
                self.root.after(0, lambda: self.status_label.config(text="Database update timeout"))
                self.root.after(0, lambda: messagebox.showerror("Error", "Database update timed out"))
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: self.status_label.config(text="Database update error"))
                self.root.after(0, lambda: messagebox.showerror("Error", f"Error updating database:\n{error_msg}"))
                if DEBUG:
                    print(f"Database update exception: {error_msg}")
            finally:
                self.root.after(0, lambda: self.update_btn.config(state='normal', text='Update DB'))
                
        # Run update in background thread
        threading.Thread(target=run_update, daemon=True).start()
        
    def clear_results(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
    def clear_search(self, event=None):
        self.search_var.set("")
        self.clear_results()
        self.status_label.config(text="Ready. Start typing to search...")
        self.results_count_label.config(text="")
        # Reset options to defaults
        self.search_location.set("/")
        self.exact_search.set(True)
        self.file_type.set("all")
        
    def on_enter_pressed(self, event):
        selection = self.tree.selection()
        if selection:
            self.on_item_double_click(None)
            
    def on_item_double_click(self, event):
        selection = self.tree.selection()
        if not selection:
            return
            
        item = self.tree.item(selection[0])
        values = item['values']
        if len(values) >= 2:
            name = values[0]
            directory = values[1]
            full_path = os.path.join(directory, name)
            
            if DEBUG:
                print(f"Attempting to open: {full_path}")
            
            try:
                # Check if file/directory exists first
                if not os.path.exists(full_path):
                    messagebox.showwarning("Warning", f"File not found: {full_path}")
                    return
                    
                # Check permissions
                if not os.access(full_path, os.R_OK):
                    messagebox.showerror("Error", f"Permission denied: {full_path}")
                    return
                
                if os.path.isfile(full_path):
                    result = subprocess.run(['xdg-open', full_path], capture_output=True, text=True)
                    if result.returncode != 0 and DEBUG:
                        print(f"xdg-open returned {result.returncode}: {result.stderr}")
                elif os.path.isdir(full_path):
                    result = subprocess.run(['xdg-open', full_path], capture_output=True, text=True)
                    if result.returncode != 0 and DEBUG:
                        print(f"xdg-open returned {result.returncode}: {result.stderr}")
                else:
                    messagebox.showwarning("Warning", f"Unknown file type: {full_path}")
                    
            except (OSError, PermissionError) as e:
                messagebox.showerror("Error", f"Permission error opening {full_path}: {e}")
                if DEBUG:
                    print(f"Permission error opening {full_path}: {e}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open {full_path}: {e}")
                if DEBUG:
                    print(f"Error opening {full_path}: {e}")
                
    def format_size(self, size_bytes):
        if size_bytes == 0:
            return "0 B"
            
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
            
        return f"{size_bytes:.1f} {size_names[i]}"

    def edit_ignore_pattern(self):
        """Edit selected ignore pattern"""
        selection = self.ignore_listbox.curselection()
        if not selection:
            return
            
        index = selection[0]
        current_pattern = self.ignore_listbox.get(index)
        
        # Create edit dialog
        edit_dialog = tk.Toplevel(self.current_ignore_window)
        edit_dialog.title("Edit Ignore Pattern")
        edit_dialog.geometry("500x150")
        edit_dialog.configure(bg='#2b2b2b')
        edit_dialog.transient(self.current_ignore_window)
        
        # Center the dialog
        edit_dialog.update_idletasks()
        x = (edit_dialog.winfo_screenwidth() - 500) // 2
        y = (edit_dialog.winfo_screenheight() - 150) // 2
        edit_dialog.geometry(f"500x150+{x}+{y}")
        
        # Wait for window to be viewable before grabbing
        edit_dialog.wait_visibility()
        edit_dialog.grab_set()
        
        main_frame = tk.Frame(edit_dialog, bg='#2b2b2b')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(
            main_frame,
            text="Edit pattern:",
            bg='#2b2b2b',
            fg='white',
            font=('Arial', 10)
        ).pack(anchor=tk.W, pady=(0, 5))
        
        edit_entry = tk.Entry(
            main_frame,
            bg='#404040',
            fg='white',
            font=('Arial', 10),
            insertbackground='white'
        )
        edit_entry.pack(fill=tk.X, pady=(0, 10))
        edit_entry.insert(0, current_pattern)
        edit_entry.select_range(0, tk.END)
        edit_entry.focus()
        
        def save_pattern():
            new_pattern = edit_entry.get().strip()
            if new_pattern and new_pattern not in self.ignore_patterns:
                old_pattern = self.ignore_patterns[index]
                self.ignore_patterns[index] = new_pattern
                self.ignore_listbox.delete(index)
                self.ignore_listbox.insert(index, new_pattern)
                self.ignore_listbox.selection_set(index)
                if DEBUG:
                    print(f"[DEBUG] Updated pattern: {old_pattern} -> {new_pattern}")
            edit_dialog.destroy()
            
        def cancel_edit():
            edit_dialog.destroy()
        
        buttons_frame = tk.Frame(main_frame, bg='#2b2b2b')
        buttons_frame.pack(fill=tk.X)
        
        save_btn = tk.Button(
            buttons_frame,
            text="Save",
            command=save_pattern,
            bg='#505050',
            fg='white',
            font=('Arial', 10),
            relief=tk.FLAT,
            cursor='hand2',
            width=8
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        cancel_btn = tk.Button(
            buttons_frame,
            text="Cancel",
            command=cancel_edit,
            bg='#505050',
            fg='white',
            font=('Arial', 10),
            relief=tk.FLAT,
            cursor='hand2',
            width=8
        )
        cancel_btn.pack(side=tk.LEFT)
        
        # Bind Enter and Escape keys
        edit_entry.bind('<Return>', lambda e: save_pattern())
        edit_dialog.bind('<Escape>', lambda e: cancel_edit())
        
        if DEBUG:
            print(f"[DEBUG] Editing pattern at index {index}: {current_pattern}")

    def sort_by_column(self, column):
        """Sort treeview by column"""
        # Toggle sort direction if same column clicked
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
            
        # Get all items from tree
        items = [(self.tree.set(child, column), child) for child in self.tree.get_children('')]
        
        # Sort items based on column type
        if column == 'size':
            # Sort by size numerically
            def get_size_value(item):
                size_text = item[0]
                if size_text == "N/A" or size_text == "":
                    return -1
                if "KB" in size_text:
                    return float(size_text.replace(" KB", "").replace(",", "")) * 1024
                elif "MB" in size_text:
                    return float(size_text.replace(" MB", "").replace(",", "")) * 1024 * 1024
                elif "GB" in size_text:
                    return float(size_text.replace(" GB", "").replace(",", "")) * 1024 * 1024 * 1024
                elif "B" in size_text:
                    return float(size_text.replace(" B", "").replace(",", ""))
                else:
                    try:
                        return float(size_text.replace(",", ""))
                    except ValueError:
                        return -1
                        
            items.sort(key=get_size_value, reverse=self.sort_reverse)
        else:
            # Sort alphabetically for name and path
            items.sort(key=lambda x: x[0].lower(), reverse=self.sort_reverse)
        
        # Rearrange items in tree
        for index, (val, child) in enumerate(items):
            self.tree.move(child, '', index)
            
        # Update column headers with sort indicators
        for col in ['name', 'path', 'size']:
            if col == column:
                direction = " ↓" if self.sort_reverse else " ↑"
                text = col.capitalize() + direction
            else:
                text = col.capitalize()
            self.tree.heading(col, text=text)
            
        if DEBUG:
            print(f"[DEBUG] Sorted by {column}, reverse={self.sort_reverse}")

    def on_right_click(self, event):
        """Handle right-click on treeview item"""
        item = self.tree.selection()
        if not item:
            return
            
        # Get the file path from the selected item
        item_id = item[0]
        file_path = self.tree.set(item_id, 'path')
        
        if not file_path or not os.path.exists(file_path):
            return
            
        # Create context menu
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.configure(bg='#404040', fg='white', activebackground='#606060', activeforeground='white')
        
        if os.path.isfile(file_path):
            context_menu.add_command(
                label="Open File", 
                command=lambda: self.open_with_default_app(file_path)
            )
            context_menu.add_command(
                label="Open Containing Folder", 
                command=lambda: self.open_folder_location(file_path)
            )
        else:
            context_menu.add_command(
                label="Open Folder", 
                command=lambda: self.open_with_default_app(file_path)
            )
            
        context_menu.add_separator()
        context_menu.add_command(
            label="Copy Path", 
            command=lambda: self.copy_to_clipboard(file_path)
        )
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
            
        if DEBUG:
            print(f"[DEBUG] Right-click context menu for: {file_path}")

    def open_with_default_app(self, file_path):
        """Open file or folder with default application"""
        try:
            subprocess.run(['xdg-open', file_path], check=True)
            if DEBUG:
                print(f"[DEBUG] Opened with default app: {file_path}")
        except subprocess.CalledProcessError as e:
            if DEBUG:
                print(f"[DEBUG] Failed to open {file_path}: {e}")
            messagebox.showerror("Error", f"Failed to open: {file_path}")
            
    def open_folder_location(self, file_path):
        """Open the folder containing the file"""
        try:
            folder_path = os.path.dirname(file_path)
            subprocess.run(['xdg-open', folder_path], check=True)
            if DEBUG:
                print(f"[DEBUG] Opened folder location: {folder_path}")
        except subprocess.CalledProcessError as e:
            if DEBUG:
                print(f"[DEBUG] Failed to open folder {folder_path}: {e}")
            messagebox.showerror("Error", f"Failed to open folder: {os.path.dirname(file_path)}")
            
    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            if DEBUG:
                print(f"[DEBUG] Copied to clipboard: {text}")
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Failed to copy to clipboard: {e}")

def main():
    if DEBUG:
        print("Starting Everything Linux...")
        
    root = tk.Tk()
    app = EverythingLinux(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nExiting...")
        
if __name__ == "__main__":
    main()
