from ModuleTool.EncryptionByte import X25519Cipher, AesGcmCipher, XorCipher
from ModuleTool.CompressZip import Bz2Compressor
from ModuleTool.HashCalcu import HmacSha256Hash
import time
import itertools
from PIL import Image
import numpy as np
from reedsolo import RSCodec
import ModuleTool.DeviceInfo as di
import os
import copy
import json
import struct

# dm = None
dm = di.DiskManager()
xor = XorCipher()
x25519_cipher = X25519Cipher()
bz2_compressor = Bz2Compressor()
hmac_sha256 = HmacSha256Hash()
AES_GCM = AesGcmCipher()
HEADER_LENGTH = 8
HEADER_FORMAT = '>Q'
def pack(original_data, public_bytes, compress=False, system_name=b"Zorn", hash_truncate=16):
    if compress:
        original_data = bz2_compressor.compress(original_data, 9)
    now_str = time.strftime("%Y-%m-%d_%H-%M-%S ", time.localtime())
    time_b = now_str.encode()
    split_byte = time_b.split(b"_")[0]
    time_b_hash = hmac_sha256.compute(system_name + time_b, public_bytes).encode()
    split_b_hash = hmac_sha256.compute(system_name + split_byte, public_bytes).encode()[:hash_truncate]
    # print(time_b)
    # print(split_byte)
    # print(time_b_hash)
    # print(public_bytes)
    key = AES_GCM.generate_random_key()
    encrypt_result = AES_GCM.encrypt(original_data, key)
    encrypt_key = x25519_cipher.encrypt(key, public_bytes, split_byte=split_b_hash)
    result = time_b + time_b_hash + encrypt_key + encrypt_result

    return xor.encrypt(result, system_name)

def unpack(encrypt_package, private_bytes, public_bytes, decompress=False, system_name=b"Zorn", hash_truncate=16):
    encrypt_package = xor.decrypt(encrypt_package, system_name)
    time_b = encrypt_package[:20]
    split_byte = time_b.split(b"_")[0]
    target_hash = encrypt_package[20:84]
    encrypt_key = encrypt_package[84:252]
    data = encrypt_package[252:]

    time_b_hash = hmac_sha256.compute(system_name + time_b, public_bytes).encode()
    # print(time_b)
    # print(split_byte)
    # print(target_hash)
    # print(time_b_hash)
    # print(private_bytes)
    # print(public_bytes)
    split_b_hash = hmac_sha256.compute(system_name + split_byte, public_bytes).encode()[:hash_truncate]
    test = target_hash == time_b_hash
    if test:
        key = x25519_cipher.decrypt(encrypt_key, private_bytes, split_byte=split_b_hash)
        encrypt_result = AES_GCM.decrypt(data, key)
        if decompress:
            encrypt_result = bz2_compressor.decompress(encrypt_result)
    else:
        encrypt_result = None
    return encrypt_result

def mix_bytes_groups(groups: list[bytes]) -> bytes:
    """
    将多组字节混淆交织，返回混淆后的字节
    :param groups: 多组原始字节列表 [b'xxx', b'yyy', ...]
    :return: 混淆后的bytes，头部存储各组长度信息
    """
    # 1. 记录每组长度，用于还原
    lengths = [len(g) for g in groups]
    # 将长度序列编码成4字节无符号整数，大端存储
    header = b"".join(l.to_bytes(4, byteorder="big") for l in lengths)
    num_groups = len(groups)
    # 2. 字节交织：按轮次依次取每个组的1个字节，组耗尽就跳过
    iters = [iter(g) for g in groups]
    mixed_body = bytearray()
    for item in itertools.zip_longest(*iters, fillvalue=None):
        for b in item:
            if b is not None:
                mixed_body.append(b)
    # 头部(组数+长度列表) + 混淆体
    full_data = len(lengths).to_bytes(2, byteorder="big") + header + bytes(mixed_body)
    return full_data

