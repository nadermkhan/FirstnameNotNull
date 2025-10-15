import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
import os
import sys
import time
import threading
from pathlib import Path
import queue
import gc

class CSVFilterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CSV Filter - Remove Empty First Names")
        
        # Color scheme (Light Theme)
        self.bg_color = "#ffffff"  # White background
        self.fg_color = "#000000"  # Black text
        self.button_bg = "#e0e0e0"  # Light gray buttons
        self.button_hover = "#d0d0d0"  # Darker gray on hover
        self.accent_color = "#808080"  # Medium gray accent
        self.entry_bg = "#f5f5f5"  # Very light gray for entries
        
        # Configure root
        self.root.configure(bg=self.bg_color)
        self.root.minsize(700, 600)
        
        # Center window
        self.center_window(700, 600)
        
        # Configure DPI scaling
        self.setup_dpi_scaling()
        
        # Setup fonts (using system defaults)
        self.main_font = ('Arial', 10)
        self.title_font = ('Arial', 14, 'bold')
        self.button_font = ('Arial', 11)
        self.credit_font = ('Arial', 9)
        
        # Variables
        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.progress_queue = queue.Queue()
        self.processing = False
        
        # Create UI
        self.create_widgets()
        
        # Make window resizable
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
    def setup_dpi_scaling(self):
        """Setup DPI awareness for Windows"""
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
        
        # Get DPI scale
        self.dpi_scale = self.root.tk.call('tk', 'scaling')
        if self.dpi_scale > 1.5:
            self.root.tk.call('tk', 'scaling', 1.5)
    
    def center_window(self, width, height):
        """Center the window on screen"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        """Create all UI widgets"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.columnconfigure(0, weight=1)
        
        # Configure ttk styles
        self.setup_styles()
        
        # Title with border
        title_frame = tk.Frame(main_frame, bg=self.bg_color, relief=tk.RIDGE, bd=2)
        title_frame.grid(row=0, column=0, pady=(0, 20))
        
        title_label = tk.Label(
            title_frame,
            text="CSV First Name Filter",
            font=self.title_font,
            bg=self.bg_color,
            fg=self.fg_color,
            padx=20,
            pady=10
        )
        title_label.pack()
        
        # Input file section
        input_frame = tk.Frame(main_frame, bg=self.bg_color)
        input_frame.grid(row=1, column=0, sticky="ew", pady=10)
        input_frame.columnconfigure(1, weight=1)
        
        tk.Label(
            input_frame,
            text="Input File:",
            font=self.main_font,
            bg=self.bg_color,
            fg=self.fg_color,
            width=12,
            anchor="w"
        ).grid(row=0, column=0, padx=(0, 10))
        
        self.input_entry = tk.Entry(
            input_frame,
            textvariable=self.input_file,
            font=self.main_font,
            bg=self.entry_bg,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            relief=tk.SOLID,
            bd=1
        )
        self.input_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        
        self.browse_input_btn = self.create_button(
            input_frame,
            "Browse",
            self.browse_input_file
        )
        self.browse_input_btn.grid(row=0, column=2)
        
        # Output file section
        output_frame = tk.Frame(main_frame, bg=self.bg_color)
        output_frame.grid(row=2, column=0, sticky="ew", pady=10)
        output_frame.columnconfigure(1, weight=1)
        
        tk.Label(
            output_frame,
            text="Output File:",
            font=self.main_font,
            bg=self.bg_color,
            fg=self.fg_color,
            width=12,
            anchor="w"
        ).grid(row=0, column=0, padx=(0, 10))
        
        self.output_entry = tk.Entry(
            output_frame,
            textvariable=self.output_file,
            font=self.main_font,
            bg=self.entry_bg,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            relief=tk.SOLID,
            bd=1
        )
        self.output_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        
        self.browse_output_btn = self.create_button(
            output_frame,
            "Browse",
            self.browse_output_file
        )
        self.browse_output_btn.grid(row=0, column=2)
        
        # Process button
        self.process_btn = self.create_button(
            main_frame,
            "Process CSV",
            self.process_csv,
            width=20,
            special=True
        )
        self.process_btn.grid(row=3, column=0, pady=20)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            maximum=100,
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        
        # Statistics frame
        stats_frame = tk.LabelFrame(
            main_frame,
            text="Statistics",
            font=self.main_font,
            bg=self.bg_color,
            fg=self.fg_color,
            relief=tk.GROOVE,
            bd=2
        )
        stats_frame.grid(row=5, column=0, sticky="ew", pady=10)
        stats_frame.columnconfigure(0, weight=1)
        
        self.stats_text = tk.Text(
            stats_frame,
            height=6,
            font=self.main_font,
            bg=self.entry_bg,
            fg=self.fg_color,
            relief=tk.SOLID,
            bd=1,
            wrap=tk.WORD
        )
        self.stats_text.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        # Credits section with gray background
        credits_frame = tk.Frame(main_frame, bg=self.accent_color, relief=tk.RAISED, bd=1)
        credits_frame.grid(row=6, column=0, sticky="ew", pady=(20, 0))
        
        credits_text = """Developed By: Nader Mahbub Khan
Software Engineer | Web Developer
Phone: 01642817116 | Email: muhammadnadermahbubkhan@gmail.com"""
        
        tk.Label(
            credits_frame,
            text=credits_text,
            font=self.credit_font,
            bg=self.accent_color,
            fg=self.bg_color,  # White text on gray background
            justify=tk.CENTER
        ).pack(pady=10)
    
    def setup_styles(self):
        """Setup ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Progress bar style - gray theme
        style.configure(
            "Custom.Horizontal.TProgressbar",
            background=self.accent_color,  # Gray progress
            troughcolor=self.entry_bg,  # Light gray trough
            bordercolor=self.accent_color,
            lightcolor=self.accent_color,
            darkcolor=self.accent_color
        )
    
    def create_button(self, parent, text, command, width=10, special=False):
        """Create a styled button"""
        if special:
            # Special button (Process CSV) - darker
            bg = self.accent_color
            fg = self.bg_color
            hover_bg = "#606060"
        else:
            # Regular buttons
            bg = self.button_bg
            fg = self.fg_color
            hover_bg = self.button_hover
        
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=self.button_font,
            bg=bg,
            fg=fg,
            activebackground=hover_bg,
            activeforeground=fg,
            relief=tk.RAISED,
            bd=1,
            padx=15,
            pady=5,
            width=width,
            cursor="hand2"
        )
        
        # Hover effects
        btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        
        return btn
    
    def browse_input_file(self):
        """Browse for input CSV file"""
        filename = filedialog.askopenfilename(
            title="Select Input CSV File",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if filename:
            self.input_file.set(filename)
    
    def browse_output_file(self):
        """Browse for output CSV file location"""
        filename = filedialog.asksaveasfilename(
            title="Save Filtered CSV As",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if filename:
            self.output_file.set(filename)
    
    def process_csv(self):
        """Process the CSV file in a separate thread"""
        if self.processing:
            return
        
        if not self.input_file.get():
            messagebox.showerror("Error", "Please select an input file")
            return
        
        if not self.output_file.get():
            messagebox.showerror("Error", "Please select an output file location")
            return
        
        if not os.path.exists(self.input_file.get()):
            messagebox.showerror("Error", "Input file does not exist")
            return
        
        self.processing = True
        self.process_btn.config(state=tk.DISABLED, text="Processing...")
        self.stats_text.delete(1.0, tk.END)
        self.progress_var.set(0)
        
        # Start processing in separate thread
        thread = threading.Thread(target=self.process_csv_thread, daemon=True)
        thread.start()
        
        # Start monitoring progress
        self.monitor_progress()
    
    def process_csv_thread(self):
        """Process CSV in separate thread for non-blocking UI"""
        try:
            start_time = time.time()
            
            # Update progress
            self.progress_queue.put(("status", "Reading CSV file..."))
            self.progress_queue.put(("progress", 10))
            
            # Read CSV with optimization
            chunk_size = 10000  # Process in chunks for memory efficiency
            total_rows = 0
            captured_rows = 0
            skipped_rows = 0
            
            # Count total rows first (fast method)
            with open(self.input_file.get(), 'r', encoding='utf-8-sig') as f:
                total_rows = sum(1 for line in f) - 1  # Subtract header
            
            self.progress_queue.put(("status", f"Processing {total_rows} rows..."))
            self.progress_queue.put(("progress", 20))
            
            # Process chunks
            filtered_chunks = []
            
            for chunk_num, chunk in enumerate(pd.read_csv(
                self.input_file.get(),
                chunksize=chunk_size,
                encoding='utf-8-sig',
                low_memory=False,
                na_values=['', ' ', '  '],  # Treat these as NaN
                keep_default_na=True
            )):
                # Filter rows where 'First Name' is not null/empty/whitespace
                if 'First Name' in chunk.columns:
                    # Efficient filtering
                    mask = chunk['First Name'].notna() & \
                           (chunk['First Name'].astype(str).str.strip() != '')
                    filtered_chunk = chunk[mask]
                    
                    captured_rows += len(filtered_chunk)
                    skipped_rows += len(chunk) - len(filtered_chunk)
                    
                    if not filtered_chunk.empty:
                        filtered_chunks.append(filtered_chunk)
                else:
                    messagebox.showerror("Error", "Column 'First Name' not found in CSV")
                    return
                
                # Update progress
                progress = 20 + (chunk_num * chunk_size / total_rows * 60)
                self.progress_queue.put(("progress", min(progress, 80)))
            
            self.progress_queue.put(("status", "Writing filtered data..."))
            self.progress_queue.put(("progress", 85))
            
            # Combine and save
            if filtered_chunks:
                result_df = pd.concat(filtered_chunks, ignore_index=True)
                result_df.to_csv(
                    self.output_file.get(),
                    index=False,
                    encoding='utf-8-sig'
                )
                del result_df  # Free memory
            else:
                # Create empty CSV with headers if no data
                pd.DataFrame(columns=chunk.columns).to_csv(
                    self.output_file.get(),
                    index=False,
                    encoding='utf-8-sig'
                )
            
            # Clean up memory
            del filtered_chunks
            gc.collect()
            
            self.progress_queue.put(("progress", 100))
            
            # Calculate statistics
            processing_time = time.time() - start_time
            
            stats = f"""Processing Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Total Rows Found: {total_rows:,}
