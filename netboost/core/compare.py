"""NetBoost - Before/After Comparison Module."""


def compare(before: dict, after: dict) -> dict:
    """Compare before and after speed test + scan results.
    
    Returns a dict of comparison items with changes.
    """
    items = []

    def add_item(name, before_val, after_val, unit, lower_is_better=False):
        if before_val is None or after_val is None:
            return
        if before_val < 0 or after_val < 0:
            return

        if before_val == 0:
            change_pct = 0
        else:
            change_pct = ((after_val - before_val) / before_val) * 100

        if lower_is_better:
            improved = after_val < before_val
        else:
            improved = after_val > before_val

        items.append({
            "name": name,
            "before": before_val,
            "after": after_val,
            "unit": unit,
            "change_pct": round(change_pct, 1),
            "improved": improved,
            "unchanged": abs(change_pct) < 2,
        })

    # Speed metrics
    add_item("下载速度", before.get("download_mbps"), after.get("download_mbps"), "Mbps")
    add_item("上传速度", before.get("upload_mbps"), after.get("upload_mbps"), "Mbps")
    add_item("延迟", before.get("latency_ms"), after.get("latency_ms"), "ms", lower_is_better=True)
    add_item("抖动", before.get("jitter_ms"), after.get("jitter_ms"), "ms", lower_is_better=True)
    add_item("丢包率", before.get("packet_loss_pct"), after.get("packet_loss_pct"), "%", lower_is_better=True)
    add_item("DNS 响应", before.get("dns_avg_ms"), after.get("dns_avg_ms"), "ms", lower_is_better=True)

    # Score
    add_item("网络评分", before.get("score"), after.get("score"), "分")

    # Summary
    improved = [i for i in items if i["improved"]]
    unchanged = [i for i in items if i["unchanged"]]
    degraded = [i for i in items if not i["improved"] and not i["unchanged"]]

    return {
        "items": items,
        "improved_count": len(improved),
        "unchanged_count": len(unchanged),
        "degraded_count": len(degraded),
        "summary": _generate_summary(items, improved, degraded),
    }


def _generate_summary(items, improved, degraded):
    """Generate human-readable summary."""
    lines = []
    for item in improved:
        pct = abs(item["change_pct"])
        if pct > 10:
            lines.append(f"✅ {item['name']}: 显著改善 ({'+' if not item.get('_lower_better') else '-'}{pct}%)")
        else:
            lines.append(f"✅ {item['name']}: 有改善 ({pct}%)")

    for item in degraded:
        pct = abs(item["change_pct"])
        if pct > 5:
            lines.append(f"⚠️ {item['name']}: 有所下降 ({pct}%)")

    unchanged_names = [i["name"] for i in items if i["unchanged"]]
    if unchanged_names:
        lines.append(f"➖ 无明显变化: {', '.join(unchanged_names)}")

    if not improved and not degraded:
        lines.append("ℹ️ 各项指标无明显变化")

    return "\n".join(lines)


def format_comparison_table(comparison: dict) -> str:
    """Format comparison as a CLI-friendly table."""
    items = comparison["items"]
    if not items:
        return "无对比数据"

    # Calculate column widths
    name_w = max(len(i["name"]) for i in items) + 2
    val_w = 12

    lines = []
    sep = "+" + "-" * (name_w + 2) + "+" + "-" * val_w + "+" + "-" * val_w + "+" + "-" * val_w + "+"
    header = f"| {'指标':<{name_w}} | {'优化前':^{val_w - 2}} | {'优化后':^{val_w - 2}} | {'变化':^{val_w - 2}} |"

    lines.append(sep)
    lines.append(header)
    lines.append(sep)

    for item in items:
        before_str = f"{item['before']} {item['unit']}"
        after_str = f"{item['after']} {item['unit']}"
        
        pct = item["change_pct"]
        if item["unchanged"]:
            change_str = "  --"
        elif item["improved"]:
            if pct > 0:
                change_str = f"  ↑ +{pct}%"
            else:
                change_str = f"  ↓ {pct}%"
        else:
            if pct > 0:
                change_str = f"  ↑ +{pct}%"
            else:
                change_str = f"  ↓ {pct}%"

        # Add star for significant improvements
        if item["improved"] and abs(pct) > 30:
            change_str += " ★★"
        elif item["improved"] and abs(pct) > 10:
            change_str += " ★"

        line = f"| {item['name']:<{name_w}} | {before_str:^{val_w - 2}} | {after_str:^{val_w - 2}} | {change_str:<{val_w - 2}} |"
        lines.append(line)

    lines.append(sep)
    return "\n".join(lines)
