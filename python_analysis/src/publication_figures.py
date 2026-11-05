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
REGION_NAME = {"YRD": "Yangtze River Delta", "GBA": "Greater Bay Area", "BTH": "Beijing–Tianjin–Hebei"}
COLORS = {"YRD": "#2F6F6D", "GBA": "#B96D52", "BTH": "#526F8C"}
NEUTRAL = "#68736F"
LIGHT = "#F0F3F1"

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

CITY_EN = {
    "上海市": "Shanghai", "丽水市": "Lishui", "亳州市": "Bozhou", "六安市": "Lu'an",
    "南京市": "Nanjing", "南通市": "Nantong", "台州市": "Taizhou (ZJ)", "合肥市": "Hefei",
    "嘉兴市": "Jiaxing", "宁波市": "Ningbo", "安庆市": "Anqing", "宣城市": "Xuancheng",
    "宿州市": "Suzhou (AH)", "宿迁市": "Suqian", "常州市": "Changzhou", "徐州市": "Xuzhou",
    "扬州市": "Yangzhou", "无锡市": "Wuxi", "杭州市": "Hangzhou", "池州市": "Chizhou",
    "泰州市": "Taizhou (JS)", "淮北市": "Huaibei", "淮南市": "Huainan", "淮安市": "Huai'an",
    "温州市": "Wenzhou", "湖州市": "Huzhou", "滁州市": "Chuzhou", "盐城市": "Yancheng",
    "绍兴市": "Shaoxing", "舟山市": "Zhoushan", "芜湖市": "Wuhu", "苏州市": "Suzhou (JS)",
    "蚌埠市": "Bengbu", "衢州市": "Quzhou", "连云港市": "Lianyungang", "金华市": "Jinhua",
    "铜陵市": "Tongling", "镇江市": "Zhenjiang", "阜阳市": "Fuyang", "马鞍山市": "Ma'anshan",
    "黄山市": "Huangshan", "东莞市": "Dongguan", "中山市": "Zhongshan", "佛山市": "Foshan",
    "广州市": "Guangzhou", "惠州市": "Huizhou", "江门市": "Jiangmen", "深圳市": "Shenzhen",
    "珠海市": "Zhuhai", "肇庆市": "Zhaoqing", "香港": "Hong Kong", "保定市": "Baoding",
    "北京市": "Beijing", "唐山市": "Tangshan", "天津市": "Tianjin", "廊坊市": "Langfang",
    "张家口市": "Zhangjiakou", "承德市": "Chengde", "沧州市": "Cangzhou", "石家庄市": "Shijiazhuang",
    "秦皇岛市": "Qinhuangdao", "衡水市": "Hengshui", "邢台市": "Xingtai", "邯郸市": "Handan",
}


# Figure 1: an executive overview combining the most decision-relevant evidence.
fig = plt.figure(figsize=(15.2, 10.2))
gs = fig.add_gridspec(3, 6, height_ratios=[0.72, 2.3, 2.0], hspace=0.58, wspace=0.65)
fig.suptitle("Wetland vegetation cover across three urban regions", fontsize=20, fontweight="bold", x=0.06, ha="left", y=0.98)
fig.text(0.06, 0.946, "Reviewed Stage 5 results  ·  30 m effective-area weighting  ·  1985–2020", fontsize=10.5, color=NEUTRAL)

kpis = [
    ("36", "annual observations", "shared regional time span"),
    ("64", "cities", "eight temporal nodes"),
    ("30 m", "reporting scale", "native Landsat pixels"),
    ("75.0%", "direction agreement", "endpoint sensitivity screen"),
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
    ax_ts.plot(d.year, d.fvc_mean_area_weighted, color=COLORS[r], lw=2.2, label=REGION_NAME[r])
    ax_ts.scatter(d.year, d.fvc_mean_area_weighted, color=COLORS[r], s=10, zorder=3)
ax_ts.axvline(2013, color="#111827", lw=1, ls="--")
ax_ts.text(2013.25, ax_ts.get_ylim()[1] * 0.96, "sensor transition", fontsize=8.5, color=NEUTRAL, va="top")
ax_ts.set_title("Annual regional FVC", loc="left", fontsize=13, fontweight="bold")
ax_ts.set_xlabel("Year")
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
                     label="Before 2013" if j == 0 else "2013 onward")
    for b, v in zip(bars, vals):
        ax_tr.text(b.get_x() + b.get_width()/2, v + (0.3 if v >= 0 else -0.65), f"{v:+.1f}", ha="center", fontsize=8)
ax_tr.axhline(0, color="#4B5563", lw=.8)
ax_tr.set_xticks(x, REGIONS)
ax_tr.set_ylabel("Sen slope ×10⁻³ yr⁻¹")
ax_tr.set_title("Segmented regional trends", loc="left", fontsize=13, fontweight="bold")
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
ax_box.set_ylabel("City-level wetland FVC")
ax_box.set_title("Variation among cities", loc="left", fontsize=13, fontweight="bold")
ax_box.grid(axis="y", alpha=.18)
for r in REGIONS:
    ax_box.plot([], [], color=COLORS[r], lw=7, alpha=.45, label=REGION_NAME[r])