✅ Captured Rows: {captured_rows:,}
❌ Skipped Rows: {skipped_rows:,}
⏱️ Processing Time: {processing_time:.2f} seconds
📁 Output File: {os.path.basename(self.output_file.get())}"""
            
            self.progress_queue.put(("stats", stats))
            self.progress_queue.put(("complete", True))
            
        except Exception as e:
            self.progress_queue.put(("error", str(e)))
    
    def monitor_progress(self):
        """Monitor progress from the processing thread"""
        try:
            while not self.progress_queue.empty():
                msg_type, msg_data = self.progress_queue.get_nowait()
                
                if msg_type == "progress":
                    self.progress_var.set(msg_data)
                elif msg_type == "status":
                    self.stats_text.insert(tk.END, msg_data + "\n")
                    self.stats_text.see(tk.END)
                elif msg_type == "stats":
                    self.stats_text.delete(1.0, tk.END)
                    self.stats_text.insert(tk.END, msg_data)
                elif msg_type == "complete":
                    self.processing = False
                    self.process_btn.config(state=tk.NORMAL, text="Process CSV")
                    messagebox.showinfo("Success", "CSV filtering completed successfully!")
                    return
                elif msg_type == "error":
                    self.processing = False
                    self.process_btn.config(state=tk.NORMAL, text="Process CSV")
                    messagebox.showerror("Error", f"An error occurred: {msg_data}")
                    return
        except queue.Empty:
            pass
        
        if self.processing:
            self.root.after(100, self.monitor_progress)

def main():
    """Main function to run the application"""
    root = tk.Tk()
    
    # Set window icon (optional)
    try:
        root.iconbitmap(default='icon.ico')
    except:
        pass
    
    app = CSVFilterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
