import os.path
import threading
from tkinter import filedialog
import tkinter as tk
import ModuleTool.PixelUI as ui
from  ModuleTool.EnDecode import Base64
from  ModuleTool.SystemTool import FileAssociationManager
from ModuleTool.QRcodeFun import generate_qr
import io
from PIL import Image, ImageDraw, ImageFont
import math, sys
from EncryptionTool import *

os.makedirs("Files", exist_ok=True)
def get_root_path():
    # 判断是否是打包后的exe
    if getattr(sys, 'frozen', False):
        # 打包后：返回exe所在的文件夹路径
        return os.path.dirname(sys.executable)
    # 正常运行.py：返回脚本所在目录
    return os.path.dirname(os.path.abspath(__file__))

script_dir = get_root_path()
base64 = Base64()
program_manager = FileAssociationManager("Zcret")

def get_nested_value(container, path):
    """
    读取嵌套容器内容，按path路径逐层访问
    :param container: 嵌套容器，支持dict/list/tuple/str
    :param path: 路径列表，dict用key，list/tuple/str用int索引
    :return: 路径指向的嵌套值
    索引溢出、键不存在直接抛出原生异常，不做捕获校验
    """
    current = container
    for step in path:
        current = current[step]
    return current
def get_proportion_img(datas, size=256, main_col="white", bg_col="black", font_col="green"):
    sum_num = sum(datas.values())
    bg = Image.new("RGB", (size, size), bg_col)
    draw = ImageDraw.Draw(bg)
    my_font = ImageFont.truetype(r"Pixel_Font.ttf", size=size / 24)

    midx = size // 2
    r = size // 2 * 0.9
    draw.circle((midx, midx), r, fill=main_col)
    draw.line((midx, midx, midx, midx - r), width=size // 64, fill=bg_col)
    count = 0
    i = 0
    for k, data in datas.items():
        count += data
        angle = count / sum_num * math.pi * 2 - math.pi / 2
        if i != len(datas) - 1:
            draw.line((midx, midx, midx + r * math.cos(angle), midx + r * math.sin(angle)), width=size // 64,
                      fill=bg_col)
        i += 1
        text_angle = (count - data / 2) / sum_num * math.pi * 2 - math.pi / 2
        draw.text((midx + r / 1.5 * math.cos(text_angle), midx + r / 1.5 * math.sin(text_angle)),
                  text=f"{k}\n{data / sum_num * 100:.1f}%", fill=font_col, font=my_font)

    return bg
def clean_folder(root_dir: str, remove_subdirs: bool = False):
    if not os.path.isdir(root_dir):
        return
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
        for name in filenames:
            file_path = os.path.join(dirpath, name)
            os.remove(file_path)

        if remove_subdirs:
            for name in dirnames:
                sub_dir = os.path.join(dirpath, name)
                os.rmdir(sub_dir)
    os.rmdir(root_dir)
def get_img_size(img: Image.Image, fmt: str = "PNG") -> int:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return len(buf.getvalue())
def get_config():
    if os.path.isfile("config.json"):
        with open("config.json", mode="r", encoding="utf-8") as f:
            encryption_config = json.loads(f.read())
    else:
        encryption_config = {
            "ExtName": "zorn",
            "HashTrunc": 16,
            "NsymSize": 32,
            "Compress": 1,
            "BlockSize": 1024**2*10,
            "PublicKey": "public_0.bin.zorn"
        }
        with open("config.json", mode="w", encoding="utf-8") as f:
            f.write(json.dumps(encryption_config, indent=4, ensure_ascii=False))
    return encryption_config
def save_config():
    global encryption_config
    with open("config.json", mode="w", encoding="utf-8") as f:
        f.write(json.dumps(encryption_config, indent=4, ensure_ascii=False))
def get_public_keys():
    if os.path.isfile("public_keys.json"):
        with open("public_keys.json", mode="r", encoding="utf-8") as f:
            public_keys = json.loads(f.read())
    else:
        public_keys = []
        with open("public_keys.json", mode="w", encoding="utf-8") as f:
            f.write(json.dumps(public_keys, indent=4, ensure_ascii=False))
    return public_keys
def save_public_keys():
    global public_keys
    with open("public_keys.json", mode="w", encoding="utf-8") as f:
        f.write(json.dumps(public_keys, indent=4, ensure_ascii=False))
def get_Instructions_config():
    if os.path.isfile("instructions_config.json"):
        with open("instructions_config.json", mode="r", encoding="utf-8") as f:
            Instructions_config = json.loads(f.read())
    else:
        Instructions_config = [
            ["Zcret Version_1.3\n", "Title"],
            ["历史版本文件可能不互通，使用前请确保已备份或转存.\n", "Emphasize"],
            ["需双击安装根目录字体文件Pixel_Font.ttf，否则可能存在界面异常.\n", "Emphasize"],

            ["Dir\n", "Title"],
            ["程序文件结构：\n", "Paragraph"],
            ["> [Temporary] 文件夹 - 临时文件夹，生成的新密钥会储存在此路径，但每次关闭程序都会清空它并无法找回.\n", "Paragraph"],
            ["> [Files] 文件夹 - 所有加密和解密文件的结果储存在此路径.\n", "Paragraph"],
            ["> [config.json] 加密配置 - 加密和解密时有任意值不同，即便密钥相同也无法解密.\n", "Paragraph"],
            ["> [public_keys.json] 公钥表 - 已添加的联系人，建议备份并定期检查是否被篡改和替换.\n", "Paragraph"],
            ["> [registration_config.json] 图标注册表配置 - 你可以定制化你的自定义文件图标，每次启动程序时自动绑定.\n", "Paragraph"],

            ["配置中任意值不相同的文件均无法解密.\n", "Emphasize"],
            ["若因私钥泄露导致需要重新生成密钥对，请确保本地旧加密文件同步更新或对旧私钥备份，否则可能导致文件无法修复.\n", "Emphasize"],

            ["PublicKey\n", "Title"],
            ["用于加密文件的公钥，希望谁能读取此数据就用谁的密钥加密，可公开，但请确保此密钥确实属于目标人员以防中间人攻击.\n", "Paragraph"],
            ["左侧空白区域左键绑定本地公钥，后续解密时的哈希校验依赖此项，若为空无法解密.\n", "Paragraph"],

            ["PrivateKey\n", "Title"],
            ["用于解密文件的私钥，不可公开，必须隐蔽保存并避免丢失和损坏，否则需要重新创建并将公钥重新给予他人.\n", "Paragraph"],

            ["FileEnc\n", "Title"],
            ["用于文件加密和解密，加密需要选择收件人公钥，选择被加密的文件，右键输入框可打开文件管理器选择，或直接输入文件路径.\n", "Paragraph"],
            ["解密需选择私钥，可以直接输入私钥字符，或加载私钥二进制文件或ImgEmb文件，程序会自动解析，注意配置文件相同.\n", "Paragraph"],
            ["加解密模式可通过“Mode”按钮切换.\n", "Paragraph"],

            ["FolderEnc\n", "Title"],
            ["用于文件夹的加密和解密，操作与FileEnc相似.\n", "Paragraph"],

            ["ImgEmb\n", "Title"],
            ["将数据嵌入图像，不影响图像读取使用，嵌入后的图像只可为PNG格式且源文件传输，通过其他软件另存可能破坏数据.\n", "Paragraph"],
            ["加解密模式可通过“Mode”按钮切换.\n", "Paragraph"],

            ["ExtName", "Title"],
            ["(str)\n", "Emphasize"],
            ["加密文件的后缀名，同时用于哈希校验.\n", "Paragraph"],

            ["HashTrunc", "Title"],
            ["(int)\n", "Emphasize"],
            ["哈希分隔符截断，加密产生的数据是多段字节包，以此为分隔符，越长越不容易出现解密错误，此值越大文件越大，最大64.\n", "Paragraph"],

            ["NsymSize", "Title"],
            ["(int)\n", "Emphasize"],
            ["纠错码容量，可以纠正每NsymSize/2数量的字节损坏，此值越大文件越大.\n", "Paragraph"],

            ["Compress", "Title"],
            ["(0/1)\n", "Emphasize"],
            ["是否对原始数据进行压缩，若加密时开启解密时也必须开启.\n", "Paragraph"]
        ]
        with open("instructions_config.json", mode="w", encoding="utf-8") as f:
            f.write(json.dumps(Instructions_config, indent=4, ensure_ascii=False))
    return Instructions_config
def get_registration_config():
    if os.path.isfile("registration_config.json"):
        with open("registration_config.json", mode="r", encoding="utf-8") as f:
            registration_config = json.loads(f.read())
    else:
        registration_config = {
            ".zorn": {
                "exe": f"{script_dir}\\Zcret.exe",
                "icon": f"{script_dir}\\icons\\zorn.ico"
            },
            ".zorns": {
                "exe": f"{script_dir}\\Zcret.exe",
                "icon": f"{script_dir}\\icons\\zorns.ico"
            },
            ".zornf": {
                "exe": f"{script_dir}\\Zcret.exe",
                "icon": f"{script_dir}\\icons\\zornf.ico"
            }
        }
        with open("registration_config.json", mode="w", encoding="utf-8") as f:
            f.write(json.dumps(registration_config, indent=4, ensure_ascii=False))
    return registration_config

registration_config = get_registration_config()
program_manager.add_associations(registration_config)
print(program_manager.query_associations(list(registration_config.keys())))

public_keys = get_public_keys()
encryption_config = get_config()
Instructions_config = get_Instructions_config()

class FlowNode:
    def __init__(self, main_frame, title, input_title, output_title, width):
        self.is_moving = False
        self.main_frame = main_frame
        self.canvas = main_frame.canvas
        self.frame = tk.Frame(self.canvas, bg=ui.col_dict["bg"])

        self.title_label = ui.Label(self.frame, text=f"{title}", font_size=8, width=width)
        self.title_label.bind("<B1-Motion>", self.move)  # 左键拖动
        self.title_label.bind("<ButtonPress-1>", self._click)  # 左键按下
        self.title_label.bind("<ButtonRelease-1>", self._release)  # 左键释放
        self.title_label.pack(expand=True, fill="x")

        tk.Frame(self.frame, bg=ui.col_dict["bg"], height=5).pack(expand=True, fill="x")

        in_out_frame = tk.Frame(self.frame, bg=ui.col_dict["main"])
        in_out_frame.pack(expand=True, fill="both")
        input_frame = tk.Frame(in_out_frame, bg=ui.col_dict["main"])
        input_frame.pack(side="left", expand=True, fill="both")
        output_frame = tk.Frame(in_out_frame, bg=ui.col_dict["main"])
        output_frame.pack(side="left", expand=True, fill="both")
        self.node_points = {}
        for input_t in input_title:
            data_node_frame = tk.Frame(input_frame, bg=ui.col_dict["main"])
            data_node_frame.pack(expand=True, fill="both")
            node_point_frame = tk.Frame(data_node_frame, bg=ui.col_dict["bg"])
            node_point_frame.pack(side="left")
            node_points = tk.Frame(node_point_frame, bg=ui.col_dict["light"], width=5, height=5)
            node_points.pack(padx=(0, 3), pady=3)
            self.node_points[input_t] = node_points
            ui.Label(data_node_frame, text=input_t, font_size=6, width=width//2, anchor="w", bg=ui.col_dict["main"]).pack(side="left", padx=(2, 0))
        for output_t in output_title:
            data_node_frame = tk.Frame(output_frame, bg=ui.col_dict["main"])
            data_node_frame.pack(expand=True, fill="both")
            node_point_frame = tk.Frame(data_node_frame, bg=ui.col_dict["bg"])
            node_point_frame.pack(side="right")
            node_points = tk.Frame(node_point_frame, bg=ui.col_dict["light"], width=5, height=5)
            node_points.pack(padx=(3, 0), pady=3)
            self.node_points[output_t] = node_points
            ui.Label(data_node_frame, text=output_t, font_size=6, width=width//2, anchor="e", bg=ui.col_dict["main"]).pack(side="right", padx=(0, 2))

    def _click(self, e):
        if self.is_moving:
            return
        self.click_x, self.click_y = e.x, e.y

    def _release(self, e):
        self.click_x, self.click_y = 0, 0

    def move(self, e):
        if self.is_moving:
            return
        self.is_moving = True
        locx, locy = ui.get_relative_pos(self.frame, self.canvas)
        x, y = e.x, e.y
        self.frame.place(x=locx + x - self.click_x, y=locy + y - self.click_y)
        self.is_moving = False

        self.main_frame.draw_line()

    def place(self, *args, **kwargs):
        self.frame.place(*args, **kwargs)

    def pack(self, *args, **kwargs):
        self.frame.place(*args, **kwargs)

class FlowScreen:
    def __init__(self, main_frame, node_config, size=(300, 300)):
        self.nodes_point = {}
        self.width, self.height = size
        self.frame = tk.Frame(main_frame, bg=ui.col_dict["main"])
        node_point_frame1 = tk.Frame(self.frame, bg=ui.col_dict["bg"])
        node_point_frame1.pack(side="left")
        input_point = tk.Frame(node_point_frame1, bg=ui.col_dict["light"], width=5, height=5)
        input_point.pack(padx=(3, 0), pady=3)
        self.canvas = tk.Canvas(self.frame, bg=ui.col_dict["bg"], highlightthickness=0, width=self.width, height=self.height)
        self.draw_grid()
        self.canvas.bind("<Enter>", self.draw_line)
        self.canvas.pack(side="left")
        node_point_frame0 = tk.Frame(self.frame, bg=ui.col_dict["bg"])
        node_point_frame0.pack(side="left")
        output_point = tk.Frame(node_point_frame0, bg=ui.col_dict["light"], width=5, height=5)
        output_point.pack(padx=(0, 3), pady=3)
        self.nodes_point["main"] = {"input": input_point, "output": output_point}

        self.edges = node_config["edges"]
        for node in node_config["nodes"]:
            title = node["title"]
            pos = node["pos"]
            input_title = node["input"]
            output_title = node["output"]
            width = node["width"]
            node_item = FlowNode(self, title, input_title, output_title, width)
            node_item.place(x=pos[0], y=pos[1])
            self.nodes_point[title] = node_item.node_points

    def draw_grid(self):
        for x in range(0, self.width, 20):
            self.canvas.create_line(x, 0, x, self.height, width=1, fill='black', tags="grid")
        for y in range(0, self.height, 20):
            self.canvas.create_line(0, y, self.width, y, width=1, fill='black', tags="grid")

    def draw_line(self, e=None):
        self.canvas.delete("all")
        self.draw_grid()
        for edge in self.edges:
            e0, e1 = edge
            point0 = get_nested_value(self.nodes_point, e0.split("."))
            x0, y0 = ui.get_relative_pos(point0, self.canvas)
            point1 = get_nested_value(self.nodes_point, e1.split("."))
            x1, y1 = ui.get_relative_pos(point1, self.canvas)
            self.canvas.create_line(
                x0+2, y0+2,  # 起点
                x0+2 + 20, y0+2,  # 控制点1
                x1+2 - 20, y1+2,  # 控制点3
                x1+2, y1+2,  # 终点
                smooth=True,  # 关键：自动平滑所有控制点
                width=4, fill=ui.col_dict["bg"]
            )
            self.canvas.create_line(
                x0 + 2, y0 + 2,  # 起点
                x0 + 2 + 20, y0 + 2,  # 控制点1
                x1 + 2 - 20, y1 + 2,  # 控制点3
                x1 + 2, y1 + 2,  # 终点
                smooth=True,  # 关键：自动平滑所有控制点
                width=2, fill=ui.col_dict["light"]
            )

    def place(self, *args, **kwargs):
        self.frame.place(*args, **kwargs)

    def pack(self, *args, **kwargs):
        self.frame.place(*args, **kwargs)

    def place_forget(self, *args, **kwargs):
        self.frame.place_forget(*args, **kwargs)

class AddRecipientWin:
    def __init__(self, root):
        def load_file(e):
            file_path = filedialog.askopenfilename(
                title="请选择文件",
                initialdir=script_dir,
            )
            if file_path:
                with open(file_path, mode="r", encoding="utf-8") as f:
                    content = f.read()
                self.PublicKey_t.delete(0.0, "end")
                self.PublicKey_t.insert(0.0, content)

                self.win.root.attributes('-topmost', True)

        self.root = root
        self.win = ui.Toplevel(
            title='Zcret.Recipient',
            w=273, h=390
        )

        self.sel_index = None
        main_frame = self.win.screen_frame
        self.key_tabel = ui.Table(main_frame, {"PubKey": 160, 'Name': 80}, height=4, font_size=8)
        self.key_tabel.bind("<ButtonRelease-1>", self.click_key_tabel)
        self.key_tabel.place(x=5, y=5)
        self.key_tabel.update(public_keys)
        ui.Label(main_frame, text="> Info", font_size=10).place(x=5, y=115)
        ui.Label(main_frame, text="Name:", font_size=8).place(x=5, y=135)
        self.name_e = ui.Entry(main_frame, font_size=9, stroke=False, width=10, fg=ui.col_dict["light"])
        self.name_e.place(x=50, y=135)
        ui.Label(main_frame, text="PublicKey:", font_size=8).place(x=5, y=155)
        self.PublicKey_t = ui.Text(main_frame, width=29, height=2, font_size=8, fg=ui.col_dict["light"])
        self.PublicKey_t.place(x=5, y=175)
        self.PublicKey_t.bind("<Button-3>", load_file)  # 右键点击
        ui.Label(main_frame, text="Note:", font_size=8).place(x=5, y=235)
        self.Instructions_t = ui.Text(main_frame, width=29, height=3, font_size=8, fg=ui.col_dict["light"])
        self.Instructions_t.place(x=5, y=255)

        self.add_b = ui.Button(main_frame, text="Add", font_size=8, stroke=True, command=self.add)
        self.add_b.place(x=167, y=115)
        self.save_b = ui.Button(main_frame, text="Save", font_size=8, stroke=True, command=self.save, width=7)
        self.del_b = ui.Button(main_frame, text="Del", fg="red", font_size=8, stroke=True, command=self.delete)
        self.del_b.place(x=207, y=115)

    def add(self):
        Name = self.name_e.get().strip()
        PublicKey = self.PublicKey_t.get(0.0, 'end').strip()
        if not PublicKey:
            ui.MessageBox("Error", "The public key cannot be empty.")
            self.PublicKey_t.main_frame.configure(bg=ui.col_dict["error"])
            return
        else:
            self.PublicKey_t.main_frame.configure(bg=ui.col_dict["bg"])
        Instructions = self.Instructions_t.get(0.0, 'end').strip()
        if not Instructions:
            ui.MessageBox("Error", "Incomplete description information.")
            self.Instructions_t.main_frame.configure(bg=ui.col_dict["error"])
            return
        else:
            self.Instructions_t.main_frame.configure(bg=ui.col_dict["bg"])
        public_keys.append([PublicKey, Name, Instructions])
        save_public_keys()
        self.key_tabel.update(public_keys)
        self.root.folder_key_tabel.update(public_keys)
        self.root.key_tabel.update(public_keys)

    def save(self):
        if self.sel_index is None:
            return

        Name = self.name_e.get().strip()
        PublicKey = self.PublicKey_t.get(0.0, 'end').strip()
        if not PublicKey:
            ui.MessageBox("Error", "The public key cannot be empty.")
            self.PublicKey_t.main_frame.configure(bg=ui.col_dict["error"])
            return
        else:
            self.PublicKey_t.main_frame.configure(bg=ui.col_dict["bg"])
        Instructions = self.Instructions_t.get(0.0, 'end').strip()
        if not Instructions:
            ui.MessageBox("Error", "Incomplete description information.")
            self.Instructions_t.main_frame.configure(bg=ui.col_dict["error"])
            return
        else:
            self.Instructions_t.main_frame.configure(bg=ui.col_dict["bg"])

        confirmation_box = ui.ConfirmationBox(title="Save", mode='reminder',  message="Are you sure you want to overwrite this recipient's information?")
        result = confirmation_box.get_result()
        if result:
            public_keys[self.sel_index] = [PublicKey, Name, Instructions]
            save_public_keys()
            self.key_tabel.update(public_keys)
            self.root.folder_key_tabel.update(public_keys)
            self.root.key_tabel.update(public_keys)

    def delete(self):
        if self.sel_index is None:
            return
        confirmation_box = ui.ConfirmationBox(title="Delete", mode='reminder', message="Are you sure you want to delete this recipient?")
        result = confirmation_box.get_result()
        if result:
            public_keys.pop(self.sel_index)
            save_public_keys()
            self.sel_index = None
            self.key_tabel.update(public_keys)
            self.root.key_tabel.update(public_keys)

    def click_key_tabel(self, e):
        self.PublicKey_t.main_frame.configure(bg=ui.col_dict["bg"])
        self.Instructions_t.main_frame.configure(bg=ui.col_dict["bg"])
        selected_item = self.key_tabel.table.selection()
        if not selected_item:
            return
        item_id = selected_item[0]
        row_index = self.key_tabel.table.index(item_id)
        self.sel_index = row_index
        values = self.key_tabel.table.item(item_id, "values")
        if any(values):
            self.name_e.delete(0, "end")
            self.name_e.insert(0, values[1])
            self.PublicKey_t.delete(0.0, "end")
            self.PublicKey_t.insert(0.0, values[0])
            self.Instructions_t.delete(0.0, "end")
            self.Instructions_t.insert(0.0, values[2])
            self.save_b.place(x=167, y=137)
        else:
            self.name_e.delete(0, "end")
            self.PublicKey_t.delete(0.0, "end")
            self.Instructions_t.delete(0.0, "end")
            self.save_b.place_forget()

class Win:
    def __init__(self):
        self.img_emb = None
        self.img_emb_bin = None
        self.emb_new_img = None
        self.emb_mode = 0
        self.pack_mode = 0
        self.endir_mode = 0
        self.endir_show_path = None
        self.DataContent_disemb = None
        self.sel_pubkey = None
        self.folder_sel_pubkey = None

        self.win = ui.Win(
            title='Zcret',
            # 顶端菜单
            menu_config={
                # "File": {"New Text": None},
                # "Open": {"Norm File": None, "Image Emb": None, "Enc File": None},
                "Enc": {"New Key": self._new_key},
            },
            page_config=['FileEnc', 'FolderEnc', 'ImgEmb', 'Setup'],
            w=520, h=410,
            icon="icon.ico"
        )
        self.win.bind_page_hook('Setup', self._Setup_update)
        self._FileEnc_page()
        self._FolderEnc_page()
        self._ImgEmb_page()
        self._Setup_page()

    def _Setup_update(self):
        if self.win.show_page == "Setup":
            encryption_config["ExtName"] = self.ExtName_e.get()
            encryption_config["HashTrunc"] = int(self.HashTrunc_e.get())
            encryption_config["NsymSize"] = int(self.NsymSize_e.get())
            encryption_config["Compress"] = int(self.Compress_e.get())
            if get_config() != encryption_config:
                self.Save_b.light_frame.configure(bg=ui.col_dict["light"])
            else:
                self.Save_b.light_frame.configure(bg=ui.col_dict["bg"])
        else:
            return

        self.win.root.after(500, self._Setup_update)

    def _new_key(self):
        try:
            i = 0
            os.makedirs("Temporary", exist_ok=True)
            ext = encryption_config["ExtName"]
            private_file_name = f"Temporary/private_{i}.bin.{ext}"
            public_file_name = f"Temporary/public_{i}.bin.{ext}"
            while os.path.isfile(private_file_name) and os.path.isfile(public_file_name):
                i += 1
                private_file_name = f"Temporary/private_{i}.bin.{ext}"
                public_file_name = f"Temporary/public_{i}.bin.{ext}"
            private_bytes, public_bytes = x25519_cipher.generate_random_key()
            with open(private_file_name, mode="wb") as f:
                f.write(private_bytes)
            with open(public_file_name, mode="wb") as f:
                f.write(public_bytes)
            ui.MessageBox("NewKey", f"The key has been successfully created: {os.path.join(script_dir, "Temporary")}", mode='pass')
        except Exception as e:
            ui.MessageBox("NewKey Error", f"{e}", mode='error')

    def _FileEnc_page(self):
        def mode_switch():
            if self.pack_mode:
                self.pack_mode = 0
                self.pack_flow_screen.place(x=5, y=5)
                self.unpack_flow_screen.place_forget()
                self.pack_Mode_switch_b.label.configure(text="> Mode Pack")
                pack_frame.place(x=5, y=232)
                unpack_frame.place_forget()
            else:
                self.pack_mode = 1
                self.unpack_flow_screen.place(x=5, y=5)
                self.pack_flow_screen.place_forget()
                self.pack_Mode_switch_b.label.configure(text="> Mode UnPack")
                pack_frame.place_forget()
                unpack_frame.place(x=5, y=232)
        def load_file(e):
            file_path = filedialog.askopenfilename(
                title="请选择文件",
                initialdir=script_dir,
            )
            if file_path:
                if self.pack_mode:
                    self.eFilePath_e.delete(0, "end")
                    self.eFilePath_e.insert(0, file_path)
                else:
                    self.FilePath_e.delete(0, "end")
                    self.FilePath_e.insert(0, file_path)
        def sel_key(e):
            selected_item = self.key_tabel.table.selection()
            if not selected_item:
                return
            item_id = selected_item[0]
            row_index = self.key_tabel.table.index(item_id)
            values = self.key_tabel.table.item(item_id, "values")
            self.sel_pubkey = values[0]
            self.Recipient_e.delete(0, "end")
            self.Recipient_e.insert(0, values[1])
        def save_as():
            try:
                ExtName = encryption_config["ExtName"]
                HashTrunc = encryption_config["HashTrunc"]
                Compress = encryption_config["Compress"]
                BlockSize = encryption_config["BlockSize"]
                if self.pack_mode:
                    PrivateKey = self.PrivateKey_e.get()
                    if os.path.isfile(PrivateKey):
                        if PrivateKey.split(".")[-1].lower() == 'png':
                            img = Image.open(PrivateKey)
                            PrivateKey_b = decode_with_ecc(bytes(lsb_extract(img)), nsym=encryption_config["NsymSize"])
                        else:
                            with open(PrivateKey, mode="rb") as f:
                                PrivateKey_b = f.read()
                    else:
                        PrivateKey_b = PrivateKey.encode()
                    PublicKey = encryption_config["PublicKey"]
                    with open(PublicKey, mode="rb") as f:
                        PublicKey_b = f.read()
                    file_path = self.eFilePath_e.get()
                    save_name = os.path.basename(".".join(file_path.split(".")[:-1]))
                    save_path = os.path.join("Files", save_name)
                    t = threading.Thread(
                        target=unpack_block,
                        args=(file_path, save_path, PrivateKey_b, PublicKey_b, Compress, ExtName.encode(), HashTrunc),
                        daemon=True
                    )
                    t.start()
                    self.win.light_breath_run()
                    while t.is_alive():
                        self.win.root.update()
                        time.sleep(0.1)
                    self.win.light_breath_init()
                    ui.MessageBox("Success", "File decryption successful.", mode="pass")
                else:
                    PublicKey = self.sel_pubkey
                    file_path = self.FilePath_e.get()
                    save_name = os.path.basename(file_path) + f".{ExtName}s"
                    save_path = os.path.join("Files", save_name)

                    t = threading.Thread(
                        target=pack_block,
                        args=(file_path, save_path, PublicKey.encode(), Compress, ExtName.encode(), HashTrunc, BlockSize),
                        daemon=True
                    )
                    t.start()
                    self.win.light_breath_run()
                    while t.is_alive():
                        self.win.root.update()
                        time.sleep(0.1)
                    self.win.light_breath_init()
                    ui.MessageBox("Success", "The encrypted file has been saved", mode="pass")
            except Exception as e:
                self.win.light_breath_init()
                ui.MessageBox("Error", f"Password Error or: {e}", mode="error")

        def load_key(e):
            file_path = filedialog.askopenfilename(
                title="请选择私钥文件",
                initialdir=script_dir,
            )
            if file_path:
                self.PrivateKey_e.delete(0, "end")
                self.PrivateKey_e.insert(0, file_path)
        def add_new_recipient():
            win = AddRecipientWin(self)

        page = self.win.screen_frames["FileEnc"]

        pack_flow_config = {
            "nodes": [
                {"title": "Time", "pos": [10, 10], "input": [], "output": ["fStr"], "width": 8},
                {"title": "HmacSha256", "pos": [160, 60], "input": ["Data", "PubKey"], "output": ["Out"], "width": 12},
                {"title": "X25519Cipher", "pos": [190, 128], "input": ["Data", "PubKey"], "output": ["Out"], "width": 14},
                {"title": "Splicing", "pos": [320, 10], "input": ["In0", "In1", "In2"], "output": ["Out"], "width": 8},
                {"title": "PublicKey", "pos": [10, 157], "input": [], "output": ["Byte"], "width": 12}
            ],
            "edges": [
                ["main.input", "X25519Cipher.Data"],
                ["Splicing.Out", "main.output"],
                ["Time.fStr", "HmacSha256.Data"],
                ["Time.fStr", "Splicing.In0"],
                ["HmacSha256.Out", "Splicing.In1"],
                ["X25519Cipher.Out", "Splicing.In2"],
                ["PublicKey.Byte", "HmacSha256.PubKey"],
                ["PublicKey.Byte", "X25519Cipher.PubKey"],
            ]
        }
        unpack_flow_config = {
            "nodes": [
                {"title": "HmacSha256", "pos": [160, 10], "input": ["Data", "PubKey"], "output": ["Out"], "width": 12},
                {"title": "X25519Cipher", "pos": [300, 140], "input": ["Data", "PriKey"], "output": ["Out"], "width": 14},
                {"title": "Split", "pos": [20, 57], "input": ["In"], "output": ["Out0", "Out1", "Out2"], "width": 8},
                {"title": "PublicKey", "pos": [10, 10], "input": [], "output": ["Byte"], "width": 12},
                {"title": "PrivateKey", "pos": [10, 157], "input": [], "output": ["Byte"], "width": 12},
                {"title": "Judge", "pos": [160, 80], "input": ["In0", "In1", "Data"], "output": ["True"], "width": 12}
            ],
            "edges": [
                ["main.input", "Split.In"],
                ["Split.Out0", "HmacSha256.Data"],
                ["PublicKey.Byte", "HmacSha256.PubKey"],
                ["PrivateKey.Byte", "X25519Cipher.PriKey"],
                ["HmacSha256.Out", "Judge.In0"],
                ["Split.Out1", "Judge.In1"],
                ["Split.Out2", "Judge.Data"],
                ["Judge.True", "X25519Cipher.Data"],
                ["X25519Cipher.Out", "main.output"],
            ]
        }
        self.pack_flow_screen = FlowScreen(page,
            pack_flow_config, size=(470, 200)
        )
        self.unpack_flow_screen = FlowScreen(page,
            unpack_flow_config, size=(470, 200)
        )
        self.pack_flow_screen.place(x=5, y=5)

        self.pack_Mode_switch_b = ui.Button(page, text="> Mode Pack", stroke=False, font_size=8, width=12, command=mode_switch, anchor="e")
        self.pack_Mode_switch_b.place(x=380, y=210)

        Control_title = ui.Label(page, text="> Control Panel", font_size=10)
        Control_title.place(x=5, y=210)

        pack_frame = tk.Frame(page, width=600, height=400, bg=ui.col_dict["main"])
        pack_frame.place(x=5, y=232)

        ui.Label(pack_frame, text="Recipient:", font_size=8).place(x=265, y=18)
        self.Recipient_e = ui.Entry(pack_frame, font_size=10, stroke=False, width=14, fg=ui.col_dict["light"])
        self.Recipient_e.place(x=345, y=18)
        ui.Label(pack_frame, text="FilePath:", font_size=8).place(x=265, y=38)
        self.FilePath_e = ui.Entry(pack_frame, font_size=10, stroke=False, width=15, fg=ui.col_dict["light"])
        self.FilePath_e.bind("<Button-3>", load_file)
        self.FilePath_e.place(x=335, y=38)

        unpack_frame = tk.Frame(page, width=600, height=400, bg=ui.col_dict["main"])
        ui.Label(unpack_frame, text="PrivateKey:", font_size=8).place(x=265, y=18)
        self.PrivateKey_e = ui.Entry(unpack_frame, font_size=10, stroke=False, width=13, fg=ui.col_dict["light"], show="*")
        self.PrivateKey_e.bind("<Button-3>", load_key)  # 右键点击
        self.PrivateKey_e.place(x=355, y=18)
        ui.Label(unpack_frame, text="FilePath:", font_size=8).place(x=265, y=38)
        self.eFilePath_e = ui.Entry(unpack_frame, font_size=10, stroke=False, width=15, fg=ui.col_dict["light"])
        self.eFilePath_e.bind("<Button-3>", load_file)  # 右键点击
        self.eFilePath_e.place(x=335, y=38)

        self.Save_as_b = ui.Button(page, text=" Save ", stroke=True, font_size=8, width=23, command=save_as)
        self.Save_as_b.place(x=272, y=290)

        self.key_tabel = ui.Table(page, {"PubKey": 160, 'Name': 100}, height=3, font_size=8)
        self.key_tabel.bind("<ButtonRelease-1>", sel_key)
        self.key_tabel.place(x=5, y=232)
        self.key_tabel.update(public_keys)
        self.key_add_b = ui.Button(self.key_tabel.table, text="+", stroke=False, font_size=8, command=add_new_recipient)
        self.key_add_b.place(x=240, y=5)

    def _FolderEnc_page(self):
        def sel_key(e):
            if not self.endir_mode:
                selected_item = self.folder_key_tabel.table.selection()
                if not selected_item:
                    return
                item_id = selected_item[0]
                row_index = self.folder_key_tabel.table.index(item_id)
                values = self.folder_key_tabel.table.item(item_id, "values")
                self.folder_sel_pubkey = values[0]
                self.folder_Recipient_e.delete(0, "end")
                self.folder_Recipient_e.insert(0, values[1])
        def load_folder(e):
            if self.endir_mode:
                file_path = filedialog.askopenfilename(
                    title="请选择文件",
                    initialdir=script_dir,
                )
                if file_path:
                    try:
                        self.DirPath_e.delete(0, "end")
                        self.DirPath_e.insert(0, file_path)
                    except Exception as e:
                        ui.MessageBox("Error", f"{e}", "error")
            else:
                folder_path = filedialog.askdirectory(
                    title="请选择目标文件夹",
                    initialdir=script_dir
                )
                if folder_path:
                    try:
                        self.endir_show_path = folder_path
                        self.DirPath_e.delete(0, "end")
                        self.DirPath_e.insert(0, folder_path)
                        self.dir_path_e.delete(0, "end")
                        self.dir_path_e.insert(0, os.path.basename(folder_path))

                        items = dm.get_dir_items(folder_path)
                        table_data = []
                        for i in items["folder"]:
                            basename = os.path.basename(i)
                            table_data.append((basename, "Folder"))
                        for i in items["file"]:
                            basename = os.path.basename(i)
                            table_data.append((basename, f'.{basename.split(".")[-1]}'))
                        self.file_tabel.update(table_data)
                    except Exception as e:
                        ui.MessageBox("Error", f"{e}", "error")
        def save_as():
            ExtName = encryption_config["ExtName"]
            HashTrunc = encryption_config["HashTrunc"]
            Compress = encryption_config["Compress"]
            BlockSize = encryption_config["BlockSize"]
            try:
                if self.endir_mode:
                    PrivateKey = self.folder_Recipient_e.get()
                    if os.path.isfile(PrivateKey):
                        if PrivateKey.split(".")[-1].lower() == 'png':
                            img = Image.open(PrivateKey)
                            PrivateKey_b = decode_with_ecc(bytes(lsb_extract(img)), nsym=encryption_config["NsymSize"])
                        else:
                            with open(PrivateKey, mode="rb") as f:
                                PrivateKey_b = f.read()
                    else:
                        PrivateKey_b = PrivateKey.encode()
                    PublicKey = encryption_config["PublicKey"]
                    with open(PublicKey, mode="rb") as f:
                        PublicKey_b = f.read()
                    target_dir = self.DirPath_e.get()
                    basename = os.path.basename(target_dir).split(".")[0]

                    self.endir_show_path = f"Files/{basename}"

                    def _folder_unpack_block(target_dir, endir_show_path, PrivateKey_b, PublicKey_b, Compress,
                                           system_name, hash_truncate, block_size):
                        for i in folder_unpack_block(target_dir, endir_show_path, PrivateKey_b, PublicKey_b,
                                                     compress=Compress,
                                                     system_name=system_name, hash_truncate=hash_truncate,
                                                     block_size=block_size):
                            self.progress_bar.update(int(100 * i) - 1, 100)

                    t = threading.Thread(
                        target=_folder_unpack_block,
                        args=(target_dir, self.endir_show_path, PrivateKey_b, PublicKey_b, Compress,
                                           ExtName.encode(), HashTrunc, BlockSize),
                        daemon=True
                    )
                    t.start()
                    self.win.light_breath_run()
                    while t.is_alive():
                        self.win.root.update()
                        time.sleep(0.01)
                    self.win.light_breath_init()

                    # for i in folder_unpack_block(target_dir, self.endir_show_path, PrivateKey_b, PublicKey_b, compress=Compress,
                    #                        system_name=ExtName.encode(), hash_truncate=HashTrunc, block_size=BlockSize):
                    #     self.progress_bar.update(int(100*i)-1, 100)

                    self.dir_path_e.delete(0, "end")
                    self.dir_path_e.insert(0, basename)
                    items = dm.get_dir_items(self.endir_show_path)
                    table_data = []
                    for i in items["folder"]:
                        basename = os.path.basename(i)
                        table_data.append((basename, "Folder"))
                    for i in items["file"]:
                        basename = os.path.basename(i)
                        table_data.append((basename, f'.{basename.split(".")[-1]}'))
                    self.file_tabel.update(table_data)
                    ui.MessageBox("Success", "Folder decryption successful.", mode="pass")
                else:
                    target_dir = self.DirPath_e.get()
                    basename = os.path.basename(target_dir)

                    def _folder_pack_block(target_dir, save_path, folder_sel_pubkey, compress, system_name,
                                           hash_truncate, block_size):
                        for i in folder_pack_block(target_dir, save_path,
                                                   folder_sel_pubkey, compress=compress,
                                                   system_name=system_name, hash_truncate=hash_truncate,
                                                   block_size=block_size):
                            self.progress_bar.update(int(100 * i) - 1, 100)

                    t = threading.Thread(
                        target=_folder_pack_block,
                        args=(target_dir, f"Files/{basename}.zornf", self.folder_sel_pubkey.encode(), Compress,
                                         ExtName.encode(), HashTrunc, BlockSize),
                        daemon=True
                    )
                    t.start()
                    self.win.light_breath_run()
                    while t.is_alive():
                        self.win.root.update()
                        time.sleep(0.01)
                    self.win.light_breath_init()

                    # for i in folder_pack_block(target_dir, f"Files/{basename}.zornf", self.folder_sel_pubkey.encode(), compress=Compress,
                    #                      system_name=ExtName.encode(), hash_truncate=HashTrunc, block_size=BlockSize):
                    #     self.progress_bar.update(int(100*i)-1, 100)
                    ui.MessageBox("Success", "The encrypted folder has been saved.", mode="pass")
            except Exception as e:
                ui.MessageBox("Error", f"{e}", mode="error")
        def mode_switch():
            self.DirPath_e.delete(0, "end")
            self.folder_Recipient_e.delete(0, "end")
            if self.endir_mode:
                self.endir_mode = 0
                self.DirPath_Mode_switch_b.label.configure(text="> Mode Enc")
                DirPath_title.configure(text="DirPath:")
                Recipient_title.configure(text="Recipient:")
                self.folder_Recipient_e.configure(show=None)
            else:
                self.endir_mode = 1
                self.DirPath_Mode_switch_b.label.configure(text="> Mode Den")
                DirPath_title.configure(text="FilePath:")
                Recipient_title.configure(text="PrivateK:")
                self.folder_Recipient_e.configure(show="*")
        def sel_item(e):
            selected_item = self.file_tabel.table.selection()
            if not selected_item:
                return
            item_id = selected_item[0]
            row_index = self.file_tabel.table.index(item_id)
            values = self.file_tabel.table.item(item_id, "values")
            item_name, item_type = values

            if item_type != "Folder":
                pil_open_suffixes = {".png", ".jpg"}
                item_path = os.path.join(self.endir_show_path, item_name)
                if item_type in pil_open_suffixes:
                    self.data_img_l.place(x=0, y=0)
                    self.data_img_l.update(item_path)
                else:
                    try:
                        self.data_img_l.place_forget()
                        self.data_t.delete(0.0, 'end')
                        with open(item_path, mode="r", encoding="utf-8") as f:
                            self.data_t.insert(0.0, f.read(1000) + "\n\n……")
                    except: pass
            else:
                self.data_t.delete(0.0, 'end')
                self.data_img_l.place_forget()
        def in_folder(e):
            selected_item = self.file_tabel.table.selection()
            if not selected_item:
                return
            item_id = selected_item[0]
            row_index = self.file_tabel.table.index(item_id)
            values = self.file_tabel.table.item(item_id, "values")
            item_name, item_type = values
            if item_type == "Folder":
                self.endir_show_path = os.path.join(self.endir_show_path, item_name)
                show_path = self.dir_path_e.get()
                self.dir_path_e.delete(0, "end")
                self.dir_path_e.insert(0, os.path.join(show_path, item_name))

                items = dm.get_dir_items(self.endir_show_path)
                table_data = []
                for i in items["folder"]:
                    basename = os.path.basename(i)
                    table_data.append((basename, "Folder"))
                for i in items["file"]:
                    basename = os.path.basename(i)
                    table_data.append((basename, f'.{basename.split(".")[-1]}'))
                self.file_tabel.update(table_data)
        def back_path():
            show_path = self.dir_path_e.get()
            if show_path.strip() == os.path.basename(self.DirPath_e.get()).strip():
                return
            self.dir_path_e.delete(0, "end")
            self.dir_path_e.insert(0, os.path.dirname(show_path))
            self.endir_show_path = os.path.dirname(self.endir_show_path)
            items = dm.get_dir_items(self.endir_show_path)
            table_data = []
            for i in items["folder"]:
                basename = os.path.basename(i)
                table_data.append((basename, "Folder"))
            for i in items["file"]:
                basename = os.path.basename(i)
                table_data.append((basename, f'.{basename.split(".")[-1]}'))
            self.file_tabel.update(table_data)
        def add_new_recipient():
            win = AddRecipientWin(self)
        def load_key(e):
            if self.endir_mode:
                file_path = filedialog.askopenfilename(
                    title="请选择私钥文件",
                    initialdir=script_dir,
                )
                if file_path:
                    self.folder_Recipient_e.delete(0, "end")
                    self.folder_Recipient_e.insert(0, file_path)

        page = self.win.screen_frames["FolderEnc"]
        self.back_b = ui.Button(page, text="Back", font_size=6, stroke=True, command=back_path)
        self.back_b.place(x=5, y=5)
        self.dir_path_e = ui.Entry(page, font_size=8, stroke=True, width=28, padx=(3, 5), pady=5, fg=ui.col_dict["light"])
        self.dir_path_e.place(x=43, y=5)
        self.file_tabel = ui.Table(page, {"Name": 210, 'Type': 60}, height=7, font_size=7)
        self.file_tabel.bind("<ButtonRelease-1>", sel_item)
        self.file_tabel.bind("<Double-Button-1>", in_folder)  # 左键双击
        self.file_tabel.place(x=5, y=28)
        self.progress_bar = ui.ProgressBar(page, title='', length=205)
        self.progress_bar.place(x=5, y=195)
        self.folder_key_tabel = ui.Table(page, {"PubKey": 170, 'Name': 100}, height=3, font_size=8)
        self.folder_key_tabel.bind("<ButtonRelease-1>", sel_key)
        self.folder_key_tabel.place(x=5, y=232)
        self.folder_key_tabel.update(public_keys)
        self.folder_key_add_b = ui.Button(self.folder_key_tabel.table, text="+", stroke=False, font_size=8, command=add_new_recipient)
        self.folder_key_add_b.place(x=250, y=5)

        tk.Frame(page, width=5, height=220, bg=ui.col_dict["bg"]).place(x=282, y=0)
        Control_title = ui.Label(page, text="> Data", font_size=10)
        Control_title.place(x=293, y=5)
        self.DirPath_Mode_switch_b = ui.Button(page, text="> Mode Enc", stroke=False, font_size=8, width=11, command=mode_switch, anchor="e")
        self.DirPath_Mode_switch_b.place(x=390, y=5)
        self.data_t = ui.Text(page, width=38, height=14, font_size=5, spacing2=3, spacing3=4)
        self.data_t.place(x=293, y=25)
        self.data_img_l = ui.ImgLabel(self.data_t.text, size=(190, 185))

        tk.Frame(page, width=500, height=5, bg=ui.col_dict["bg"]).place(x=0, y=220)
        Recipient_title = ui.Label(page, text="Recipient:", font_size=8)
        Recipient_title.place(x=283, y=245)
        self.folder_Recipient_e = ui.Entry(page, font_size=10, stroke=False, width=13, fg=ui.col_dict["light"])
        self.folder_Recipient_e.place(x=361, y=245)
        self.folder_Recipient_e.bind("<ButtonRelease-3>", load_key)
        DirPath_title = ui.Label(page, text="DirPath:", font_size=8)
        DirPath_title.place(x=283, y=265)
        self.DirPath_e = ui.Entry(page, font_size=10, stroke=False, width=14, fg=ui.col_dict["light"])
        self.DirPath_e.bind("<ButtonRelease-3>", load_folder)
        self.DirPath_e.place(x=351, y=267)
        self.save_folder_b = ui.Button(page, text=" Save as ", stroke=True, font_size=8, width=21, command=save_as)
        self.save_folder_b.place(x=285, y=290)

    def _ImgEmb_page(self):
        def load_img(e):
            file_path = filedialog.askopenfilename(
                title="请选择文件",
                initialdir=script_dir,
            )
            if file_path:
                try:
                    img = Image.open(file_path)
                    if self.emb_mode:
                        result_data = decode_with_ecc(bytes(lsb_extract(img)), nsym=encryption_config["NsymSize"])
                        self.DataContent_t.delete(0.0, 'end')
                        self.DataContent_t.insert(0.0, f"{result_data[:256]}\n\n{f'{len(result_data)}byte …'if len(result_data)>256 else ''}")
                        self.DataContent_disemb = result_data
                    else:
                        self.img_emb = img
                        self.img_label.update(img)
                        if self.img_emb_bin:
                            self.emb_new_img = lsb_embed(self.img_emb, self.img_emb_bin)
                            img_size = get_img_size(self.img_emb)
                            result_size = get_img_size(self.emb_new_img)
                            proportion_img = get_proportion_img(
                                {"Data": result_size - img_size, "Image": img_size},
                                256,
                                ui.col_dict["main"],
                                ui.col_dict["bg"],
                                ui.col_dict["light"]
                            )
                            self.proportion_img_label.update(proportion_img)
                except Exception as e:
                    ui.MessageBox("Error", f"{e}", "error")
        def load_bin(e):
            file_path = filedialog.askopenfilename(
                title="请选择文件",
                initialdir=script_dir,
            )
            if file_path:
                try:
                    self.BinPath_e.delete(0, "end")
                    self.BinPath_e.insert(0, file_path)
                    with open(file_path, mode="rb") as f:
                        self.img_emb_bin = encode_with_ecc(f.read(), nsym=encryption_config["NsymSize"])
                    self.emb_new_img = lsb_embed(self.img_emb, self.img_emb_bin)
                    img_size = get_img_size(self.img_emb)
                    result_size = get_img_size(self.emb_new_img)
                    proportion_img = get_proportion_img(
                        {"Data": result_size - img_size, "Image": img_size},
                        256,
                        ui.col_dict["main"],
                        ui.col_dict["bg"],
                        ui.col_dict["light"]
                    )
                    self.proportion_img_label.update(proportion_img)
                except Exception as e:
                    ui.MessageBox("Error", f"{e}", "error")
        def save_as():
            if self.emb_mode:
                save_path = filedialog.asksaveasfilename(
                    title="选择保存位置并输入文件名",
                    initialdir=script_dir,  # 默认打开的文件夹
                    defaultextension=".bin",  # 默认后缀（用户不输入则自动添加）
                )
                if save_path:
                    with open(save_path, mode="wb") as f:
                        f.write(self.DataContent_disemb)
            else:
                save_path = filedialog.asksaveasfilename(
                    title="选择保存位置并输入文件名",
                    initialdir=script_dir,  # 默认打开的文件夹
                    defaultextension=".png",  # 默认后缀（用户不输入则自动添加）
                )
                if save_path:
                    self.emb_new_img.save(save_path)
        def mode_switch():
            if self.emb_mode:
                self.emb_mode = 0
                self.Image_Mode_switch_b.label.configure(text="> Mode Emb")
                Proportion_title.configure(text="> Proportion")
                block_frame.place(x=290, y=230)
                Control_title.place(x=300, y=240)
                BinPath_title.place(x=300, y=265)
                self.BinPath_e.place(x=368, y=267)
                self.DataContent_t.place_forget()
                self.proportion_img_label.resize((194, 194))
            else:
                self.emb_mode = 1
                self.Image_Mode_switch_b.label.configure(text="> Mode DisEmb")
                Proportion_title.configure(text="> DataContent")
                block_frame.place_forget()
                Control_title.place_forget()
                BinPath_title.place_forget()
                self.BinPath_e.place_forget()
                self.DataContent_t.place(x=0, y=0)
                self.proportion_img_label.resize((194, 254))

        page = self.win.screen_frames["ImgEmb"]

        ui.Label(page, text="> Image", font_size=10).place(x=5, y=5)
        self.img_label = ui.ImgLabel(page, img=None, size=(280, 287))
        self.img_label.place(x=5, y=30)
        self.img_label.bind("<Button-1>", load_img)  # 左键点击
        self.Image_Mode_switch_b = ui.Button(page, text="> Mode Emb", stroke=False, font_size=8, width=12, command=mode_switch, anchor="e")
        self.Image_Mode_switch_b.place(x=170, y=5)

        tk.Frame(page, width=5, height=360, bg=ui.col_dict["bg"]).place(x=290, y=0)
        Proportion_title = ui.Label(page, text="> Proportion", font_size=10)
        Proportion_title.place(x=300, y=5)
        self.proportion_img_label = ui.ImgLabel(page, img=None, size=(194, 194))
        self.proportion_img_label.place(x=300, y=30)

        block_frame = tk.Frame(page, width=300, height=5, bg=ui.col_dict["bg"])
        block_frame.place(x=290, y=230)
        Control_title = ui.Label(page, text="> Control Panel", font_size=10)
        Control_title.place(x=300, y=240)
        BinPath_title = ui.Label(page, text="BinPath:", font_size=8)
        BinPath_title.place(x=300, y=265)
        self.BinPath_e = ui.Entry(page, font_size=10, stroke=False, width=12, fg=ui.col_dict["light"])
        self.BinPath_e.bind("<Button-3>", load_bin)
        self.BinPath_e.place(x=368, y=267)
        self.Image_Emb_b = ui.Button(page, text=" Save as ", stroke=True, font_size=8, width=19, command=save_as)
        self.Image_Emb_b.place(x=305, y=290)
        self.DataContent_t = ui.Text(self.proportion_img_label.frame, width=18, height=10)

    def _Setup_page(self):
        def new_public_key(e):
            file_path = filedialog.askopenfilename(
                title="请选择文件",
                initialdir=script_dir,
            )
            if file_path:
                encryption_config["PublicKey"] = file_path
                with open(file_path, mode='rb') as f:
                    PublicKey = f.read()
                print(PublicKey)
                PublicKey_qr_img = generate_qr(PublicKey, fill_color=ui.col_dict['text'],  back_color=ui.col_dict['bg'])
                self.PublicKey_img_label.update(PublicKey_qr_img)

        page = self.win.screen_frames["Setup"]

        ui.Label(page, text="> Config", font_size=10).place(x=5, y=5)
        ui.Label(page, text="  ExtName:", font_size=8).place(x=5, y=30)
        ui.Label(page, text="  HashTrunc:", font_size=8).place(x=5, y=50)
        ui.Label(page, text="  NsymSize:", font_size=8).place(x=5, y=70)
        ui.Label(page, text="  Compress:", font_size=8).place(x=5, y=90)
        self.ExtName_e = ui.Entry(page, font_size=10, stroke=False, width=10, fg=ui.col_dict["light"])
        self.ExtName_e.place(x=85, y=30)
        self.ExtName_e.insert(0, encryption_config["ExtName"])
        self.HashTrunc_e = ui.Entry(page, font_size=10, stroke=False, width=8, fg=ui.col_dict["light"])
        self.HashTrunc_e.place(x=105, y=50)
        self.HashTrunc_e.insert(0, encryption_config["HashTrunc"])
        self.NsymSize_e = ui.Entry(page, font_size=10, stroke=False, width=9, fg=ui.col_dict["light"])
        self.NsymSize_e.place(x=95, y=70)
        self.NsymSize_e.insert(0, encryption_config["NsymSize"])
        self.Compress_e = ui.Entry(page, font_size=10, stroke=False, width=9, fg=ui.col_dict["light"])
        self.Compress_e.place(x=95, y=90)
        self.Compress_e.insert(0, encryption_config["Compress"])

        self.Save_b = ui.Button(page, text="Save", stroke=True, font_size=6, width=22, command=save_config)
        self.Save_b.place(x=15, y=110)

        tk.Frame(page, width=5, height=360, bg=ui.col_dict["bg"]).place(x=192, y=0)

        ui.Label(page, text="> Instructions", font_size=10).place(x=202, y=5)
        self.Instructions_t = ui.Text(page, width=28, height=11,
              tag_config=[
                  {"tagName": "Title", "font": ("Fusion Pixel 12px Mono zh_hans", 12, "bold"), "foreground": ui.col_dict['text']},
                  {"tagName": "Paragraph", "font": ("Fusion Pixel 12px Mono zh_hans", 8), "foreground": ui.col_dict['text']},
                  {"tagName": "Emphasize", "font": ("Fusion Pixel 12px Mono zh_hans", 8), "foreground": ui.col_dict['light']}
              ]
          )
        self.Instructions_t.place(x=202, y=30)
        for content in Instructions_config:
            self.Instructions_t.insert("end", *content)

        PublicKey_path = encryption_config["PublicKey"]
        if PublicKey_path and os.path.isfile(PublicKey_path):
            with open(PublicKey_path, mode='rb') as f:
                PublicKey = f.read()
            PublicKey_qr_img = generate_qr(PublicKey, fill_color=ui.col_dict['text'], back_color=ui.col_dict['bg'])
        else:
            PublicKey_qr_img = None
        self.PublicKey_img_label = ui.ImgLabel(page, img=PublicKey_qr_img, size=(182, 178))
        self.PublicKey_img_label.place(x=5, y=140)
        self.PublicKey_img_label.bind("<Button-1>", new_public_key)  # 左键点击

    def mainloop(self):
        self.win.mainloop()

if __name__ == '__main__':
    win = Win()

    win.mainloop()

    clean_folder("Temporary")