def unmix_bytes_groups(data: bytes) -> list[bytes]:
    """
    逆运算，还原出原始多组字节
    :param data: mix_bytes_groups输出的混淆字节
    :return: 原始字节列表
    """
    ptr = 0
    # 读取组数量
    num_groups = int.from_bytes(data[ptr:ptr+2], byteorder="big")
    ptr +=2
    # 读取每组长度，每个占4字节
    lengths = []
    for _ in range(num_groups):
        l = int.from_bytes(data[ptr:ptr+4], byteorder="big")
        lengths.append(l)
        ptr +=4
    body = bytearray(data[ptr:])

    # 初始化输出缓冲区
    buffers = [bytearray() for _ in range(num_groups)]
    remain = lengths.copy()
    idx = 0
    for byte_val in body:
        # 循环轮询各个组，还需要字节就分配给该组
        while True:
            g = idx % num_groups
            idx += 1
            if remain[g] > 0:
                buffers[g].append(byte_val)
                remain[g] -=1
                break
    return [bytes(buf) for buf in buffers]

def pack_(original_data_list, public_bytes_list, compress=False, system_name=b"Zorn", hash_truncate=16):
    if len(original_data_list) != len(public_bytes_list):
        raise (ValueError, "数据数量需与公钥数量一致")
    encrypt_results = []
    now_str = time.strftime("%Y-%m-%d_%H-%M-%S ", time.localtime())
    time_b = now_str.encode()
    split_byte = time_b.split(b"_")[0]
    for i in range(len(original_data_list)):
        original_data = original_data_list[i]
        if compress:
            original_data = bz2_compressor.compress(original_data, 9)
        public_bytes = public_bytes_list[i]
        time_b_hash = hmac_sha256.compute(system_name + time_b, public_bytes).encode()
        split_b_hash = hmac_sha256.compute(system_name + split_byte, public_bytes).encode()[:hash_truncate]
        encrypt_result = x25519_cipher.encrypt(original_data, public_bytes, split_byte=split_b_hash)
        encrypt_results.append(time_b_hash + encrypt_result)
    result = mix_bytes_groups(encrypt_results)
    return time_b + result

def unpack_(encrypt_package, private_bytes, public_bytes, decompress=False, system_name=b"Zorn", hash_truncate=16):
    time_b = encrypt_package[:20]
    split_byte = time_b.split(b"_")[0]
    encrypt_package_data = encrypt_package[20:]
    encrypt_package_list = unmix_bytes_groups(encrypt_package_data)
    encrypt_results = []
    for encrypt_package_ in encrypt_package_list:
        target_hash = encrypt_package_[:64]
        data = encrypt_package_[64:]
        time_b_hash = hmac_sha256.compute(system_name + time_b, public_bytes).encode()
        split_b_hash = hmac_sha256.compute(system_name + split_byte, public_bytes).encode()[:hash_truncate]
        test = target_hash == time_b_hash
        if test:
            encrypt_result = x25519_cipher.decrypt(data, private_bytes, split_byte=split_b_hash)
            if decompress:
                encrypt_result = bz2_compressor.decompress(encrypt_result)
            encrypt_results.append(encrypt_result)

    return encrypt_results

def lsb_embed(img: Image.Image, secret_data: bytes) -> Image.Image:
    """
    LSB隐写，嵌入任意bytes数据
    :param img: 输入PIL图像(RGB/RGBA)
    :param secret_data: 需要隐藏的字节串
    :return: 载密图像
    """
    arr = np.array(img)
    flat = arr.reshape(-1)
    max_bits = flat.shape[0]
    secret_bits = []
    # 先写入4字节长度头，再写入真实数据
    length = len(secret_data)
    payload = length.to_bytes(4, byteorder="little") + secret_data
    for b in payload:
        for i in range(8):
            secret_bits.append((b >> i) & 1)
    if len(secret_bits) > max_bits:
        raise OverflowError("图片容量不足，无法嵌入该数据")
    # 写入每一位到通道最低位
    for idx, bit in enumerate(secret_bits):
        flat[idx] = (flat[idx] & 0xFE) | bit
    return Image.fromarray(flat.reshape(arr.shape))

