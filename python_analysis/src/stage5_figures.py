"""Create reader-oriented Stage 5 figures for the enriched 30 m report."""
import csv
import math
import os
from pathlib import Path
from statistics import mean, pstdev

os.environ.setdefault("MPLCONFIGDIR", "/tmp/srdp-enriched-mpl-cache")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

ROOT = Path(__file__).resolve().parents[2]
IN = ROOT / "outputs" / "stage5_final"
OUT = ROOT / "docs" / "assets" / "stage5"
OUT.mkdir(parents=True, exist_ok=True)

REGIONS = ["YRD", "GBA", "BTH"]
CN = {"YRD": "长三角", "GBA": "粤港澳大湾区", "BTH": "京津冀"}
COLORS = {"YRD": "#2878B5", "GBA": "#D65F32", "BTH": "#3A9D5D"}

plt.rcParams.update({
    "font.sans-serif": ["Arial Unicode MS", "PingFang SC", "Hiragino Sans GB", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def num(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def save(fig, name):
    fig.savefig(OUT / name, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


regional = {}
for region in REGIONS:
    rows = read(IN / f"Stage5_Final_Regional30m_36Years_{region}.csv")
    regional[region] = sorted(rows, key=lambda r: int(float(r["year"])))

city = read(IN / "Stage5_QA_City_FVC_8Nodes_30m.csv")
endpoint = read(IN / "Stage5_QA_Endpoint_Percentiles.csv")

# 1. Annual FVC, wetland area, and observation coverage in one reader-oriented dashboard.
fig, axes = plt.subplots(3, 3, figsize=(13.2, 9.2), sharex="col")
for i, region in enumerate(REGIONS):
    rr = regional[region]
    years = [int(float(r["year"])) for r in rr]
    fvc = [num(r["fvc_mean_area_weighted"]) for r in rr]
    area = [num(r["wetland_area_km2"]) for r in rr]
    valid = [num(r["valid_fraction"]) for r in rr]
    scenes = [num(r["scenes"]) for r in rr]

    ax = axes[i, 0]
    ax.plot(years, fvc, color=COLORS[region], lw=1.6, marker="o", ms=2.8)
    ax.axvline(2013, color="#777777", ls="--", lw=1)
    ax.set_ylim(0, max(0.34, max(v for v in fvc if v is not None) + .03))
    ax.set_ylabel(f"{CN[region]}\nFVC", fontweight="bold")
    ax.grid(axis="y", alpha=.2)
    if region == "GBA":
        ax.annotate("1985缺测", (1985, .015), fontsize=8, color="#666666")

    ax = axes[i, 1]
    ax.plot(years, area, color="#4C78A8", lw=1.5)
    ax.fill_between(years, area, color="#4C78A8", alpha=.12)
    ax.axvline(2000, color="#B279A2", ls=":", lw=1)
    ax.set_ylabel("湿地面积 km²")
    ax.grid(axis="y", alpha=.2)

    ax = axes[i, 2]
    ax.plot(years, [100 * x if x is not None else None for x in valid], color="#59A14F", lw=1.5, label="有效覆盖")
    ax.set_ylim(0, 105)
    ax.set_ylabel("有效覆盖 %")
    ax.grid(axis="y", alpha=.2)
    ax2 = ax.twinx()
    ax2.bar(years, scenes, color="#9C9C9C", width=.75, alpha=.22, label="场景数")
    ax2.set_ylabel("场景数", color="#666666")
for j, title in enumerate(["植被覆盖度", "分类湿地面积", "观测覆盖与场景数"]):
    axes[0, j].set_title(title, fontweight="bold")
for ax in axes[-1, :]:
    ax.set_xlabel("年份")
fig.suptitle("三大城市群年度结果与数据基础总览", fontsize=15, fontweight="bold", y=.995)
fig.text(.5, .01, "虚线：2013年传感器节点；紫色点线：2000年分类产品时间组织边界", ha="center", fontsize=9, color="#555555")
fig.tight_layout(rect=(0, .03, 1, .97))
save(fig, "regional_fvc_area_coverage.png")

# 2. Standardized annual anomalies make within-region timing comparable without ranking absolute FVC.
years_all = list(range(1985, 2021))
matrix = []
for region in REGIONS:
    vals = {int(float(r["year"])): num(r["fvc_mean_area_weighted"]) for r in regional[region]}
    observed = [v for v in vals.values() if v is not None]
    mu, sd = mean(observed), pstdev(observed)
    matrix.append([(vals.get(y) - mu) / sd if vals.get(y) is not None and sd else math.nan for y in years_all])
fig, ax = plt.subplots(figsize=(12.5, 3.3))
im = ax.imshow(matrix, aspect="auto", cmap="RdBu_r", norm=TwoSlopeNorm(vmin=-2.2, vcenter=0, vmax=2.2))
ax.set_yticks(range(3), [CN[r] for r in REGIONS])
ax.set_xticks(range(0, len(years_all), 5), [years_all[i] for i in range(0, len(years_all), 5)])
ax.axvline(2013 - 1985 - .5, color="#222222", ls="--", lw=1.2)
ax.set_title("区域内部年度FVC标准化异常", fontweight="bold")
ax.set_xlabel("年份")
cbar = fig.colorbar(im, ax=ax, fraction=.025, pad=.02)
cbar.set_label("相对本区域长期均值的标准差")
fig.text(.5, .01, "红色表示高于本区域长期均值，蓝色表示低于均值；用于比较变化时序，不用于三地绝对值排名", ha="center", fontsize=9)
fig.tight_layout(rect=(0, .06, 1, 1))
save(fig, "standardized_fvc_anomaly.png")

# 3. Segmented Sen slopes, with significance conveyed by fill.
trend_rows = read(IN / "analysis" / "regional_trends_mk_tfpw.csv")
periods = ["1985-2012", "2013-2020"]
fig, ax = plt.subplots(figsize=(10.5, 4.8))
positions = []
labels = []
for i, region in enumerate(REGIONS):
    for k, period in enumerate(periods):
        row = next(r for r in trend_rows if r["region"] == region and r["period"] == period)
        slope = float(row["sen_slope"]) * 1000
        significant = float(row["tfpw_p"]) < .05
        x = i * 2.5 + k
        positions.append(x)
        labels.append(("2013前" if k == 0 else "2013后"))
        ax.bar(x, slope, width=.72, color=COLORS[region] if significant else "white",
               edgecolor=COLORS[region], linewidth=1.8, hatch=None if significant else "//")
        ax.text(x, slope + (.35 if slope >= 0 else -.55), f"{slope:+.2f}", ha="center", va="bottom" if slope >= 0 else "top", fontsize=9)
ax.axhline(0, color="#555555", lw=.9)
ax.set_xticks(positions, labels)
for i, region in enumerate(REGIONS):
    ax.text(i * 2.5 + .5, ax.get_ylim()[0] * .88, CN[region], ha="center", fontweight="bold", color=COLORS[region])
ax.set_ylabel("Sen斜率 ×10⁻³ FVC/年")
ax.set_title("2013年前后分段趋势及显著性", fontweight="bold")
ax.grid(axis="y", alpha=.2)
fig.text(.5, .01, "实色：TFPW Mann–Kendall p<0.05；斜线空心：未达显著；GBA前段按1986—2012有效年份计算", ha="center", fontsize=9)
fig.tight_layout(rect=(0, .07, 1, 1))
save(fig, "segmented_sen_trends.png")

# 4. City distributions across eight nodes, avoiding an unreadable 64-line spaghetti chart.
node_years = sorted({int(float(r["year"])) for r in city})
fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.6), sharey=True)
for ax, region in zip(axes, REGIONS):
    data = []
    labels = []
    for year in node_years:
        vals = [num(r["fvc_mean_area_weighted"]) for r in city if r["region"] == region and int(float(r["year"])) == year and num(r["fvc_mean_area_weighted"]) is not None]
        data.append(vals)
        labels.append(str(year))
    bp = ax.boxplot(data, patch_artist=True, showfliers=False, medianprops={"color": "#222222", "linewidth": 1.4})
    for box in bp["boxes"]:
        box.set(facecolor=COLORS[region], alpha=.36, edgecolor=COLORS[region])
    ax.set_title(f"{CN[region]} 城市分布", fontweight="bold")
    ax.set_xticks(range(1, len(labels) + 1), labels, rotation=45)
    ax.grid(axis="y", alpha=.2)
axes[0].set_ylabel("城市湿地FVC")
fig.suptitle("八个时间节点的城市FVC分布", fontweight="bold")
fig.text(.5, .01, "箱体表示城市间四分位范围，中线为中位数；GBA 1985无有效结果", ha="center", fontsize=9)
fig.tight_layout(rect=(0, .06, 1, .94))
save(fig, "city_fvc_node_boxplots.png")

# 5. Named city changes: top and bottom FVC deltas after baseline QC.
idx = {(r["region"], r["name"], int(float(r["year"]))): r for r in city}
changes = []
for region in REGIONS:
    baseline = 1990 if region == "GBA" else 1985
    for name in sorted({r["name"] for r in city if r["region"] == region}):
        a, b = idx.get((region, name, baseline)), idx.get((region, name, 2020))
        if not a or not b or (num(a["valid_fraction"]) or 0) < .5:
            continue
        fa, fb = num(a["fvc_mean_area_weighted"]), num(b["fvc_mean_area_weighted"])
        if fa is not None and fb is not None:
            changes.append((fb - fa, name, region, baseline))
selected = sorted(changes)[:8] + sorted(changes)[-8:]
selected = sorted(selected, key=lambda x: x[0])
fig, ax = plt.subplots(figsize=(10.5, 7.2))
y = list(range(len(selected)))
ax.hlines(y, 0, [x[0] for x in selected], color=[COLORS[x[2]] for x in selected], lw=2)
ax.scatter([x[0] for x in selected], y, c=[COLORS[x[2]] for x in selected], s=48, zorder=3)
ax.axvline(0, color="#555555", lw=.9)
ax.set_yticks(y, [f"{x[1]}  {CN[x[2]]}" for x in selected])
ax.set_xlabel("FVC变化（基准年—2020）")
ax.set_title("城市FVC变化幅度最大的正负样本", fontweight="bold")
ax.grid(axis="x", alpha=.2)
fig.text(.5, .01, "仅纳入基准年有效覆盖≥50%的城市；YRD/BTH基准为1985，GBA基准为1990；用于定位复核对象，不代表显著性排名", ha="center", fontsize=9)
fig.tight_layout(rect=(0, .05, 1, 1))
save(fig, "city_fvc_change_lollipop.png")

# 6. Endpoint offsets from annual percentiles, shown directly as diagnostic gaps.
fig, axes = plt.subplots(2, 1, figsize=(12.2, 6.2), sharex=True)
for region in REGIONS:
    rr = sorted([r for r in endpoint if r["region"] == region], key=lambda r: int(float(r["year"])))
    years = [int(float(r["year"])) for r in rr]
    soil_gap = [(num(r["fixed_soil"]) - num(r["p05"])) if num(r["p05"]) is not None else None for r in rr]
    veg_gap = [(num(r["fixed_veg"]) - num(r["p95"])) if num(r["p95"]) is not None else None for r in rr]
    axes[0].plot(years, soil_gap, color=COLORS[region], lw=1.5, marker="o", ms=2.7, label=CN[region])
    axes[1].plot(years, veg_gap, color=COLORS[region], lw=1.5, marker="o", ms=2.7, label=CN[region])
for ax, label in zip(axes, ["固定土壤端元 − 年度P5", "固定植被端元 − 年度P95"]):
    ax.axhline(0, color="#555555", lw=.9)
    ax.axvline(2013, color="#777777", ls="--", lw=1)
    ax.set_ylabel(label)
    ax.grid(axis="y", alpha=.2)
axes[0].legend(ncol=3, frameon=False)
axes[1].set_xlabel("年份")
fig.suptitle("固定端元相对年度NDVI分布的偏离幅度", fontweight="bold")
fig.text(.5, .01, "正值表示固定端元高于相应年度分位；这是内部诊断，不替代外部端元验证", ha="center", fontsize=9)
fig.tight_layout(rect=(0, .05, 1, .96))
save(fig, "endpoint_offset.png")

manifest = [
    ("regional_fvc_area_coverage.png", "区域FVC、湿地面积、有效覆盖与场景数"),
    ("standardized_fvc_anomaly.png", "区域内部年度异常"),
    ("segmented_sen_trends.png", "2013前后分段趋势"),
    ("city_fvc_node_boxplots.png", "城市节点分布"),
    ("city_fvc_change_lollipop.png", "重点城市定位"),
    ("endpoint_offset.png", "端元偏离诊断"),
]
with (OUT / "figure_manifest.csv").open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["file", "purpose"])
    w.writerows(manifest)
print(f"Generated {len(manifest)} enriched figures in {OUT}")
