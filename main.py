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
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

class CSVFilterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CSV Multi-Filter - Remove Empty First Names (Up to 5 Files)")
        
        # Color scheme (Light Theme)
        self.bg_color = "#ffffff"  # White background
        self.fg_color = "#000000"  # Black text
        self.button_bg = "#e0e0e0"  # Light gray buttons
        self.button_hover = "#d0d0d0"  # Darker gray on hover
        self.accent_color = "#808080"  # Medium gray accent
        self.entry_bg = "#f5f5f5"  # Very light gray for entries
        self.success_color = "#4CAF50"  # Green for success
        self.error_color = "#f44336"  # Red for errors
        
        # Configure root
        self.root.configure(bg=self.bg_color)
        self.root.minsize(900, 750)
        
        # Center window
        self.center_window(900, 750)
        
        # Configure DPI scaling
        self.setup_dpi_scaling()
        
        # Setup fonts (using system defaults)
        self.main_font = ('Arial', 10)
        self.title_font = ('Arial', 14, 'bold')
        self.button_font = ('Arial', 11)
        self.credit_font = ('Arial', 9)
        self.small_font = ('Arial', 9)
        
        # Variables for multiple files
        self.max_files = 5
        self.input_files = [tk.StringVar() for _ in range(self.max_files)]
        self.output_files = [tk.StringVar() for _ in range(self.max_files)]
        self.file_status = [tk.StringVar(value="") for _ in range(self.max_files)]
        self.progress_queue = queue.Queue()
        self.processing = False
        
        # Get optimal number of workers
        self.num_workers = min(multiprocessing.cpu_count(), 4)
        
        # File entries and buttons storage
        self.input_entries = []
        self.output_entries = []
        self.browse_input_btns = []
        self.browse_output_btns = []
        self.status_labels = []
        self.clear_btns = []
        
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
        # Main container with scrollbar
        main_canvas = tk.Canvas(self.root, bg=self.bg_color)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        main_canvas.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=20)
        
        # Main frame inside scrollable area
        main_frame = scrollable_frame
        
        # Configure ttk styles
        self.setup_styles()
        
        # Title with border
        title_frame = tk.Frame(main_frame, bg=self.bg_color, relief=tk.RIDGE, bd=2)
        title_frame.grid(row=0, column=0, pady=(0, 10), padx=10, sticky="ew")
        
        title_label = tk.Label(
            title_frame,
            text="CSV Multi-File First Name Filter",
            font=self.title_font,
            bg=self.bg_color,
            fg=self.fg_color,
            padx=20,
            pady=10
        )
        title_label.pack()
        
        # Info label
        info_label = tk.Label(
            main_frame,
            text=f"Process up to {self.max_files} CSV files simultaneously | Using {self.num_workers} parallel workers",
            font=self.small_font,
            bg=self.bg_color,
            fg=self.accent_color
        )
        info_label.grid(row=1, column=0, pady=(0, 10))
        
        # Files section
        files_frame = tk.LabelFrame(
            main_frame,
            text="Files to Process",
            font=self.main_font,
            bg=self.bg_color,
            fg=self.fg_color,
            relief=tk.GROOVE,
            bd=2
        )
        files_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        
        # Create file input/output rows
        for i in range(self.max_files):
            self.create_file_row(files_frame, i)
        
        # Control buttons frame
        control_frame = tk.Frame(main_frame, bg=self.bg_color)
        control_frame.grid(row=3, column=0, pady=15)
        
        # Clear All button
        self.clear_all_btn = self.create_button(
            control_frame,
            "Clear All",
            self.clear_all_files,
            width=12
        )
        self.clear_all_btn.grid(row=0, column=0, padx=5)
        
        # Process button
        self.process_btn = self.create_button(
            control_frame,
            "Process All Files",
            self.process_all_csv,
            width=20,
            special=True
        )
        self.process_btn.grid(row=0, column=1, padx=5)
        
        # Auto-fill button
        self.autofill_btn = self.create_button(
            control_frame,
            "Auto-Fill Outputs",
            self.autofill_outputs,
            width=15
        )
        self.autofill_btn.grid(row=0, column=2, padx=5)
        
        # Overall progress bar
        progress_frame = tk.LabelFrame(
            main_frame,
            text="Overall Progress",
            font=self.main_font,
            bg=self.bg_color,
            fg=self.fg_color,
            relief=tk.GROOVE,
            bd=2
        )
        progress_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=10)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.progress_label = tk.Label(
            progress_frame,
            text="Ready",
            font=self.small_font,
            bg=self.bg_color,
            fg=self.fg_color
        )
        self.progress_label.grid(row=1, column=0, pady=(0, 10))
        
        # Statistics frame
        stats_frame = tk.LabelFrame(
            main_frame,
            text="Processing Statistics",
            font=self.main_font,
            bg=self.bg_color,
            fg=self.fg_color,
            relief=tk.GROOVE,
            bd=2
        )
        stats_frame.grid(row=5, column=0, sticky="ew", padx=10, pady=10)
        stats_frame.columnconfigure(0, weight=1)
        
        # Create scrolled text for statistics
        stats_container = tk.Frame(stats_frame, bg=self.bg_color)
        stats_container.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.stats_text = tk.Text(
            stats_container,
            height=8,
            font=self.main_font,
            bg=self.entry_bg,
            fg=self.fg_color,
            relief=tk.SOLID,
            bd=1,
            wrap=tk.WORD
        )
        self.stats_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        stats_scroll = ttk.Scrollbar(stats_container, command=self.stats_text.yview)
        stats_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.stats_text.config(yscrollcommand=stats_scroll.set)
        
        # Credits section with gray background
        credits_frame = tk.Frame(main_frame, bg=self.accent_color, relief=tk.RAISED, bd=1)
        credits_frame.grid(row=6, column=0, sticky="ew", padx=10, pady=(20, 10))
        
        credits_text = """Enhanced Multi-File Version | Developed By: Nader Mahbub Khan
Software Engineer | Web Developer
Phone: 01642817116 | Email: muhammadnadermahbubkhan@gmail.com"""
        
        tk.Label(
            credits_frame,
            text=credits_text,
            font=self.credit_font,
            bg=self.accent_color,
            fg=self.bg_color,
            justify=tk.CENTER
        ).pack(pady=10)
    
    def create_file_row(self, parent, index):
        """Create a row for file input/output"""
        row_frame = tk.Frame(parent, bg=self.bg_color)
        row_frame.grid(row=index, column=0, sticky="ew", padx=10, pady=5)
        row_frame.columnconfigure(2, weight=1)
        row_frame.columnconfigure(5, weight=1)
        
        # File number
        tk.Label(
            row_frame,
            text=f"File {index + 1}:",
            font=self.main_font,
            bg=self.bg_color,
            fg=self.fg_color,
            width=6
        ).grid(row=0, column=0, padx=(0, 5))
        
        # Input section
        tk.Label(
            row_frame,
            text="Input:",
            font=self.small_font,
            bg=self.bg_color,
            fg=self.fg_color
        ).grid(row=0, column=1, padx=(0, 5))
        
        input_entry = tk.Entry(
            row_frame,
            textvariable=self.input_files[index],
            font=self.small_font,
            bg=self.entry_bg,
            fg=self.fg_color,
            relief=tk.SOLID,
            bd=1,
            width=30
        )
        input_entry.grid(row=0, column=2, sticky="ew", padx=(0, 5))
        self.input_entries.append(input_entry)
        
        browse_input = self.create_button(
            row_frame,
            "📁",
            lambda idx=index: self.browse_input_file(idx),
            width=3
        )
        browse_input.grid(row=0, column=3, padx=(0, 10))
        self.browse_input_btns.append(browse_input)
        
        # Output section
        tk.Label(
            row_frame,
            text="Output:",
            font=self.small_font,
            bg=self.bg_color,
            fg=self.fg_color
        ).grid(row=0, column=4, padx=(0, 5))
        
        output_entry = tk.Entry(
            row_frame,
            textvariable=self.output_files[index],
            font=self.small_font,
            bg=self.entry_bg,
            fg=self.fg_color,
            relief=tk.SOLID,
            bd=1,
            width=30
        )
        output_entry.grid(row=0, column=5, sticky="ew", padx=(0, 5))
        self.output_entries.append(output_entry)
        
        browse_output = self.create_button(
            row_frame,
            "💾",
            lambda idx=index: self.browse_output_file(idx),
            width=3
        )
        browse_output.grid(row=0, column=6, padx=(0, 5))
        self.browse_output_btns.append(browse_output)
        
        # Clear button
        clear_btn = self.create_button(
            row_frame,
            "✖",
            lambda idx=index: self.clear_file_row(idx),
            width=3
        )
        clear_btn.grid(row=0, column=7, padx=(0, 5))
        self.clear_btns.append(clear_btn)
        
        # Status label
        status_label = tk.Label(
            row_frame,
            textvariable=self.file_status[index],
            font=self.small_font,
            bg=self.bg_color,
            fg=self.accent_color,
            width=10
        )
        status_label.grid(row=0, column=8, padx=(5, 0))
        self.status_labels.append(status_label)
    
    def setup_styles(self):
        """Setup ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Progress bar style - gray theme
        style.configure(
            "Custom.Horizontal.TProgressbar",
            background=self.accent_color,
            troughcolor=self.entry_bg,
            bordercolor=self.accent_color,
            lightcolor=self.accent_color,
            darkcolor=self.accent_color
        )
    
    def create_button(self, parent, text, command, width=10, special=False):
        """Create a styled button"""
        if special:
            bg = self.accent_color
            fg = self.bg_color
            hover_bg = "#606060"
        else:
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
            padx=10,
            pady=5,
            width=width,
            cursor="hand2"
        )
        
        btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        
        return btn
    
    def browse_input_file(self, index):
        """Browse for input CSV file"""
        filename = filedialog.askopenfilename(
            title=f"Select Input CSV File {index + 1}",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if filename:
            self.input_files[index].set(filename)
            self.file_status[index].set("")
    
    def browse_output_file(self, index):
        """Browse for output CSV file location"""
        default_name = ""
        if self.input_files[index].get():
            input_path = Path(self.input_files[index].get())
            default_name = f"{input_path.stem}_filtered.csv"
        
        filename = filedialog.asksaveasfilename(
            title=f"Save Filtered CSV {index + 1} As",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if filename:
            self.output_files[index].set(filename)
    
    def clear_file_row(self, index):
        """Clear a specific file row"""
        self.input_files[index].set("")
        self.output_files[index].set("")
        self.file_status[index].set("")
    
    def clear_all_files(self):
        """Clear all file inputs and outputs"""
        for i in range(self.max_files):
            self.clear_file_row(i)
        self.stats_text.delete(1.0, tk.END)
        self.progress_var.set(0)
        self.progress_label.config(text="Ready")
    
    def autofill_outputs(self):
        """Auto-generate output filenames based on input files"""
        for i in range(self.max_files):
            if self.input_files[i].get() and not self.output_files[i].get():
                input_path = Path(self.input_files[i].get())
                output_path = input_path.parent / f"{input_path.stem}_filtered.csv"
                self.output_files[i].set(str(output_path))
    
    def get_valid_file_pairs(self):
        """Get list of valid input/output file pairs"""
        valid_pairs = []
        for i in range(self.max_files):
            if self.input_files[i].get() and self.output_files[i].get():
                if not os.path.exists(self.input_files[i].get()):
                    self.file_status[i].set("❌ Not Found")
                    continue
                valid_pairs.append((i, self.input_files[i].get(), self.output_files[i].get()))
                self.file_status[i].set("⏳ Queued")
        return valid_pairs
    
    def process_all_csv(self):
        """Process all CSV files in parallel"""
        if self.processing:
            return
        
        valid_pairs = self.get_valid_file_pairs()
        
        if not valid_pairs:
            messagebox.showerror("Error", "No valid file pairs found. Please select at least one input and output file.")
            return
        
        self.processing = True
        self.process_btn.config(state=tk.DISABLED, text="Processing...")
        self.stats_text.delete(1.0, tk.END)
        self.progress_var.set(0)
        
        # Start processing in separate thread
        thread = threading.Thread(target=self.process_files_thread, args=(valid_pairs,), daemon=True)
        thread.start()
        
        # Start monitoring progress
        self.monitor_progress()
    
    def process_single_csv(self, file_index, input_file, output_file):
        """Process a single CSV file (optimized for parallel execution)"""
        try:
            start_time = time.time()
            self.file_status[file_index].set("🔄 Processing")
            
            # Read CSV with optimization
            chunk_size = 50000  # Larger chunks for better performance
            total_rows = 0
            captured_rows = 0
            skipped_rows = 0
            
            # Quick row count
            with open(input_file, 'r', encoding='utf-8-sig') as f:
                total_rows = sum(1 for line in f) - 1
            
            # Process chunks with optimized settings
            filtered_chunks = []
            
            # Use engine='c' for faster parsing
            reader = pd.read_csv(
                input_file,
                chunksize=chunk_size,
                encoding='utf-8-sig',
                engine='c',  # C engine is faster
                low_memory=False,
                na_values=['', ' ', '  '],
                keep_default_na=True
            )
            
            for chunk in reader:
                if 'First Name' in chunk.columns:
                    # Vectorized operation for better performance
                    first_name_col = chunk['First Name']
                    mask = first_name_col.notna() & (first_name_col.astype(str).str.strip() != '')
                    filtered_chunk = chunk.loc[mask]
                    
                    captured_rows += len(filtered_chunk)
                    skipped_rows += len(chunk) - len(filtered_chunk)
                    
                    if not filtered_chunk.empty:
                        filtered_chunks.append(filtered_chunk)
                else:
                    raise ValueError(f"Column 'First Name' not found in {os.path.basename(input_file)}")
            
            # Combine and save with optimization
            if filtered_chunks:
                result_df = pd.concat(filtered_chunks, ignore_index=True)
                # Use faster CSV writing
                result_df.to_csv(
                    output_file,
                    index=False,
                    encoding='utf-8-sig',
                    chunksize=chunk_size  # Write in chunks too
                )
                del result_df
            else:
                pd.DataFrame(columns=chunk.columns).to_csv(
                    output_file,
                    index=False,
                    encoding='utf-8-sig'
                )
            
            # Clean up
            del filtered_chunks
            gc.collect()
            
            processing_time = time.time() - start_time
            
            # Return statistics
            return {
                'file_index': file_index,
                'input_file': os.path.basename(input_file),
                'output_file': os.path.basename(output_file),
                'total_rows': total_rows,
                'captured_rows': captured_rows,
                'skipped_rows': skipped_rows,
                'processing_time': processing_time,
                'success': True,
                'error': None
            }
            
        except Exception as e:
            return {
                'file_index': file_index,
                'input_file': os.path.basename(input_file),
                'output_file': os.path.basename(output_file),
                'success': False,
                'error': str(e)
            }
    
    def process_files_thread(self, valid_pairs):
        """Process multiple CSV files in parallel threads"""
        try:
            overall_start = time.time()
            total_files = len(valid_pairs)
            
            self.progress_queue.put(("status", f"Processing {total_files} file(s) in parallel..."))
            self.progress_queue.put(("progress_label", f"0/{total_files} files completed"))
            
            results = []
            completed = 0
            
            # Use ThreadPoolExecutor for parallel processing
            with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(
                        self.process_single_csv, 
                        file_index, 
                        input_file, 
                        output_file
                    ): (file_index, input_file, output_file)
                    for file_index, input_file, output_file in valid_pairs
                }
                
                # Process completed tasks
                for future in as_completed(future_to_file):
                    file_index, input_file, output_file = future_to_file[future]
                    
                    try:
                        result = future.result()
                        results.append(result)
                        
                        if result['success']:
                            self.file_status[file_index].set("✅ Complete")
                            status_msg = f"✅ File {file_index + 1}: {result['input_file']} - Captured {result['captured_rows']:,} rows"
                        else:
                            self.file_status[file_index].set("❌ Error")
                            status_msg = f"❌ File {file_index + 1}: {result['input_file']} - Error: {result['error']}"
                        
                        self.progress_queue.put(("status", status_msg))
                        
                    except Exception as e:
                        self.file_status[file_index].set("❌ Failed")
                        self.progress_queue.put(("status", f"❌ File {file_index + 1} failed: {str(e)}"))
                    
                    completed += 1
                    progress = (completed / total_files) * 100
                    self.progress_queue.put(("progress", progress))
                    self.progress_queue.put(("progress_label", f"{completed}/{total_files} files completed"))
            
            # Calculate overall statistics
            overall_time = time.time() - overall_start
            successful_files = sum(1 for r in results if r.get('success', False))
            failed_files = len(results) - successful_files
            
            total_rows_all = sum(r.get('total_rows', 0) for r in results if r.get('success', False))
            captured_rows_all = sum(r.get('captured_rows', 0) for r in results if r.get('success', False))
            skipped_rows_all = sum(r.get('skipped_rows', 0) for r in results if r.get('success', False))
            
            # Generate detailed statistics
            stats_text = f"""
