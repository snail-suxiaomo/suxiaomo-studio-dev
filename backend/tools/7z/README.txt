放置 7-Zip 可执行文件，用于解压「skills 上传」里的 .7z / .rar 压缩包。

用法：
1. 从 https://7-zip.org 下载 7-Zip（Windows 版），把 7z.exe（或 7za.exe）放到本目录。
2. 打包时 desktop/package.json 的 extraResources 已包含 tools/7z/，会随安装包分发。
3. 运行时后端会优先使用本目录的 7z.exe；找不到时再尝试系统 PATH 上的 7z / 7za。

说明：
- .zip / .tar(.gz/.bz2/.xz) 用 Python 标准库解压，无需本文件。
- 若本目录与系统都无 7-Zip，上传 .7z / .rar 会提示「请安装 7-Zip 或改用 zip/tar」。
- 7-Zip 为 LGPL 开源软件，可随本软件免费分发。
