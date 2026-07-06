#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
町名ごとの 3LDK家賃 バブルマップ生成スクリプト

町丁目の行政界ポリゴンはこの環境で取得できないため「塗り分け(コロプレス)」は不可。
代わりに、各町名の位置（緯度経度）に点を打ち、家賃で色・大きさを表す
**バブルマップ**（地理的な相場分布が見える地図型）を出力する。

入力CSVの列:
  town     : 町名（必須）
  lat, lon : 緯度・経度（必須, 概略で可）
  rent_yen : 3LDK平均家賃（円）← 実測値に差し替え可
  ward     : 区名（任意, ラベル補助）

使い方:
  python3 build_town_map.py data/sapporo_town_3ldk.csv "札幌市 町名別" output/sapporo_town_map.png
"""
import os
import sys
import math
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
    norm = Normalize(vmin=df["rent_yen"].min(), vmax=df["rent_yen"].max())
    cmap = cm.YlOrRd

    fig, ax = plt.subplots(figsize=(11, 10))
    # 緯度により経度1度の実距離が縮むため、アスペクト比を補正して地図の歪みを抑える
    lat0 = df["lat"].mean()
    ax.set_aspect(1.0 / math.cos(math.radians(lat0)))

    sizes = 300 + 900 * norm(df["rent_yen"].values)
    sc = ax.scatter(df["lon"], df["lat"], c=df["rent_yen"], cmap=cmap, norm=norm,
                    s=sizes, edgecolor="#555555", linewidth=0.6, alpha=0.9, zorder=3)

    for _, r in df.iterrows():
        ax.annotate(f"{r['town']}\n{r['rent_yen']/10000:.1f}万",
                    (r["lon"], r["lat"]), fontsize=7.5, ha="center", va="center",
                    zorder=4)

    cb = fig.colorbar(sc, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("3LDK 平均家賃 (円)")

    ax.set_title(f"{title} 3LDK平均家賃バブルマップ（推計値）", fontsize=14, pad=12)
    ax.set_xlabel("経度")
    ax.set_ylabel("緯度")
    ax.grid(True, linestyle=":", linewidth=0.5, color="#cccccc", zorder=0)
    ax.margins(0.08)
    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("written:", out_path)


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data/sapporo_town_3ldk.csv"
    title = sys.argv[2] if len(sys.argv) > 2 else "札幌市 町名別"
    out_path = sys.argv[3] if len(sys.argv) > 3 else "output/sapporo_town_map.png"
    build(csv_path, title, out_path)