def lsb_extract(img: Image.Image) -> bytes:
    """提取LSB隐藏的bytes，自动解析4字节长度头"""
    arr = np.array(img)
    flat = arr.reshape(-1)
    bits = [int(flat[i] & 1) for i in range(len(flat))]

    def read_byte(offset):
        v = 0
        for i in range(8):
            v |= (bits[offset+i] << i)
        return v, offset+8

    offset = 0
    # 读取4字节长度
    len_bytes = bytearray()
    for _ in range(4):
        b, offset = read_byte(offset)
        len_bytes.append(b)
    data_len = int.from_bytes(len_bytes, byteorder="little")
    # 读取真实秘密数据
    out = bytearray()
    for _ in range(data_len):
        b, offset = read_byte(offset)
        out.append(b)
    return bytes(out)

def encode_with_ecc(data: bytes, nsym=32) -> bytes:
    """
    给原始字节附加RS纠错校验，输出完整数据包
    :param data: 原始输入字节
    :param nsym: 校验冗余
    :return: data + RS纠错校验码 的合并数据包
    """
    if nsym:
        # 配置：设置32字节校验冗余；最多纠正16字节错误
        rsc = RSCodec(nsym=nsym)
        packet = rsc.encode(data)
    else:
        packet = data
    return packet

def decode_with_ecc(packet: bytes, nsym=32) -> bytes:
    """
    输入带RS校验的数据包，自动纠错，返回原始字节
    :param packet: encode_with_ecc输出的数据包
    :param nsym: 校验冗余
    :return: 还原后的原始bytes
    :raises Exception: 错误过多无法纠错抛出异常
    """
    if nsym:
        rsc = RSCodec(nsym=nsym)
        # decode返回 (原始数据, 纠错后的完整块, 纠错统计)
        raw_data, _, _ = rsc.decode(packet)
    else:
        raw_data = packet
    return bytes(raw_data)

def pack_header(data_size):
    """打包：固定长度包头+数据，解决粘包"""
    header = struct.pack(HEADER_FORMAT, data_size)
    return header

def unpack_header(header):
    data_size = struct.unpack(HEADER_FORMAT, header)[0]
    return data_size

def recursion(target_path):
    items = dm.get_dir_items(target_path)
    files_path = []
    for folder_path in items["folder"]:
        internal_files_path = recursion(folder_path)
        files_path.extend(internal_files_path)
    for file_path in items["file"]:
        files_path.append(file_path)
    return files_path

def get_target_items(target_path):
    items = recursion(target_path)
    item_map = []
    for i, item in enumerate(items):
        item = item.replace(target_path, "")
        item_map.append(item[1:])
    return items, item_map

def pack_data(data):
    data_len = len(data)
    header = pack_header(data_len)
    return header + data

def folder_pack(folder_path, public_bytes, compress=False, system_name=b"Zorn", hash_truncate=16, save_path=None):
    target_path = folder_path
    items, item_map = get_target_items(target_path)

    # print(items)
    # print(item_map)
    map_b = json.dumps(item_map, ensure_ascii=False).encode()

    en_map_b = pack(map_b, public_bytes, compress=compress, system_name=system_name, hash_truncate=hash_truncate)
    # print(len(en_map_b))
    map_data = pack_data(en_map_b)
    # print(unpack_header(map_data[:HEADER_LENGTH]))
    if save_path:
        with open(save_path, mode="wb") as wf:
            pass
        with open(save_path, mode="ab") as wf:
            wf.write(map_data)
            for i, file_path in enumerate(items):
                with open(file_path, mode="rb") as f:
                    data = f.read()
                en_data = pack(data, public_bytes, compress=compress, system_name=system_name, hash_truncate=hash_truncate)
                wf.write(pack_data(en_data))
                yield (i+1) / len(items)
        return 1.0
    else:
        all_data = map_data
        for file_path in items:
            with open(file_path, mode="rb") as f:
                data = f.read()
            en_data = pack(data, public_bytes, compress=compress, system_name=system_name, hash_truncate=hash_truncate)
            all_data += pack_data(en_data)
        return all_data

