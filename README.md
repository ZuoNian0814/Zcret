# Zcret
Lightweight file encryption tool | 轻量化文件加密工具

windows开发环境，其余环境适配度未知，依赖的模块在主页中有。

公钥加密动态密钥，支持文件和文件夹。

- 加密：X25519Cipher, AesGcmCipher
- 压缩：Bz2Compressor
- 哈希校验：HmacSha256Hash
  
附加图像嵌入数据操作，带纠错码。

支持定制化文件图标和后缀，注意后缀参与哈希校验，不同配置的加解密不互通

Windows development environment, the compatibility with other environments is unknown, and the dependent modules are on the homepage.

Public key encryption dynamic key, supports files and folders.

- Encryption: X25519Cipher, AesGcmCipher,
- Compression: Bz2Compressor
- Hash verification: HmacSha256Hash
  
Additional image embedding data operation with error correction code.

Support customized file icons and suffixes, note that suffixes participate in hash verification, and encryption and decryption configurations are not compatible
