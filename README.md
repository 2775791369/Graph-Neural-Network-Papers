# Graph-Neural-Network-Papers
图神经网络相关的资源合集、基于图深度学习的会议期刊。

## 下载论文脚本

仓库提供了 `scripts/download_papers.py` 脚本，用于根据 `GNNPapers.md`
中的目录批量下载论文，并按照章节名称自动整理为 `papers/<章节>/<论文标题>.pdf`
的层级结构。使用方式如下：

```bash
python scripts/download_papers.py
```

脚本会在终端输出成功与失败的条目，失败通常是由于网络限制或目标地址
无法直接访问所致。在可以访问外网的环境下运行，即可完成批量下载。

开发或测试时，可通过 `--limit N` 仅处理前 N 篇论文，或加入 `--dry-run`
参数仅查看计划的下载路径而不实际请求网络。