╔══════════════════════════════════════════════════════════╗
║                   PROCESSING COMPLETE                      ║
╚══════════════════════════════════════════════════════════╝

📊 OVERALL STATISTICS:
━━━━━━━━━━━━━━━━━━━━━━
• Files Processed: {successful_files}/{total_files}
• Failed Files: {failed_files}
• Total Rows Processed: {total_rows_all:,}
• Total Captured: {captured_rows_all:,}
• Total Skipped: {skipped_rows_all:,}
• Total Processing Time: {overall_time:.2f} seconds
• Average Speed: {total_rows_all/overall_time:.0f} rows/second

📁 FILE DETAILS:
━━━━━━━━━━━━━━━"""
            
            for result in results:
                if result.get('success', False):
                    stats_text += f"""
File: {result['input_file']}
  ✅ Captured: {result['captured_rows']:,} | Skipped: {result['skipped_rows']:,}
  ⏱️ Time: {result['processing_time']:.2f}s | Speed: {result['total_rows']/result['processing_time']:.0f} rows/s"""
                else:
                    stats_text += f"""
File: {result['input_file']}
  ❌ Error: {result['error']}"""
            
            self.progress_queue.put(("stats", stats_text))
            self.progress_queue.put(("complete", (successful_files, failed_files)))
            
        except Exception as e:
            self.progress_queue.put(("error", str(e)))
    
    def monitor_progress(self):
        """Monitor progress from the processing thread"""
        try:
            while not self.progress_queue.empty():
                msg_type, msg_data = self.progress_queue.get_nowait()
                
                if msg_type == "progress":
                    self.progress_var.set(msg_data)
                elif msg_type == "progress_label":
                    self.progress_label.config(text=msg_data)
                elif msg_type == "status":
                    self.stats_text.insert(tk.END, msg_data + "\n")
                    self.stats_text.see(tk.END)
                elif msg_type == "stats":
                    self.stats_text.delete(1.0, tk.END)
                    self.stats_text.insert(tk.END, msg_data)
                elif msg_type == "complete":
                    successful, failed = msg_data
                    self.processing = False
                    self.process_btn.config(state=tk.NORMAL, text="Process All Files")
                    self.progress_label.config(text="Complete!")
                    
                    if failed > 0:
                        messagebox.showwarning(
                            "Processing Complete", 
                            f"Processing completed!\n✅ Successful: {successful} files\n❌ Failed: {failed} files\n\nCheck the statistics for details."
                        )
                    else:
                        messagebox.showinfo(
                            "Success", 
                            f"All {successful} file(s) processed successfully!"
                        )
                    return
                elif msg_type == "error":
                    self.processing = False
                    self.process_btn.config(state=tk.NORMAL, text="Process All Files")
                    self.progress_label.config(text="Error!")
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
    
    # Bind mousewheel to canvas for scrolling
    def on_mousewheel(event):
        canvas = root.winfo_children()[0]
        if isinstance(canvas, tk.Canvas):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    root.bind_all("<MouseWheel>", on_mousewheel)
    
    root.mainloop()

if __name__ == "__main__":
    main()
