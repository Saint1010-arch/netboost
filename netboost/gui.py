"""NetBoost - Premium GUI Interface (Tkinter).

High-end dark theme with animations, progress rings, and polished UX.
Zero-dependency. Built with Tkinter + Canvas custom drawing.
"""
import threading
import time
import math
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import os

from . import utils
from .core import scanner, speedtest, diagnosis, optimizer, compare


# ============ Color Palette ============
class Theme:
    BG = "#0f0f1a"
    BG_CARD = "#1a1a2e"
    BG_CARD_HOVER = "#222240"
    BG_INPUT = "#12121f"
    ACCENT = "#6c5ce7"
    ACCENT_LIGHT = "#a29bfe"
    GREEN = "#00b894"
    GREEN_LIGHT = "#55efc4"
    YELLOW = "#fdcb6e"
    RED = "#e17055"
    RED_LIGHT = "#fab1a0"
    BLUE = "#74b9ff"
    CYAN = "#00cec9"
    TEXT = "#f0f0f0"
    TEXT_DIM = "#636e72"
    TEXT_MUTED = "#4a4a5a"
    BORDER = "#2d2d44"
    PROGRESS_BG = "#1e1e30"
    SHADOW = "#0a0a12"


class NetBoostGUI:
    """Main GUI application with premium dark theme."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("NetBoost")
        self.root.geometry("760x860")
        self.root.minsize(680, 780)
        self.root.configure(bg=Theme.BG)

        # Remove default title bar style on Windows
        try:
            self.root.attributes("-alpha", 0.97)
        except:
            pass

        # State
        self.scan_results = None
        self.speed_before = None
        self.speed_after = None
        self.report = None
        self.report_after = None
        self.actions = []
        self.running = False
        self.score_angle = 0
        self.anim_id = None

        self._build_ui()
        self._center_window()

    def _center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"+{x}+{y}")

    def _build_ui(self):
        """Build the complete UI."""
        # Main scrollable area
        self.main_frame = tk.Frame(self.root, bg=Theme.BG)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=16)

        # ---- Header ----
        header = tk.Frame(self.main_frame, bg=Theme.BG)
        header.pack(fill=tk.X, pady=(0, 20))

        title_frame = tk.Frame(header, bg=Theme.BG)
        title_frame.pack(side=tk.LEFT)

        tk.Label(title_frame, text="NetBoost", font=("Segoe UI", 24, "bold"),
                bg=Theme.BG, fg=Theme.ACCENT_LIGHT).pack(side=tk.LEFT)
        tk.Label(title_frame, text="  网络加速助手", font=("Segoe UI", 13),
                bg=Theme.BG, fg=Theme.TEXT_DIM).pack(side=tk.LEFT, pady=(8, 0))

        # Version badge
        ver_frame = tk.Frame(header, bg=Theme.BG)
        ver_frame.pack(side=tk.RIGHT, pady=(8, 0))
        tk.Label(ver_frame, text=" v1.0 ", font=("Consolas", 9),
                bg=Theme.BORDER, fg=Theme.TEXT_DIM).pack()

        # ---- Score Card (Canvas for ring) ----
        self.score_card = tk.Frame(self.main_frame, bg=Theme.BG_CARD, highlightthickness=1,
                                   highlightbackground=Theme.BORDER)
        self.score_card.pack(fill=tk.X, pady=(0, 16), ipady=12)

        # Score ring canvas
        self.score_canvas = tk.Canvas(self.score_card, width=140, height=140,
                                      bg=Theme.BG_CARD, highlightthickness=0)
        self.score_canvas.pack(pady=(16, 4))
        self._draw_score_ring(0, "--")

        self.score_status = tk.Label(self.score_card, text="点击下方按钮开始诊断",
                                     font=("Segoe UI", 11), bg=Theme.BG_CARD, fg=Theme.TEXT_DIM)
        self.score_status.pack(pady=(0, 4))

        # Metrics row
        self.metrics_frame = tk.Frame(self.score_card, bg=Theme.BG_CARD)
        self.metrics_frame.pack(fill=tk.X, padx=40, pady=(8, 12))

        self.metric_widgets = {}
        metrics_config = [
            ("download", "下载", "--", "Mbps"),
            ("upload", "上传", "--", "Mbps"),
            ("latency", "延迟", "--", "ms"),
            ("loss", "丢包", "--", "%"),
        ]
        for key, label, val, unit in metrics_config:
            col = tk.Frame(self.metrics_frame, bg=Theme.BG_CARD)
            col.pack(side=tk.LEFT, expand=True)
            val_lbl = tk.Label(col, text=val, font=("Segoe UI", 16, "bold"),
                              bg=Theme.BG_CARD, fg=Theme.TEXT)
            val_lbl.pack()
            sub_lbl = tk.Label(col, text=label + " " + unit, font=("Segoe UI", 9),
                              bg=Theme.BG_CARD, fg=Theme.TEXT_DIM)
            sub_lbl.pack()
            self.metric_widgets[key] = val_lbl

        # ---- Action Buttons ----
        btn_frame = tk.Frame(self.main_frame, bg=Theme.BG)
        btn_frame.pack(fill=tk.X, pady=(0, 16))

        self.start_btn = self._make_button(btn_frame, "开始诊断", Theme.ACCENT, self._on_start, bold=True)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.export_btn = self._make_button(btn_frame, "导出报告", Theme.BORDER, self._on_export)
        self.export_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.export_btn.configure(state=tk.DISABLED)

        self.rollback_btn = self._make_button(btn_frame, "还原改动", Theme.BORDER, self._on_rollback)
        self.rollback_btn.pack(side=tk.LEFT)
        self.rollback_btn.configure(state=tk.DISABLED)

        # ---- Progress bar ----
        self.progress_frame = tk.Frame(self.main_frame, bg=Theme.PROGRESS_BG, height=4)
        self.progress_frame.pack(fill=tk.X, pady=(0, 16))
        self.progress_frame.pack_propagate(False)

        self.progress_bar = tk.Frame(self.progress_frame, bg=Theme.ACCENT, height=4, width=0)
        self.progress_bar.place(x=0, y=0, relheight=1)

        # ---- Results Area ----
        self.results_frame = tk.Frame(self.main_frame, bg=Theme.BG)
        self.results_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollable canvas for results
        self.canvas = tk.Canvas(self.results_frame, bg=Theme.BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.results_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scroll_inner = tk.Frame(self.canvas, bg=Theme.BG)

        self.scroll_inner.bind("<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_inner, anchor=tk.NW, width=700)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mouse wheel scroll
        self.canvas.bind_all("<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        # ---- Log Area ----
        log_label = tk.Label(self.main_frame, text="运行日志", font=("Segoe UI", 9, "bold"),
                            bg=Theme.BG, fg=Theme.TEXT_DIM, anchor=tk.W)
        log_label.pack(fill=tk.X, pady=(12, 4))

        self.log_text = tk.Text(self.main_frame, height=5, bg=Theme.BG_INPUT, fg=Theme.TEXT_MUTED,
                               font=("Consolas", 9), relief=tk.FLAT, wrap=tk.WORD, padx=10, pady=8,
                               insertbackground=Theme.TEXT_MUTED, highlightthickness=1,
                               highlightbackground=Theme.BORDER)
        self.log_text.pack(fill=tk.X)
        self.log_text.configure(state=tk.DISABLED)

    def _make_button(self, parent, text, bg_color, command, bold=False):
        """Create a styled flat button."""
        font = ("Segoe UI", 11, "bold") if bold else ("Segoe UI", 10)
        btn = tk.Button(parent, text=text, font=font,
                       bg=bg_color, fg=Theme.TEXT, relief=tk.FLAT,
                       padx=18, pady=8, cursor="hand2",
                       activebackground=Theme.ACCENT_LIGHT, activeforeground=Theme.BG,
                       command=command)
        # Hover effect
        def on_enter(e): btn.configure(bg=Theme.ACCENT_LIGHT if bg_color == Theme.ACCENT else Theme.BG_CARD_HOVER)
        def on_leave(e): btn.configure(bg=bg_color)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    # ============ Drawing ============

    def _draw_score_ring(self, score, label_text, color=None):
        """Draw an animated score ring on canvas."""
        c = self.score_canvas
        c.delete("all")
        cx, cy, r = 70, 70, 55

        if color is None:
            if isinstance(score, int):
                if score >= 90: color = Theme.GREEN
                elif score >= 70: color = Theme.BLUE
                elif score >= 50: color = Theme.YELLOW
                else: color = Theme.RED
            else:
                color = Theme.BORDER

        # Background ring
        c.create_oval(cx-r, cy-r, cx+r, cy+r, outline=Theme.PROGRESS_BG, width=8)

        # Score arc
        if isinstance(score, (int, float)) and score > 0:
            extent = score / 100 * 360
            c.create_arc(cx-r, cy-r, cx+r, cy+r, start=90, extent=-extent,
                        outline=color, width=8, style=tk.ARC)

        # Center text
        display = str(score) if isinstance(score, int) else score
        c.create_text(cx, cy - 8, text=display, font=("Segoe UI", 28, "bold"),
                     fill=color if isinstance(score, int) else Theme.TEXT_DIM)
        c.create_text(cx, cy + 20, text=label_text, font=("Segoe UI", 10),
                     fill=Theme.TEXT_DIM)

    def _animate_score(self, target, label_text):
        """Animate score ring from 0 to target."""
        def step(current):
            if current <= target:
                self.root.after(0, lambda: self._draw_score_ring(current, label_text))
                self.root.after(20, lambda: step(current + 2))
        step(0)

    def _set_progress(self, fraction):
        """Set progress bar 0.0~1.0."""
        def do():
            w = self.progress_frame.winfo_width()
            self.progress_bar.place(x=0, y=0, width=max(1, int(w * fraction)), relheight=1)
            if fraction >= 1.0:
                self.progress_bar.configure(bg=Theme.GREEN)
            else:
                self.progress_bar.configure(bg=Theme.ACCENT)
        self.root.after(0, do)

    # ============ Helpers ============

    def _log(self, msg):
        def do():
            self.log_text.configure(state=tk.NORMAL)
            t = time.strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{t}] {msg}\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)
        self.root.after(0, do)

    def _update_score(self, score, label):
        self.root.after(0, lambda: self._animate_score(score, label))

    def _update_status(self, text):
        self.root.after(0, lambda: self.score_status.configure(text=text))

    def _update_metric(self, key, value):
        def do():
            if key in self.metric_widgets:
                self.metric_widgets[key].configure(text=str(value))
        self.root.after(0, do)

    def _clear_results(self):
        def do():
            for w in self.scroll_inner.winfo_children():
                w.destroy()
        self.root.after(0, do)

    def _add_card(self, title, detail="", icon_color=Theme.ACCENT, tag=""):
        """Add a result card."""
        def do():
            card = tk.Frame(self.scroll_inner, bg=Theme.BG_CARD, highlightthickness=1,
                           highlightbackground=Theme.BORDER, padx=14, pady=10)
            card.pack(fill=tk.X, pady=3)

            # Color accent bar on left
            accent = tk.Frame(card, bg=icon_color, width=4)
            accent.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

            content = tk.Frame(card, bg=Theme.BG_CARD)
            content.pack(side=tk.LEFT, fill=tk.X, expand=True)

            # Tag badge
            top_row = tk.Frame(content, bg=Theme.BG_CARD)
            top_row.pack(fill=tk.X)
            if tag:
                tk.Label(top_row, text=f" {tag} ", font=("Segoe UI", 8),
                        bg=icon_color, fg="white").pack(side=tk.LEFT, padx=(0, 8))
            tk.Label(top_row, text=title, font=("Segoe UI", 11, "bold"),
                    bg=Theme.BG_CARD, fg=Theme.TEXT).pack(side=tk.LEFT)

            if detail:
                tk.Label(content, text=detail, font=("Segoe UI", 9),
                        bg=Theme.BG_CARD, fg=Theme.TEXT_DIM, wraplength=580,
                        justify=tk.LEFT, anchor=tk.W).pack(fill=tk.X, pady=(4, 0))
        self.root.after(0, do)

    def _ask_thread_safe(self, title, message):
        result = [False]
        event = threading.Event()
        def ask():
            result[0] = messagebox.askyesno(title, message, parent=self.root)
            event.set()
        self.root.after(0, ask)
        event.wait()
        return result[0]

    # ============ Main Flow ============

    def _on_start(self):
        if self.running:
            return
        self.running = True
        self.start_btn.configure(state=tk.DISABLED, text="运行中...", bg=Theme.BORDER)
        self._set_progress(0)
        self._clear_results()
        threading.Thread(target=self._run_flow, daemon=True).start()

    def _run_flow(self):
        try:
            # Phase 1: Scan
            self._update_status("正在扫描网络环境...")
            self._log("开始扫描（只读，不改任何设置）")
            self._set_progress(0.05)

            self.scan_results = scanner.scan_all(log_callback=self._log)
            self._set_progress(0.25)

            # Show scan summary cards
            wifi = self.scan_results.get("wifi", {})
            gw = self.scan_results.get("gateway", {})
            vpn = self.scan_results.get("vpn", {})

            if wifi.get("connected"):
                sig = str(wifi.get("signal_pct", "?")) + "%"
                self._add_card("Wi-Fi: " + wifi.get("ssid", "已连接"),
                              "信号 " + sig + " | 频道 " + str(wifi.get("channel", "?")) + " | " + str(wifi.get("band", "")),
                              Theme.GREEN, "已连接")
            if gw.get("ip"):
                self._add_card("网关: " + gw["ip"], "", Theme.BLUE)
            if vpn.get("active"):
                self._add_card("VPN: " + vpn.get("type", "已检测到"), "VPN 可能影响速度", Theme.YELLOW, "注意")

            # Phase 2: Speed test
            self._update_status("扫描完成，等待确认...")
            do_speed = self._ask_thread_safe("测速",
                "是否进行速度测试？\n\n将消耗约 30-80 MB 流量\n测速约需 30 秒")

            if do_speed:
                self._update_status("正在测速...")
                self._set_progress(0.3)
                self._log("开始速度测试...")

                def speed_progress(phase, frac, val):
                    base = 0.3 if phase == "download" else (0.5 if phase == "upload" else 0.25)
                    self._set_progress(base + frac * 0.15)

                self.speed_before = speedtest.run_speedtest(
                    log_callback=self._log,
                    progress_callback=speed_progress
                )
                self._update_metric("download", self.speed_before["download_mbps"])
                self._update_metric("upload", self.speed_before["upload_mbps"])
                self._update_metric("latency", self.speed_before["latency_ms"])
                self._update_metric("loss", self.speed_before["packet_loss_pct"])

            self._set_progress(0.65)

            # Phase 3: Diagnosis
            self._update_status("正在分析...")
            self.report = diagnosis.diagnose(self.scan_results, self.speed_before)
            self._update_score(self.report.score, self.report.score_label)
            self._set_progress(0.7)

            # Display issues
            self._clear_results()
            if not self.report.issues:
                self._add_card("网络状态良好", "未发现明显问题，你的网络很健康！", Theme.GREEN, "OK")
            else:
                for issue in self.report.issues:
                    colors = {"critical": Theme.RED, "warning": Theme.YELLOW, "info": Theme.BLUE}
                    tags = {"critical": "严重", "warning": "注意", "info": "提示"}
                    detail = issue.evidence + "\n" + issue.recommendation
                    self._add_card(issue.title, detail,
                                  colors.get(issue.severity, Theme.TEXT_DIM),
                                  tags.get(issue.severity, ""))

            # Phase 4: Optimization
            self.actions = optimizer.generate_actions(self.scan_results, self.report)
            self._set_progress(0.75)

            if self.actions:
                self._update_status("发现 " + str(len(self.actions)) + " 项可优化，等待确认...")
                approved = self._show_optimization_dialog()

                if approved:
                    self._update_status("正在优化...")
                    self._set_progress(0.8)
                    for i, action in enumerate(approved):
                        optimizer.execute_action(action, log_callback=self._log)
                        self._set_progress(0.8 + 0.1 * (i + 1) / len(approved))
                        time.sleep(0.3)

                    rollback_path = optimizer.save_rollback(approved)
                    if rollback_path:
                        self._log("还原脚本已保存: " + rollback_path)
                        self.root.after(0, lambda: self.rollback_btn.configure(state=tk.NORMAL, bg=Theme.BG_CARD))

                    # Phase 5: After speed test
                    if self.speed_before:
                        do_after = self._ask_thread_safe("再次测速",
                            "优化完成！\n\n是否再测一次看看效果？")
                        if do_after:
                            self._update_status("After 测速中...")
                            self._log("开始 After 测速...")
                            self.speed_after = speedtest.run_speedtest(log_callback=self._log)

                            new_dns = scanner.scan_dns_timing()
                            scan_after = dict(self.scan_results)
                            scan_after["dns_timing"] = new_dns
                            self.report_after = diagnosis.diagnose(scan_after, self.speed_after)

                            self._update_score(self.report_after.score, self.report_after.score_label)
                            self._update_metric("download", self.speed_after["download_mbps"])
                            self._update_metric("upload", self.speed_after["upload_mbps"])
                            self._update_metric("latency", self.speed_after["latency_ms"])
                            self._update_metric("loss", self.speed_after["packet_loss_pct"])

                            self._show_comparison()

            self._set_progress(1.0)
            self._update_status("完成！")
            self._log("所有步骤完成")
            self.root.after(0, lambda: self.export_btn.configure(state=tk.NORMAL, bg=Theme.BG_CARD))

        except Exception as e:
            self._log("出错: " + str(e))
            self._update_status("出错: " + str(e))
        finally:
            self.running = False
            self.root.after(0, lambda: self.start_btn.configure(
                state=tk.NORMAL, text="开始诊断", bg=Theme.ACCENT))

    def _show_optimization_dialog(self):
        """Show optimization approval dialog with checkboxes."""
        result = [None]
        event = threading.Event()

        def show():
            dlg = tk.Toplevel(self.root)
            dlg.title("优化建议")
            dlg.geometry("520x440")
            dlg.configure(bg=Theme.BG)
            dlg.transient(self.root)
            dlg.grab_set()

            # Center
            dlg.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() - 520) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - 440) // 2
            dlg.geometry(f"+{x}+{y}")

            tk.Label(dlg, text="以下优化可以自动执行", font=("Segoe UI", 13, "bold"),
                    bg=Theme.BG, fg=Theme.TEXT).pack(pady=(20, 4))
            tk.Label(dlg, text="勾选你想执行的项目，所有改动均可一键还原", font=("Segoe UI", 9),
                    bg=Theme.BG, fg=Theme.TEXT_DIM).pack(pady=(0, 12))

            vars_list = []
            scroll = tk.Frame(dlg, bg=Theme.BG)
            scroll.pack(fill=tk.BOTH, expand=True, padx=16)

            for action in self.actions:
                var = tk.BooleanVar(value=True)
                vars_list.append((var, action))

                card = tk.Frame(scroll, bg=Theme.BG_CARD, highlightthickness=1,
                               highlightbackground=Theme.BORDER, padx=12, pady=8)
                card.pack(fill=tk.X, pady=3)

                cb = tk.Checkbutton(card, text=action.title, variable=var,
                    bg=Theme.BG_CARD, fg=Theme.TEXT, selectcolor=Theme.BG_INPUT,
                    activebackground=Theme.BG_CARD, activeforeground=Theme.TEXT,
                    font=("Segoe UI", 10, "bold"))
                cb.pack(anchor=tk.W)

                risk_color = {"low": Theme.GREEN, "medium": Theme.YELLOW, "high": Theme.RED}.get(action.risk, Theme.TEXT_DIM)
                tk.Label(card, text="  " + action.expected_benefit + "  |  风险: " + action.risk,
                        bg=Theme.BG_CARD, fg=risk_color, font=("Segoe UI", 9)).pack(anchor=tk.W)

            btn_row = tk.Frame(dlg, bg=Theme.BG)
            btn_row.pack(fill=tk.X, pady=16, padx=16)

            def approve():
                result[0] = [a for v, a in vars_list if v.get()]
                dlg.destroy()
                event.set()

            def skip():
                result[0] = []
                dlg.destroy()
                event.set()

            self._make_button(btn_row, "执行选中项", Theme.GREEN, approve, bold=True).pack(side=tk.LEFT, padx=(0, 10))
            self._make_button(btn_row, "跳过", Theme.BORDER, skip).pack(side=tk.LEFT)

            dlg.protocol("WM_DELETE_WINDOW", skip)

        self.root.after(0, show)
        event.wait()
        return result[0] or []

    def _show_comparison(self):
        """Show before/after comparison cards."""
        if not self.speed_before or not self.speed_after:
            return

        before_data = {
            "download_mbps": self.speed_before.get("download_mbps", 0),
            "upload_mbps": self.speed_before.get("upload_mbps", 0),
            "latency_ms": self.speed_before.get("latency_ms", -1),
            "jitter_ms": self.speed_before.get("jitter_ms", -1),
            "packet_loss_pct": self.speed_before.get("packet_loss_pct", -1),
            "dns_avg_ms": self.report.metrics.get("dns_avg_ms", -1) if self.report else -1,
            "score": self.report.score if self.report else 0,
        }
        after_data = {
            "download_mbps": self.speed_after.get("download_mbps", 0),
            "upload_mbps": self.speed_after.get("upload_mbps", 0),
            "latency_ms": self.speed_after.get("latency_ms", -1),
            "jitter_ms": self.speed_after.get("jitter_ms", -1),
            "packet_loss_pct": self.speed_after.get("packet_loss_pct", -1),
            "dns_avg_ms": self.report_after.metrics.get("dns_avg_ms", -1) if self.report_after else -1,
            "score": self.report_after.score if self.report_after else 0,
        }

        comp = compare.compare(before_data, after_data)
        self._clear_results()
        self._add_card("Before / After 对比", "", Theme.CYAN, "对比")

        for item in comp["items"]:
            if item["unchanged"]:
                color, tag = Theme.TEXT_DIM, ""
            elif item["improved"]:
                color, tag = Theme.GREEN, "改善"
            else:
                color, tag = Theme.YELLOW, "下降"

            pct = item["change_pct"]
            pct_str = (" (+" if pct > 0 else " (") + str(pct) + "%)"
            text = str(item["before"]) + " " + item["unit"] + "  ->  " + str(item["after"]) + " " + item["unit"] + pct_str
            self._add_card(item["name"], text, color, tag)

    # ============ Toolbar Actions ============

    def _on_export(self):
        filepath = filedialog.asksaveasfilename(parent=self.root, defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("All Files", "*.*")],
            initialfile="netboost_report.md")
        if filepath and self.report:
            from .cli import _export_report
            _export_report(self.report, self.scan_results, self.speed_before,
                         self.speed_after, self.report_after, filepath)
            messagebox.showinfo("导出成功", "报告已保存到:\n" + filepath, parent=self.root)

    def _on_rollback(self):
        if messagebox.askyesno("确认还原", "还原所有 NetBoost 的改动？", parent=self.root):
            rollback_file = os.path.join(os.path.expanduser("~"), "netboost_rollback")
            rollback_file += ".bat" if utils.IS_WIN else ".sh"
            if os.path.exists(rollback_file):
                cmd = f'"{rollback_file}"' if utils.IS_WIN else f'bash "{rollback_file}"'
                utils.run_cmd(cmd, timeout=30)
                self._log("还原完成")
                messagebox.showinfo("还原完成", "所有改动已还原", parent=self.root)
            else:
                messagebox.showwarning("未找到", "未找到还原文件:\n" + rollback_file, parent=self.root)

    def run(self):
        self.root.mainloop()


def gui_main():
    app = NetBoostGUI()
    app.run()
