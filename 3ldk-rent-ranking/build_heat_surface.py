#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地点データ(緯度経度+家賃)から「地図上のヒートマップ(補間サーフェス)」を生成する。

行政界ポリゴンが無くても、地点をIDW(逆距離加重)補間して面で色を塗るため、
"ヒートマップを地図で" 表示できる。データの無い遠方はマスクして色を塗らない。

入力CSV列: town, lat, lon, rent_yen （ward任意）

使い方:
  python3 build_heat_surface.py data/sapporo_town_3ldk.csv "札幌市 町名別" output/sapporo_heatmap_map.png
"""
import os
import sys
import math
import numpy as np
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


def build(csv_path, title, out_path, grid=420, power=2.4, mask_dist=0.030):
    df = pd.read_csv(csv_path)
    lat0 = df["lat"].mean()
    kx = math.cos(math.radians(lat0))  # 経度方向の距離補正係数

    pad = 0.015
    lon_min, lon_max = df["lon"].min() - pad, df["lon"].max() + pad
    lat_min, lat_max = df["lat"].min() - pad, df["lat"].max() + pad
    gx = np.linspace(lon_min, lon_max, grid)
    gy = np.linspace(lat_min, lat_max, grid)
    GX, GY = np.meshgrid(gx, gy)

    plon = df["lon"].values
    plat = df["lat"].values
    pval = df["rent_yen"].values.astype(float)

    # IDW補間 + 最近傍距離マスク
    num = np.zeros_like(GX)
    den = np.zeros_like(GX)
    nearest = np.full(GX.shape, np.inf)
    for lo, la, v in zip(plon, plat, pval):
        d2 = ((GX - lo) * kx) ** 2 + (GY - la) ** 2
        d = np.sqrt(d2)
        nearest = np.minimum(nearest, d)
        w = 1.0 / np.power(d2 + 1e-9, power / 2.0)
        num += w * v
        den += w
    field = num / den
    field = np.ma.masked_where(nearest > mask_dist, field)

    norm = Normalize(vmin=pval.min(), vmax=pval.max())
    fig, ax = plt.subplots(figsize=(11, 10))
    ax.set_aspect(1.0 / kx)

    im = ax.imshow(field, origin="lower", extent=[lon_min, lon_max, lat_min, lat_max],
                   cmap=cm.YlOrRd, norm=norm, alpha=0.92, zorder=1, interpolation="bilinear")
    ax.scatter(plon, plat, c="#222222", s=14, zorder=3)
    for _, r in df.iterrows():
        ax.annotate(f"{r['town']} {r['rent_yen']/10000:.1f}万",
                    (r["lon"], r["lat"]), fontsize=7, ha="center", va="bottom",
                    xytext=(0, 4), textcoords="offset points", zorder=4,
                    color="#111111")

    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("3LDK 平均家賃 (円)")
    ax.set_title(f"{title} 3LDK平均家賃 地図ヒートマップ（推計値・IDW補間）", fontsize=13, pad=12)
    ax.set_xlabel("経度")
    ax.set_ylabel("緯度")
    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("written:", out_path)


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data/sapporo_town_3ldk.csv"
    title = sys.argv[2] if len(sys.argv) > 2 else "札幌市 町名別"
    out_path = sys.argv[3] if len(sys.argv) > 3 else "output/sapporo_heatmap_map.png"
    build(csv_path, title, out_path)
