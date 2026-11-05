"""Build publication-oriented Stage 5 visualizations from reviewed CSV outputs."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/wetland-publication-mpl")

import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch, Rectangle
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "outputs" / "stage5_final"
TRANS = DATA / "transition"
TREND = DATA / "Stage5_30m区域趋势_MK_TFPW.csv"
CITY_AGREE = DATA / "城市趋势_一致性汇总.csv"
OUT = ROOT / "docs" / "assets" / "publication"
OUT.mkdir(parents=True, exist_ok=True)

REGIONS = ["YRD", "GBA", "BTH"]
CN = {"YRD": "长三角", "GBA": "粤港澳大湾区", "BTH": "京津冀"}
COLORS = {"YRD": "#2A9D8F", "GBA": "#E76F51", "BTH": "#457B9D"}
NEUTRAL = "#6B7280"
LIGHT = "#EEF2F4"

plt.rcParams.update({
    "font.sans-serif": ["Arial Unicode MS", "PingFang SC", "Hiragino Sans GB", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "font.size": 10,
})


def save(fig, name: str):
    fig.savefig(OUT / name, dpi=320, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / name.replace(".png", ".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def read_regional():
    return {
        r: pd.read_csv(DATA / f"Stage5_Final_Regional30m_36Years_{r}.csv")
        for r in REGIONS
    }


regional = read_regional()
city = pd.read_csv(DATA / "Stage5_QA_City_FVC_8Nodes_30m.csv")
scale = pd.read_csv(DATA / "Stage5_QA_Scale_30_100_250_500m.csv")
trend = pd.read_csv(TREND)
agreement = pd.read_csv(CITY_AGREE)


# Figure 1: an executive overview combining the most decision-relevant evidence.
fig = plt.figure(figsize=(15.2, 10.2))
gs = fig.add_gridspec(3, 6, height_ratios=[0.72, 2.3, 2.0], hspace=0.58, wspace=0.65)
fig.suptitle("三大城市群湿地植被覆盖变化总览", fontsize=20, fontweight="bold", x=0.06, ha="left", y=0.98)
fig.text(0.06, 0.946, "Stage 5  ·  30 m有效面积加权  ·  1985—2020", fontsize=10.5, color=NEUTRAL)

kpis = [
    ("36", "年度序列", "三地统一年度统计"),
    ("64", "城市样本", "8个时间节点"),
    ("30 m", "正式尺度", "原生Landsat像元"),
    ("75.0%", "端元方向一致率", "50%覆盖质控情景"),
]
top = gs[0, :].subgridspec(1, 4, wspace=.32)
for i, (value, label, sub) in enumerate(kpis):
    ax = fig.add_subplot(top[0, i])
    ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=LIGHT, edgecolor="none"))
    ax.text(0.06, 0.62, value, transform=ax.transAxes, fontsize=23, fontweight="bold", color="#183B56")
    ax.text(0.06, 0.33, label, transform=ax.transAxes, fontsize=10.5, fontweight="bold")
    ax.text(0.06, 0.12, sub, transform=ax.transAxes, fontsize=8.5, color=NEUTRAL)

ax_ts = fig.add_subplot(gs[1, :4])
for r in REGIONS:
    d = regional[r].sort_values("year")
    ax_ts.plot(d.year, d.fvc_mean_area_weighted, color=COLORS[r], lw=2.2, label=CN[r])
    ax_ts.scatter(d.year, d.fvc_mean_area_weighted, color=COLORS[r], s=10, zorder=3)
ax_ts.axvline(2013, color="#111827", lw=1, ls="--")
ax_ts.text(2013.25, ax_ts.get_ylim()[1] * 0.96, "传感器节点", fontsize=8.5, color=NEUTRAL, va="top")
ax_ts.set_title("区域年度FVC", loc="left", fontsize=13, fontweight="bold")
ax_ts.set_xlabel("年份")
ax_ts.set_ylabel("FVC")
ax_ts.grid(axis="y", alpha=0.18)
ax_ts.legend(frameon=False, ncol=3, loc="upper left")

ax_tr = fig.add_subplot(gs[1, 4:])
periods = ["1985-2012", "2013-2020"]
x = np.arange(3)
w = 0.32
for j, period in enumerate(periods):
    vals = []
    sig = []
    for r in REGIONS:
        row = trend[(trend.region == r) & (trend.period == period)].iloc[0]
        vals.append(row.sen_slope * 1000)
        sig.append(row.tfpw_p < 0.05)
    bars = ax_tr.bar(x + (j - .5) * w, vals, width=w, color=[COLORS[r] if s else "white" for r, s in zip(REGIONS, sig)],
                     edgecolor=[COLORS[r] for r in REGIONS], linewidth=1.6, hatch=[None if s else "///" for s in sig],
                     label="2013年前" if j == 0 else "2013年后")
    for b, v in zip(bars, vals):
        ax_tr.text(b.get_x() + b.get_width()/2, v + (0.3 if v >= 0 else -0.65), f"{v:+.1f}", ha="center", fontsize=8)
ax_tr.axhline(0, color="#4B5563", lw=.8)
ax_tr.set_xticks(x, [CN[r] for r in REGIONS])
ax_tr.set_ylabel("Sen斜率 ×10⁻³/年")
ax_tr.set_title("2013年前后分段趋势", loc="left", fontsize=13, fontweight="bold")
ax_tr.legend(frameon=False, fontsize=8)
ax_tr.grid(axis="y", alpha=.18)

ax_box = fig.add_subplot(gs[2, :4])
years = sorted(city.year.unique())
positions, data, box_colors = [], [], []
offsets = [-0.24, 0, 0.24]
for yi, year in enumerate(years):
    for ri, r in enumerate(REGIONS):
        vals = city[(city.region == r) & (city.year == year)].fvc_mean_area_weighted.dropna().values
        positions.append(yi + offsets[ri])
        data.append(vals)
        box_colors.append(COLORS[r])
bp = ax_box.boxplot(data, positions=positions, widths=.19, patch_artist=True, showfliers=False,
                    medianprops={"color": "#111827", "linewidth": 1})
for box, c in zip(bp["boxes"], box_colors):
    box.set_facecolor(c); box.set_alpha(.42); box.set_edgecolor(c)
ax_box.set_xticks(range(len(years)), years, rotation=35)
ax_box.set_ylabel("城市湿地FVC")
ax_box.set_title("城市间差异与时间变化", loc="left", fontsize=13, fontweight="bold")
ax_box.grid(axis="y", alpha=.18)
for r in REGIONS:
    ax_box.plot([], [], color=COLORS[r], lw=7, alpha=.45, label=CN[r])
ax_box.legend(frameon=False, ncol=3, fontsize=8)

ax_sc = fig.add_subplot(gs[2, 4:])
valid_scale = scale.dropna(subset=["fvc_mean_area_weighted"])
base = valid_scale[valid_scale.scale_m == 30][["region", "year", "fvc_mean_area_weighted"]].rename(columns={"fvc_mean_area_weighted": "fvc30"})
merged = valid_scale.merge(base, on=["region", "year"])
merged["delta"] = merged.fvc_mean_area_weighted - merged.fvc30
for r in REGIONS:
    d = merged[(merged.region == r) & (merged.scale_m != 30)]
    ax_sc.scatter(d.scale_m, d.delta, s=34, alpha=.72, color=COLORS[r], label=CN[r])
ax_sc.axhline(0, color="#4B5563", lw=.8)
ax_sc.set_xticks([100, 250, 500])
ax_sc.set_xlabel("统计尺度（m）")
ax_sc.set_ylabel("相对30 m的FVC差异")
ax_sc.set_title("尺度变化造成的偏差", loc="left", fontsize=13, fontweight="bold")
ax_sc.grid(axis="y", alpha=.18)
ax_sc.legend(frameon=False, fontsize=8)

fig.text(0.06, 0.025, "注：实色趋势柱表示TFPW Mann–Kendall p<0.05；斜线空心柱表示未达到显著。GBA 1985保持缺测。", fontsize=9, color=NEUTRAL)
save(fig, "图A_三大城市群FVC综合总览.png")


def aggregate_transition(region: str, interval: str):
    d = pd.read_csv(TRANS / f"{region}_WetlandTransitionStructure.csv")
    d = d[d.interval == interval].copy()
    d["name"] = d.converted_class_name.replace({
        "Water Body": "水体", "Irrigated Cropland": "灌溉耕地", "Impervious Surface": "建设用地",
        "Rainfed Cropland": "旱地", "Herbaceous Cover Cropland": "草本覆盖耕地", "Grassland": "草地",
        "Bare Land": "裸地", "Unconsolidated Bare Land": "松散裸地", "Sparse Vegetation": "稀疏植被",
        "Shrubland": "灌丛", "Evergreen Shrubland": "常绿灌丛", "Lichens and Mosses": "地衣与苔藓",
        "Open Evergreen Broadleaved Forest": "疏林常绿阔叶林", "Closed Evergreen Broadleaved Forest": "郁闭常绿阔叶林",
        "Open Deciduous Broadleaved Forest": "疏林落叶阔叶林", "Closed Deciduous Broadleaved Forest": "郁闭落叶阔叶林",
        "Open Evergreen Needle-Leaved Forest": "疏林常绿针叶林", "Closed Evergreen Needle-Leaved Forest": "郁闭常绿针叶林",
        "Open Deciduous Needle-Leaved Forest": "疏林落叶针叶林", "Closed Deciduous Needle-Leaved Forest": "郁闭落叶针叶林",
        "Open Mixed Leaf Forest": "疏林针阔混交林", "Unknown": "未分类",
    })
    out = {}
    for direction in ["in", "out"]:
        s = d[d.direction == direction].groupby("name", as_index=False).area_km2.sum().sort_values("area_km2", ascending=False)
        # Reset the retained source indices before appending “其他”. Otherwise
        # top.loc[len(top)] may overwrite a row whose old index equals the new
        # length, understating the Sankey totals.
        top = s.head(5).copy().reset_index(drop=True)
        other = s.iloc[5:].area_km2.sum()
        if other > 0:
            top.loc[len(top)] = ["其他", other]
        out[direction] = top
    return out


def ribbon(ax, x0, y0a, y0b, x1, y1a, y1b, color, alpha=.64):
    c = (x1 - x0) * .48
    verts = [(x0, y0a), (x0+c, y0a), (x1-c, y1a), (x1, y1a),
             (x1, y1b), (x1-c, y1b), (x0+c, y0b), (x0, y0b), (x0, y0a)]
    codes = [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
             MplPath.LINETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4, MplPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MplPath(verts, codes), facecolor=color, edgecolor="none", alpha=alpha))


def draw_sankey(ax, region: str, interval="1995-2000"):
    flows = aggregate_transition(region, interval)
    incoming, outgoing = flows["in"], flows["out"]
    total_in, total_out = incoming.area_km2.sum(), outgoing.area_km2.sum()
    palette = ["#4C78A8", "#F2A541", "#59A14F", "#E15759", "#B07AA1", "#BAB0AC"]
    gap = .018
    def stack(df, bottom=.08, height=.84):
        total = df.area_km2.sum()
        usable = height - gap * (len(df)-1)
        cur = bottom
        slots = []
        for _, row in df.iterrows():
            h = usable * row.area_km2 / total if total else 0
            slots.append((cur, cur+h, row))
            cur += h + gap
        return slots
    left = stack(incoming)
    right = stack(outgoing)
    center_left = stack(incoming, .08, .84)
    center_right = stack(outgoing, .08, .84)
    for i, ((ya, yb, row), (ca, cb, _)) in enumerate(zip(left, center_left)):
        ribbon(ax, .13, ya, yb, .47, ca, cb, palette[i % len(palette)])
        ax.add_patch(Rectangle((.08, ya), .05, yb-ya, color=palette[i % len(palette)], alpha=.9))
        ax.text(.065, (ya+yb)/2, f"{row['name']}  {row.area_km2:,.0f}", ha="right", va="center", fontsize=7.5)
    for i, ((ca, cb, _), (ya, yb, row)) in enumerate(zip(center_right, right)):
        ribbon(ax, .53, ca, cb, .87, ya, yb, palette[i % len(palette)])
        ax.add_patch(Rectangle((.87, ya), .05, yb-ya, color=palette[i % len(palette)], alpha=.9))
        ax.text(.935, (ya+yb)/2, f"{row['name']}  {row.area_km2:,.0f}", ha="left", va="center", fontsize=7.5)
    ax.add_patch(Rectangle((.47, .08), .06, .84, color=COLORS[region], alpha=.95))
    ax.text(.50, .50, "湿地", rotation=90, ha="center", va="center", color="white", fontweight="bold")
    ax.text(.10, .98, "转入来源", ha="center", va="top", fontsize=9, fontweight="bold")
    ax.text(.90, .98, "转出去向", ha="center", va="top", fontsize=9, fontweight="bold")
    ax.text(.50, .015, f"转入 {total_in:,.0f} km²   ·   转出 {total_out:,.0f} km²", ha="center", fontsize=8, color=NEUTRAL)
    ax.set_title(CN[region], fontsize=13, fontweight="bold", color=COLORS[region], pad=8)
    ax.set_xlim(-.08, 1.08); ax.set_ylim(0, 1); ax.axis("off")


fig, axes = plt.subplots(1, 3, figsize=(17, 7.3))
for ax, r in zip(axes, REGIONS):
    draw_sankey(ax, r)
fig.suptitle("1995—2000年湿地转入来源与转出去向", fontsize=18, fontweight="bold", y=.98)
fig.text(.5, .025, "流带宽度表示分类产品记录的面积；该时期跨越产品时间组织边界，图示用于描述转化结构，不单独解释为生态恢复。", ha="center", fontsize=9, color=NEUTRAL)
fig.tight_layout(rect=(0, .05, 1, .95), w_pad=1.5)
save(fig, "图B_1995_2000湿地转化桑基图.png")


# Figure 3: publication-style city change ranking, balanced by region.
detail = pd.read_csv(DATA / "表_Stage5城市面积FVC变化明细_qc50.csv")
fig, axes = plt.subplots(1, 3, figsize=(15, 8), sharex=True)
for ax, r in zip(axes, REGIONS):
    d = detail[(detail.region == r) & (detail.included_qc50 == True)].sort_values("delta_fvc")
    pick = pd.concat([d.head(6), d.tail(6)]).drop_duplicates().sort_values("delta_fvc")
    y = np.arange(len(pick))
    vals = pick.delta_fvc.values
    ax.hlines(y, 0, vals, color=np.where(vals >= 0, COLORS[r], "#C44536"), lw=2.5, alpha=.85)
    ax.scatter(vals, y, c=np.where(vals >= 0, COLORS[r], "#C44536"), s=52, zorder=3, edgecolor="white", linewidth=.5)
    ax.axvline(0, color="#374151", lw=.8)
    ax.set_yticks(y, pick.city)
    ax.set_title(CN[r], fontweight="bold", fontsize=13, color=COLORS[r])
    ax.grid(axis="x", alpha=.18)
    ax.set_xlabel("FVC变化")
axes[0].set_ylabel("城市")
fig.suptitle("城市FVC变化幅度较大的样本", fontsize=18, fontweight="bold", y=.98)
fig.text(.5, .025, "仅纳入基准年有效覆盖率≥50%的城市；长三角和京津冀基准为1985年，粤港澳大湾区基准为1990年。", ha="center", fontsize=9, color=NEUTRAL)
fig.tight_layout(rect=(0, .05, 1, .95), w_pad=2.0)
save(fig, "图C_城市FVC变化排名.png")


print(f"Generated publication figures in {OUT}")
