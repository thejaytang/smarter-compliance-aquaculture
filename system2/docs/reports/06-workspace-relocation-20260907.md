# Workspace relocation | 2026-09-07

用户授权将原桌面 PDF Extraction Product 整体迁入 05/system2，并将原 05 内容置于 system1，创建 system3 与分层入口文档。

采用同文件系统目录移动。对文件、目录和符号链接比较 inode、size、mode 和 link target，不读取或改写 PDF、Gold 与历史产物内容。校验完成后只更新入口文档、状态、Git 忽略路径与虚拟环境启动路径。

迁移清单结果：

```json
{
  "system1_entries": 1864,
  "system2_entries": 145822,
  "same_inode_size_mode_symlinks": true,
  "workbook_sha256": "96aebadfbb42265c8a0e050cc0014006372b33711a5ed371a3ce0e61a7bf1fab"
}
```

System2 新位置本地 pytest 通过，1 项跳过，1 项 Starlette/httpx 弃用提示。System1 Doctor PASS，61 项回归中 60 项通过，Dashboard 隐藏列合同 1 项失败；工作簿 hash 在迁移前后及测试后相同，作为既存差异记录于 System1 状态。

未修改原始输入、Gold 或历史解析结果，未启动生产提取、来源检索、外部 API 或自动化。原目录路径没有保留别名；后续从新路径使用。