ax_box.legend(frameon=False, ncol=3, fontsize=8)

ax_sc = fig.add_subplot(gs[2, 4:])
valid_scale = scale.dropna(subset=["fvc_mean_area_weighted"])
base = valid_scale[valid_scale.scale_m == 30][["region", "year", "fvc_mean_area_weighted"]].rename(columns={"fvc_mean_area_weighted": "fvc30"})
merged = valid_scale.merge(base, on=["region", "year"])
merged["delta"] = merged.fvc_mean_area_weighted - merged.fvc30
for r in REGIONS:
    d = merged[(merged.region == r) & (merged.scale_m != 30)]
    ax_sc.scatter(d.scale_m, d.delta, s=34, alpha=.72, color=COLORS[r], label=REGION_NAME[r])
ax_sc.axhline(0, color="#4B5563", lw=.8)
ax_sc.set_xticks([100, 250, 500])
ax_sc.set_xlabel("Analysis scale (m)")
ax_sc.set_ylabel("FVC difference from 30 m")
ax_sc.set_title("Scale sensitivity", loc="left", fontsize=13, fontweight="bold")
ax_sc.grid(axis="y", alpha=.18)
ax_sc.legend(frameon=False, fontsize=8)

fig.text(0.06, 0.025, "Solid trend bars indicate TFPW Mann–Kendall p < 0.05; hatched bars are not significant. GBA remains missing in 1985.", fontsize=9, color=NEUTRAL)
save(fig, "fvc_overview.png")


def aggregate_transition(region: str, interval: str):
    d = pd.read_csv(TRANS / f"{region}_WetlandTransitionStructure.csv")
    d = d[d.interval == interval].copy()
    d["name"] = d.converted_class_name
    out = {}
    for direction in ["in", "out"]:
        s = d[d.direction == direction].groupby("name", as_index=False).area_km2.sum().sort_values("area_km2", ascending=False)
        # Reset retained indices before appending "Other". Otherwise
        # top.loc[len(top)] may overwrite a row whose old index equals the new
        # length, understating the Sankey totals.
        top = s.head(5).copy().reset_index(drop=True)
        other = s.iloc[5:].area_km2.sum()
        if other > 0:
            top.loc[len(top)] = ["Other", other]
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
    palette = ["#557A95", "#C89A58", "#6D9274", "#B96D6A", "#8D7897", "#AAA7A1"]
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
    ax.text(.50, .50, "Wetland", rotation=90, ha="center", va="center", color="white", fontweight="bold")
    ax.text(.10, .98, "Sources of gain", ha="center", va="top", fontsize=9, fontweight="bold")
    ax.text(.90, .98, "Destinations of loss", ha="center", va="top", fontsize=9, fontweight="bold")
    ax.text(.50, .015, f"Gain {total_in:,.0f} km²   ·   Loss {total_out:,.0f} km²", ha="center", fontsize=8, color=NEUTRAL)
    ax.set_title(REGION_NAME[region], fontsize=13, fontweight="bold", color=COLORS[region], pad=8)
    ax.set_xlim(-.08, 1.08); ax.set_ylim(0, 1); ax.axis("off")


fig, axes = plt.subplots(1, 3, figsize=(17, 7.3))
for ax, r in zip(axes, REGIONS):
    draw_sankey(ax, r)
fig.suptitle("Wetland gains and losses recorded from 1995 to 2000", fontsize=18, fontweight="bold", y=.98)
fig.text(.5, .025, "Ribbon width represents area recorded by the land-cover product. This interval crosses a product time boundary and is not direct evidence of ecological recovery.", ha="center", fontsize=9, color=NEUTRAL)
fig.tight_layout(rect=(0, .05, 1, .95), w_pad=1.5)
save(fig, "wetland_transition_1995_2000.png")


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
    ax.set_yticks(y, pick.city.map(CITY_EN).fillna(pick.city))
    ax.set_title(REGION_NAME[r], fontweight="bold", fontsize=13, color=COLORS[r])
    ax.grid(axis="x", alpha=.18)
    ax.set_xlabel("Change in FVC")
axes[0].set_ylabel("City")
fig.suptitle("Cities with the largest observed changes in FVC", fontsize=18, fontweight="bold", y=.98)
fig.text(.5, .025, "Only cities with at least 50% valid baseline coverage are included. Baseline: 1985 for YRD/BTH and 1990 for GBA.", ha="center", fontsize=9, color=NEUTRAL)
fig.tight_layout(rect=(0, .05, 1, .95), w_pad=2.0)
save(fig, "city_fvc_change_ranking.png")


print(f"Generated publication figures in {OUT}")
