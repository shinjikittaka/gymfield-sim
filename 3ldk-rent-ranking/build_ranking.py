#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
47都道府県 3LDK家賃ランキング生成スクリプト

data/prefecture_3ldk_rent.csv を読み込み、以下を output/ に生成する:
  - ranking.md      : 順位つきMarkdown表
  - ranking.xlsx    : Excel(順位・地方・都道府県・平均家賃・全国平均との差・比・偏差値)
  - heatmap.png     : 家賃の高い順の横棒ヒートマップ
  - map.png         : 日本地図(都道府県別コロプレス)

データを差し替える場合は data/prefecture_3ldk_rent.csv の rent_yen 列を
実測値(e-Stat 小売物価統計調査 / CHINTAI / SUUMO / LIFULL HOME'S 等)に置き換えて
再実行するだけでよい。

使い方:  python3 build_ranking.py
"""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, cm
from matplotlib.colors import Normalize

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "prefecture_3ldk_rent.csv")
OUT = os.path.join(HERE, "output")
os.makedirs(OUT, exist_ok=True)

# ---- 日本語フォント設定 (IPAGothic) ----
_JP_FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf",
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
]
JP_FONT = next((p for p in _JP_FONT_CANDIDATES if os.path.exists(p)), None)
if JP_FONT:
    font_manager.fontManager.addfont(JP_FONT)
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=JP_FONT).get_name()
plt.rcParams["axes.unicode_minus"] = False


def load() -> pd.DataFrame:
    df = pd.read_csv(DATA)
    df = df.sort_values("rent_yen", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))
    national_avg = df["rent_yen"].mean()
    df["nat_avg_diff"] = (df["rent_yen"] - national_avg).round(0).astype(int)
    df["nat_avg_ratio"] = (df["rent_yen"] / national_avg * 100).round(1)
    std = df["rent_yen"].std(ddof=0)
    df["hensachi"] = (50 + 10 * (df["rent_yen"] - national_avg) / std).round(1)
    return df, national_avg


def write_markdown(df: pd.DataFrame, national_avg: float):
    lines = []
    lines.append("# 47都道府県 3LDK 平均家賃ランキング\n")
    lines.append(f"- 全国平均(単純平均): **{national_avg:,.0f}円**")
    lines.append(f"- 最高: {df.iloc[0]['prefecture']} {df.iloc[0]['rent_yen']:,}円 / "
                 f"最低: {df.iloc[-1]['prefecture']} {df.iloc[-1]['rent_yen']:,}円\n")
    lines.append("> ⚠️ 本表の家賃は**推計値**です(暮らしコストラボ2026の生活コスト係数モデル準拠)。"
                 "確定値にするには data/prefecture_3ldk_rent.csv の rent_yen を"
                 "e-Stat「小売物価統計調査」等の実測値へ差し替えて再生成してください。\n")
    lines.append("| 順位 | 地方 | 都道府県 | 平均家賃(円) | 全国平均との差(円) | 全国平均比(%) | 偏差値 |")
    lines.append("|---:|:--|:--|---:|---:|---:|---:|")
    for _, r in df.iterrows():
        diff = f"{r['nat_avg_diff']:+,}"
        lines.append(f"| {r['rank']} | {r['region']} | {r['prefecture']} | "
                     f"{r['rent_yen']:,} | {diff} | {r['nat_avg_ratio']:.1f} | {r['hensachi']:.1f} |")
    path = os.path.join(OUT, "ranking.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("written:", path)


def write_excel(df: pd.DataFrame, national_avg: float):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.formatting.rule import ColorScaleRule
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "3LDK家賃ランキング"

    headers = ["順位", "地方", "都道府県", "平均家賃(円)",
               "全国平均との差(円)", "全国平均比(%)", "偏差値", "データ種別"]
    ws.append(headers)

    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    head_fill = PatternFill("solid", fgColor="1F4E78")
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = head_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    for _, r in df.iterrows():
        ws.append([
            int(r["rank"]), r["region"], r["prefecture"], int(r["rent_yen"]),
            int(r["nat_avg_diff"]), float(r["nat_avg_ratio"]), float(r["hensachi"]), r["source"],
        ])

    n = len(df)
    for row in range(2, n + 2):
        for col in range(1, len(headers) + 1):
            ws.cell(row=row, column=col).border = border
        ws.cell(row=row, column=4).number_format = "#,##0"
        ws.cell(row=row, column=5).number_format = "+#,##0;-#,##0"
        ws.cell(row=row, column=6).number_format = "0.0"
        ws.cell(row=row, column=7).number_format = "0.0"

    # 家賃列にカラースケール(青=安 → 赤=高)
    ws.conditional_formatting.add(
        f"D2:D{n+1}",
        ColorScaleRule(start_type="min", start_color="63BE7B",
                       mid_type="percentile", mid_value=50, mid_color="FFEB84",
                       end_type="max", end_color="F8696B"),
    )

    widths = [6, 8, 12, 14, 18, 14, 8, 46]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"

    # 注記シート
    ws2 = wb.create_sheet("注記・出典")
    notes = [
        ["47都道府県 3LDK平均家賃ランキング — 注記"],
        [""],
        ["全国平均(単純平均)", f"{national_avg:,.0f}円"],
        [""],
        ["⚠️ 重要", "本ファイルの家賃は実測値ではなく推計値です。"],
        ["推計方法", "全国平均12万円 × 各都道府県の生活コスト係数(暮らしコストラボ2026準拠)"],
        ["検索で確認できた実値", "東京15万円 / 大阪13万円 / 神奈川 係数1.10 / 秋田 係数0.83 / 沖縄 係数0.88"],
        ["確定版にするには", "data/prefecture_3ldk_rent.csv の rent_yen 列を実測値へ差し替えて build_ranking.py を再実行"],
        [""],
        ["推奨する実測データ源", ""],
        ["公的(最も正確)", "総務省 小売物価統計調査(動向編) 民営家賃・3LDK — e-Stat で取得可"],
        ["民間ポータル(実勢)", "CHINTAI / SUUMO / LIFULL HOME'S の都道府県別 3LDK 家賃相場"],
        [""],
        ["生成日時基準", "暮らしコストラボ 2026年時点データを参照"],
    ]
    for row in notes:
        ws2.append(row)
    ws2.column_dimensions["A"].width = 22
    ws2.column_dimensions["B"].width = 70
    ws2.cell(row=1, column=1).font = Font(bold=True, size=13)
    ws2.cell(row=5, column=1).font = Font(bold=True, color="C00000")

    path = os.path.join(OUT, "ranking.xlsx")
    wb.save(path)
    print("written:", path)


def write_heatmap(df: pd.DataFrame, national_avg: float):
    d = df.sort_values("rent_yen", ascending=True)
    norm = Normalize(vmin=d["rent_yen"].min(), vmax=d["rent_yen"].max())
    colors = cm.YlOrRd(norm(d["rent_yen"].values))

    fig, ax = plt.subplots(figsize=(9, 12))
    labels = [f"{p}" for p in d["prefecture"]]
    bars = ax.barh(labels, d["rent_yen"], color=colors, edgecolor="white", linewidth=0.5)
    for bar, v in zip(bars, d["rent_yen"]):
        ax.text(bar.get_width() + 800, bar.get_y() + bar.get_height() / 2,
                f"{v/10000:.1f}万", va="center", ha="left", fontsize=8)
    ax.axvline(national_avg, color="#333333", linestyle="--", linewidth=1)
    ax.text(national_avg, len(d) - 0.3, f" 全国平均 {national_avg/10000:.1f}万",
            color="#333333", fontsize=9, ha="left")
    ax.set_xlabel("3LDK 平均家賃 (円)")
    ax.set_title("47都道府県 3LDK平均家賃ヒートマップ(推計値)", fontsize=14, pad=12)
    ax.set_xlim(0, d["rent_yen"].max() * 1.15)
    ax.margins(y=0.005)
    fig.tight_layout()
    path = os.path.join(OUT, "heatmap.png")
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("written:", path)


def write_map(df: pd.DataFrame):
    try:
        from japanmap import picture
    except Exception as e:  # pragma: no cover
        print("japanmap 未導入のため地図生成をスキップ:", e)
        return
    import numpy as np

    norm = Normalize(vmin=df["rent_yen"].min(), vmax=df["rent_yen"].max())
    cmap = cm.YlOrRd
    # japanmap は都道府県コード(1-47)→RGBのdictで塗り分け
    color_dict = {}
    for _, r in df.iterrows():
        rgba = cmap(norm(r["rent_yen"]))
        color_dict[int(r["pref_code"])] = tuple(int(255 * c) for c in rgba[:3])

    fig, (ax, cax) = plt.subplots(
        1, 2, figsize=(11, 9), gridspec_kw={"width_ratios": [20, 1]})
    ax.imshow(picture(color_dict))
    ax.axis("off")
    ax.set_title("47都道府県 3LDK平均家賃マップ(推計値)", fontsize=15, pad=12)

    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cb = fig.colorbar(sm, cax=cax)
    cb.set_label("平均家賃 (円)")
    fig.tight_layout()
    path = os.path.join(OUT, "map.png")
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("written:", path)


def main():
    df, national_avg = load()
    print(f"全国平均(単純平均): {national_avg:,.0f}円")
    write_markdown(df, national_avg)
    write_excel(df, national_avg)
    write_heatmap(df, national_avg)
    write_map(df)
    print("完了。output/ を確認してください。")


if __name__ == "__main__":
    main()