def folder_unpack(folder_data, private_bytes, public_bytes, compress=False, system_name=b"Zorn", hash_truncate=16, save_path=None):
    if type(folder_data) is bytes:
        all_data = folder_data
        folder_name = save_path
        map_len_header = all_data[:HEADER_LENGTH]
        map_len = unpack_header(map_len_header)
        en_map_b = all_data[HEADER_LENGTH : HEADER_LENGTH + map_len]
        data_index = HEADER_LENGTH + map_len
        map_b = unpack(en_map_b, private_bytes, public_bytes, decompress=compress, system_name=system_name, hash_truncate=hash_truncate)
        item_map = json.loads(map_b.decode())
        for item in item_map:
            save_path = os.path.join(folder_name, item)
            file_len_header = all_data[data_index:data_index+HEADER_LENGTH]
            file_len = unpack_header(file_len_header)
            file_en_data = all_data[data_index+HEADER_LENGTH:data_index+HEADER_LENGTH+file_len]
            data_index = data_index+HEADER_LENGTH+file_len
            file_data = unpack(file_en_data, private_bytes, public_bytes, decompress=compress, system_name=system_name, hash_truncate=hash_truncate)
            folder_path = os.path.dirname(save_path)
            os.makedirs(folder_path, exist_ok=True)
            with open(save_path, mode="wb") as f:
                f.write(file_data)
    else:
        folder_name = save_path
        with open(folder_data, mode="rb") as rf:
            map_len_header = rf.read(HEADER_LENGTH)
            map_len = unpack_header(map_len_header)
            en_map_b = rf.read(map_len)
            map_b = unpack(en_map_b, private_bytes, public_bytes, decompress=compress, system_name=system_name, hash_truncate=hash_truncate)
            item_map = json.loads(map_b.decode())
            for i, item in enumerate(item_map):
                out_file_path = os.path.join(folder_name, item)
                file_len_header = rf.read(HEADER_LENGTH)
                file_len = unpack_header(file_len_header)
                file_en_data = rf.read(file_len)
                file_data = unpack(file_en_data, private_bytes, public_bytes, decompress=compress, system_name=system_name, hash_truncate=hash_truncate)
                out_dir = os.path.dirname(out_file_path)
                os.makedirs(out_dir, exist_ok=True)
                with open(out_file_path, mode="wb") as wf:
                    wf.write(file_data)
                yield (i+1) / len(item_map)

def pack_header(data_size):
    """打包：固定长度包头+数据，解决粘包"""
    header = struct.pack(HEADER_FORMAT, data_size)
    return header

def pack_data(data):
    data_len = len(data)
    header = pack_header(data_len)
    return header + data

def unpack_header(header):
    data_size = struct.unpack(HEADER_FORMAT, header)[0]
    return data_size

def pack_block(file_path, save_path, public_bytes, compress=False, system_name=b"Zorn", hash_truncate=16, block_size=1024**2*10):
    size = 0
    file_size = dm.get_file_size(file_path, num_mode=True)
    block_nums = file_size // block_size+1
    with open(save_path, mode="wb") as wf:
        pass
    with open(save_path, mode="ab") as wf:
        with open(file_path, mode="rb") as f:
            for _ in range(block_nums):
                original_data = f.read(block_size)
                data = pack(original_data, public_bytes, compress=compress, system_name=system_name, hash_truncate=hash_truncate)
                pack_header_data = pack_data(data)
                wf.write(pack_header_data)
                size += len(pack_header_data)
    return size

def unpack_block(save_path, file_path, private_bytes, public_bytes, decompress=False, system_name=b"Zorn", hash_truncate=16):
    with open(file_path, mode="wb") as f:
        pass
    with open(file_path, mode="ab") as wf:
        with open(save_path, mode="rb") as f:
            while True:
                len_header = f.read(HEADER_LENGTH)
                if not len_header:
                    break
                data_length = unpack_header(len_header)
                en_data = f.read(data_length)
                data = unpack(en_data, private_bytes, public_bytes, decompress=decompress, system_name=system_name, hash_truncate=hash_truncate)
                wf.write(data)

