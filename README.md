<div align="center">

# NetBoost

**网络诊断与优化工具**

扫描 · 测速 · 诊断 · 优化 · 验证

[![Release](https://img.shields.io/github/v/release/Saint1010-arch/netboost?style=flat-square)](https://github.com/Saint1010-arch/netboost/releases)
[![License](https://img.shields.io/github/license/Saint1010-arch/netboost?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.7+-blue?style=flat-square)](https://python.org)

</div>

---

## 它解决什么问题

网速不达标、网页加载慢、视频卡顿——问题可能出在 DNS 配置、Wi-Fi 信道拥堵、MTU 不匹配、代理检测延迟等任何一个环节。

NetBoost 自动扫描你的网络环境，定位瓶颈，给出可执行的优化方案。优化前后自动对比，验证改善效果。所有改动可一键还原。

## 功能

| 模块 | 说明 |
|------|------|
| 环境扫描 | 接口 / 网关 / DNS / Wi-Fi 信号 / MTU / VPN / 代理 / 丢包 / 延迟 |
| 内置测速 | 基于 Cloudflare CDN，零依赖，不需要打开浏览器 |
| 诊断引擎 | 100 分制评分，自动识别 6+ 类问题并排列优先级 |
| 优化执行 | DNS 切换 / 缓存刷新 / TCP 参数 / 代理检测 / Wi-Fi 重连 / MTU 调整 |
| 效果验证 | 优化前后自动对比，量化改善幅度 |
| 一键还原 | 所有改动记录回滚脚本，随时恢复 |

## 界面

Web Dashboard —— 深色主题，数据可视化，浏览器中运行。

```
python netboost.py
```

启动后自动在浏览器打开 `http://127.0.0.1:7890`

## 快速开始

**Windows**
```
双击「点我启动.vbs」
```

**macOS**
```
双击 other-platforms/启动 NetBoost.command
```

**Linux**
```bash
bash other-platforms/启动\ NetBoost.sh
```

**命令行模式**
```bash
python netboost.py --cli
```

## 工作流程

```
扫描环境 → 测速 → 生成诊断报告 → 展示优化建议
                                          ↓
                                 用户确认后执行优化
                                          ↓
                                   重新测速 · 前后对比
```

每一步操作都需要用户确认。不会静默修改任何系统设置。

## 优化项目

| 项目 | 作用 | 风险 |
|------|------|------|
| DNS 切换 | 降低域名解析延迟 50-500ms | 低 |
| DNS 缓存刷新 | 清除过期/错误缓存记录 | 低 |
| TCP Nagle 关闭 | 减少小包延迟 5-20ms | 低 |
| 自动代理检测关闭 | 消除每次连接 0.5-2s 的检测等待 | 低 |
| Wi-Fi 重连 | 重新协商信道，刷新连接状态 | 低 |
| MTU 调整 | 减少分片重传，降低丢包 | 低 |

## 安全策略

- 扫描阶段只读，不修改设置
- 优化需逐项确认
- 不触碰 VPN 配置
- 所有改动可还原
- 代码开源可审计

## 技术栈

- Python 3.7+，零外部依赖
- 前端: HTML/CSS/JS 单页面 Dashboard
- 后端: Python 内置 HTTPServer
- 跨平台: Windows / macOS / Linux

## License

MIT