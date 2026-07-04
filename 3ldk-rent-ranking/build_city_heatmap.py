#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市区町村別 3LDK家賃ヒートマップ生成スクリプト（汎用）

市区町村レベルの行政界ポリゴンはこの環境で取得できないため、
「日本地図の塗り分け」ではなく **順位バー型ヒートマップ** を出力する。

入力CSV（例: data/tokyo_3ldk_rent.csv）の列:
  municipality : 市区町村名（必須）
  rent_yen     : 3LDK平均家賃（円）← 実測値に差し替え可
  group        : グループ（任意。例: 23区 / 多摩）区切り線と平均線に使用
  source       : 出典メモ（任意）

使い方:
  python3 build_city_heatmap.py data/tokyo_3ldk_rent.csv "東京都 市区町村別" output/tokyo_heatmap.png
"""
import os
import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, cm
from matplotlib.colors import Normalize

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


def build(csv_path: str, title: str, out_path: str):
    df = pd.read_csv(csv_path)
    df = df.sort_values("rent_yen", ascending=True).reset_index(drop=True)
    avg = df["rent_yen"].mean()

    norm = Normalize(vmin=df["rent_yen"].min(), vmax=df["rent_yen"].max())
    colors = cm.YlOrRd(norm(df["rent_yen"].values))

    height = max(6, 0.32 * len(df) + 2)
    fig, ax = plt.subplots(figsize=(10, height))
    labels = df["municipality"].tolist()
    bars = ax.barh(labels, df["rent_yen"], color=colors, edgecolor="white", linewidth=0.5)
    for bar, v in zip(bars, df["rent_yen"]):
        ax.text(bar.get_width() + df["rent_yen"].max() * 0.006,
                bar.get_y() + bar.get_height() / 2,
                f"{v/10000:.1f}万", va="center", ha="left", fontsize=8)

    ax.axvline(avg, color="#333333", linestyle="--", linewidth=1)
    ax.text(avg, len(df) - 0.3, f" 平均 {avg/10000:.1f}万",
            color="#333333", fontsize=9, ha="left")

    ax.set_xlabel("3LDK 平均家賃 (円)")
    ax.set_title(f"{title} 3LDK平均家賃ヒートマップ（推計値）", fontsize=14, pad=12)
    ax.set_xlim(0, df["rent_yen"].max() * 1.16)
    ax.margins(y=0.004)
    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)

    # ランキングMarkdownも出力
    md = out_path.rsplit(".", 1)[0] + "_ranking.md"
    d2 = df.sort_values("rent_yen", ascending=False).reset_index(drop=True)
    with open(md, "w", encoding="utf-8") as f:
        f.write(f"# {title} 3LDK平均家賃ランキング（推計値）\n\n")
        f.write(f"- 平均: **{avg:,.0f}円** / 最高: {d2.iloc[0]['municipality']} "
                f"{d2.iloc[0]['rent_yen']:,}円 / 最低: {d2.iloc[-1]['municipality']} "
                f"{d2.iloc[-1]['rent_yen']:,}円\n\n")
        f.write("> ⚠️ 推計値。実測値へ差し替え可能。\n\n")
        f.write("| 順位 | 市区町村 | 平均家賃(円) |\n|---:|:--|---:|\n")
        for i, r in d2.iterrows():
            f.write(f"| {i+1} | {r['municipality']} | {r['rent_yen']:,} |\n")
    print("written:", out_path)
    print("written:", md)


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data/tokyo_3ldk_rent.csv"
    title = sys.argv[2] if len(sys.argv) > 2 else "東京都 市区町村別"
    out_path = sys.argv[3] if len(sys.argv) > 3 else "output/tokyo_heatmap.png"
    build(csv_path, title, out_path)