def recursion(target_path):
    items = dm.get_dir_items(target_path)
    files_path = []
    for folder_path in items["folder"]:
        internal_files_path = recursion(folder_path)
        files_path.extend(internal_files_path)
    for file_path in items["file"]:
        files_path.append(file_path)
    return files_path

def get_target_items(target_path):
    items = recursion(target_path)
    item_map = []
    for i, item in enumerate(items):
        item = item.replace(target_path, "")
        item_map.append(item[1:])
    return items, item_map

def write_block(wf, data_path, block_size=1024**2*10):
    with open(data_path, mode="rb") as f:
        while True:
            data = f.read(block_size)
            if not data:
                break
            wf.write(data)

def prepend_bytes_no_load_all(file_path: str, header_bytes: bytes, chunk_size=1024*1024*4):
    """
    在文件最开头插入字节，不读取整个文件进内存
    :param file_path: 目标文件
    :param header_bytes: 需要加到头部的字节
    :param chunk_size: 流式拷贝块大小
    """
    temp_path = file_path + ".tmp"
    with open(temp_path, "wb") as fw, open(file_path, "rb") as fr:
        fw.write(header_bytes)
        while True:
            chunk = fr.read(chunk_size)
            if not chunk:
                break
            fw.write(chunk)
    # 原子替换
    os.replace(temp_path, file_path)

def folder_pack_block(folder_path, save_path, public_bytes, compress=False, system_name=b"Zorn", hash_truncate=16, block_size=1024**2*10):
    temporary_path = "_temporary.bin"
    target_path = folder_path
    items, item_map = get_target_items(target_path)
    map_b = json.dumps(item_map, ensure_ascii=False).encode()
    en_map_b = pack(map_b, public_bytes, compress=compress, system_name=system_name, hash_truncate=hash_truncate)
    map_data = pack_data(en_map_b)

    # 直接wb模式创建并写入索引，无需重复打开
    with open(save_path, mode="wb") as wf:
        wf.write(map_data)
        for i, file_path in enumerate(items):
            # 获取打包后文件的真实总大小
            file_en_size = pack_block(file_path, temporary_path, public_bytes,
                                     compress=compress, system_name=system_name,
                                     hash_truncate=hash_truncate, block_size=block_size)
            wf.write(pack_header(file_en_size))
            write_block(wf, temporary_path, block_size=block_size)
            yield (i+1) / len(items)

    os.remove(temporary_path)
    return 1.0

def folder_unpack_block(folder_file_path, save_path, private_bytes, public_bytes, compress=False, system_name=b"Zorn", hash_truncate=16, block_size=1024**2*10):
    temporary_path = "_temporary.bin"
    folder_name = save_path
    with open(folder_file_path, mode="rb") as rf:
        # 读取文件索引
        map_len_header = rf.read(HEADER_LENGTH)
        map_len = unpack_header(map_len_header)
        en_map_b = rf.read(map_len)
        map_b = unpack(en_map_b, private_bytes, public_bytes, decompress=compress, system_name=system_name, hash_truncate=hash_truncate)
        item_map = json.loads(map_b.decode())
        for i, item in enumerate(item_map):
            # 读取当前文件的总长度
            file_len_header = rf.read(HEADER_LENGTH)
            if len(file_len_header) < HEADER_LENGTH:
                break
            file_len = unpack_header(file_len_header)

            # 流式读取对应长度的加密数据，写入临时文件
            remaining = file_len
            with open(temporary_path, "wb") as tf:
                while remaining > 0:
                    read_size = min(remaining, block_size)
                    chunk = rf.read(read_size)
                    if not chunk:
                        break
                    tf.write(chunk)
                    remaining -= len(chunk)

            # 创建目录并解包
            out_file_path = os.path.join(folder_name, item)
            os.makedirs(os.path.dirname(out_file_path), exist_ok=True)
            unpack_block(temporary_path, out_file_path, private_bytes, public_bytes,
                        decompress=compress, system_name=system_name, hash_truncate=hash_truncate)

            yield (i+1) / len(item_map)

    # 清理临时文件（移到with块外，确保文件关闭后再删除）
    if os.path.exists(temporary_path):
        os.remove(temporary_path)
    return 1.0