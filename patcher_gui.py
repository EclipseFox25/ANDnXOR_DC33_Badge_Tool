import os, sys, io, gc
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


try:
    from littlefs import LittleFS
except ImportError:
    sys.stderr.write("[!] Missing dependency: littlefs-python\n")
    sys.stderr.write("Install it with:\n    python3 -m pip install littlefs-python\n")
    sys.exit(1)
    
try:
    from PIL import Image, ImageTk
except ImportError:
    sys.stderr.write("[!] Missing dependency: Pillow (PIL)\n")
    sys.stderr.write("Install it with:\n    python3 -m pip install Pillow\n")
    sys.exit(1)

LFS_TYPE_DIR = 0x4000

OFFSET = 0x200000
BLOCK_SIZE = 4096


class FlashBlockDevice:
    def __init__(self, data: bytes, offset: int, block_size: int):
        self.data = bytearray(data)
        self.offset = offset
        self.block_size = block_size
        self.block_count = (len(data) - offset) // block_size

    def read(self, context, block, off, size):
        start = self.offset + block * self.block_size + off
        return bytes(self.data[start:start + size])

    def prog(self, context, block, off, data):
        start = self.offset + block * self.block_size + off
        self.data[start:start + len(data)] = data
        return 0

    def erase(self, context, block):
        start = self.offset + block * self.block_size
        end = start + self.block_size
        self.data[start:end] = b"\xFF" * self.block_size
        return 0

    def sync(self, context): return 0


class FSExplorerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AND!XOR DC33 BADGE TOOL")
        self.root.geometry("900x600")
        self.root.resizable(False, False)

        self.fs = None
        self.bd = None
        self.data = None
        self.dirty = False
        self.gif_image = None
        self.preview_job = None

        self.drag_start_y = None

        main = tk.Frame(root)
        main.pack(fill="both", expand=True)

        left = tk.Frame(main, width=600)
        left.pack(side="left", fill="both", expand=True)
        left.pack_propagate(False)

        right = tk.Frame(main, width=300, bg="#1e1e1e")
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        bar = tk.Frame(left)
        bar.pack(fill="x")
        tk.Button(bar, text="Open BIN", command=self.open_bin).pack(side="left")
        tk.Button(bar, text="Add", command=self.add_file).pack(side="left")
        tk.Button(bar, text="Delete", command=self.delete_selected).pack(side="left")
        tk.Button(bar, text="Extract Selected", command=self.extract_selected).pack(side="left")
        tk.Button(bar, text="Save", command=self.save_as).pack(side="left")

        # Enable multi-select
        self.tree = ttk.Treeview(left, columns=("type", "size"), show="tree headings", selectmode="extended")
        self.tree.heading("#0", text="Path")
        self.tree.heading("type", text="Type")
        self.tree.heading("size", text="Size")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Ctrl+A
        self.tree.bind("<Control-a>", lambda e: self.tree.selection_set(self.tree.get_children()))
        self.tree.bind("<Command-a>", lambda e: self.tree.selection_set(self.tree.get_children()))

        # Drag select
        self.tree.bind("<Button-1>", self.start_drag)
        self.tree.bind("<B1-Motion>", self.do_drag)
        self.tree.bind("<ButtonRelease-1>", self.end_drag)

        self.status = tk.StringVar()
        tk.Label(left, textvariable=self.status, anchor="w").pack(fill="x")

        tk.Label(right, text="GIF Preview", bg="#1e1e1e", fg="white").pack(pady=10)
        self.preview_canvas = tk.Canvas(right, width=128, height=128, bg="black", highlightthickness=0)
        self.preview_canvas.pack(pady=20)

    def set_status(self, msg): self.status.set(msg)

    def open_bin(self):
        path = filedialog.askopenfilename(filetypes=[("BIN files", "*.bin")])
        if not path:
            return
        with open(path, "rb") as f:
            self.data = f.read()
        self.bd = FlashBlockDevice(self.data, OFFSET, BLOCK_SIZE)
        self.fs = LittleFS(block_size=BLOCK_SIZE, block_count=self.bd.block_count,
                           read_size=16, prog_size=16, lookahead_size=16, context=self.bd)
        self.fs.mount()
        self.reload_tree()
        self.set_status(f"Loaded BIN: {os.path.basename(path)}")

    def reload_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.insert_dir("/", "")

    def insert_dir(self, path, parent):
        for name in sorted(self.fs.listdir(path)):
            full = path.rstrip("/") + "/" + name
            st = self.fs.stat(full)
            if st.type & LFS_TYPE_DIR:
                node = self.tree.insert(parent, "end", iid=full, text=full, values=("DIR", ""))
                self.insert_dir(full, node)
            else:
                size = getattr(st, "size", 0)
                self.tree.insert(parent, "end", iid=full, text=full, values=("FILE", size))

    def add_file(self):
        if not self.fs:
            return
        local = filedialog.askopenfilename()
        if not local:
            return
        dst = "/" + os.path.basename(local)
        try:
            self.fs.remove(dst)
        except:
            pass
        with open(local, "rb") as fsrc, self.fs.open(dst, "wb") as fdst:
            while chunk := fsrc.read(65536):
                fdst.write(chunk)
        self.dirty = True
        self.reload_tree()
        self.set_status(f"Added {dst}")
    
    def delete_selected(self):
        if not self.fs:
            return

        selected = self.tree.selection()
        if not selected:
            self.set_status("No files selected for deletion.")
            return

        deleted_count = 0
        for item in selected:
            # Get name from either `text` or first column
            raw_name = self.tree.item(item, "text")
            if not raw_name:
                vals = self.tree.item(item, "values")
                raw_name = vals[0] if vals else ""

            # Normalize path
            file_path = raw_name if raw_name.startswith("/") else f"/{raw_name}"

            try:
                self.fs.remove(file_path)
                deleted_count += 1
            except Exception as e:
                self.set_status(f"Error deleting {file_path}: {e}")

        self.dirty = True
        self.reload_tree()
        self.set_status(f"Deleted {deleted_count} file(s)")

    def extract_selected(self):
        if not self.fs:
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select one or more files or folders to extract.")
            return

        dest = filedialog.askdirectory(title="Select destination folder")
        if not dest:
            return

        def extract(src, dst):
            st = self.fs.stat(src)
            if st.type & LFS_TYPE_DIR:
                os.makedirs(dst, exist_ok=True)
                for nm in self.fs.listdir(src):
                    extract(src.rstrip("/") + "/" + nm, os.path.join(dst, nm))
            else:
                with self.fs.open(src, "rb") as fin, open(dst, "wb") as fout:
                    while chunk := fin.read(65536):
                        fout.write(chunk)

        for path in selected:
            name = os.path.basename(path.strip("/")) or "root"
            out_path = os.path.join(dest, name)
            extract(path, out_path)

        self.set_status(f"Extracted {len(selected)} item(s) to {dest}")

    def save_as(self):
        if not self.fs:
            return
        out = filedialog.asksaveasfilename(defaultextension=".bin")
        if not out:
            return
        with open(out, "wb") as f:
            f.write(self.bd.data)
        self.dirty = False
        self.set_status(f"Saved {out}")

    # Drag logic (no rectangle)
    def start_drag(self, event):
        self.drag_start_y = event.y
        self.tree.selection_remove(self.tree.selection())

    def do_drag(self, event):
        if self.drag_start_y is None:
            return
        y1, y2 = sorted([self.drag_start_y, event.y])
        for item in self.tree.get_children():
            bbox = self.tree.bbox(item)
            if not bbox:
                continue
            _, iy, _, ih = bbox
            if iy + ih >= y1 and iy <= y2:
                self.tree.selection_add(item)
            else:
                self.tree.selection_remove(item)

    def end_drag(self, event):
        self.drag_start_y = None

    def on_select(self, event):
        sel = self.tree.selection()
        if sel and len(sel) == 1:
            path = sel[0]
            if path.lower().endswith(".gif"):
                self.show_gif(path)
            else:
                self.clear_gif()
        else:
            self.clear_gif()

    def clear_gif(self):
        if self.preview_job:
            self.root.after_cancel(self.preview_job)
            self.preview_job = None
        if self.gif_image:
            try:
                self.gif_image.close()
            except:
                pass
        self.gif_image = None
        self.preview_canvas.delete("all")
        self.preview_canvas.image = None
        gc.collect()

    def show_gif(self, path):
        self.clear_gif()
        try:
            with self.fs.open(path, "rb") as f:
                data = f.read()
            self.gif_image = Image.open(io.BytesIO(data))
            self.gif_frames = getattr(self.gif_image, "n_frames", 1)
            self.frame_index = 0
            self.animate()
        except Exception as e:
            self.clear_gif()
            self.set_status(str(e))

    def animate(self):
        if not self.gif_image:
            return
        try:
            self.gif_image.seek(self.frame_index)
            frame = self.gif_image.copy().resize((128, 128))
            tk_frame = ImageTk.PhotoImage(frame)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(0, 0, anchor="nw", image=tk_frame)
            self.preview_canvas.image = tk_frame
            self.frame_index = (self.frame_index + 1) % self.gif_frames
            self.preview_job = self.root.after(100, self.animate)
        except EOFError:
            self.frame_index = 0
            self.preview_job = self.root.after(100, self.animate)


if __name__ == "__main__":
    root = tk.Tk()
    app = FSExplorerApp(root)
    root.mainloop()
