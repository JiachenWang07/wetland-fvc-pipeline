"""Render a continuous-value FVC map from a GeoTIFF display export.

The input is expected to contain FVC in the range 0–1 and GeoTIFF model-pixel
scale/tie-point tags. The script deliberately does not classify the values.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, PowerNorm
import numpy as np
from PIL import Image


PALETTE = ["#F2EFE9", "#D5DDD3", "#A9C4B6", "#6D9E8B", "#326C61", "#123B36"]
REGION_NAMES = {
    "YRD": "Yangtze River Delta",
    "GBA": "Greater Bay Area",
    "BTH": "Beijing–Tianjin–Hebei",
}


def load_geotiff(path: Path):
    image = Image.open(path)
    values = np.asarray(image, dtype=np.float32)
    scale = image.tag_v2.get(33550)
    tie = image.tag_v2.get(33922)
    if not scale or not tie:
        raise ValueError("GeoTIFF pixel-scale or tie-point tags are missing")
    pixel_x, pixel_y = float(scale[0]), float(scale[1])
    xmin, ymax = float(tie[3]), float(tie[4])
    xmax = xmin + values.shape[1] * pixel_x
    ymin = ymax - values.shape[0] * pixel_y
    valid = np.isfinite(values) & (values >= 0) & (values <= 1)
    return np.ma.masked_where(~valid, values), [xmin / 1000, xmax / 1000, ymin / 1000, ymax / 1000], pixel_x


def render(input_path: Path, output_path: Path, region: str, year: int):
    data, extent, pixel_m = load_geotiff(input_path)
    finite = data.compressed()
    cmap = LinearSegmentedColormap.from_list("fvc_continuous", PALETTE, N=256)
    cmap.set_bad("#E8ECEB")

    fig = plt.figure(figsize=(10.8, 12.4), facecolor="#F7F8F6")
    ax = fig.add_axes([0.08, 0.12, 0.77, 0.78])
    ax.set_facecolor("#E8ECEB")
    norm = PowerNorm(gamma=0.62, vmin=0, vmax=1)
    im = ax.imshow(data, extent=extent, origin="upper", cmap=cmap, norm=norm, interpolation="nearest")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Easting (km)", fontsize=10, color="#3C4743", labelpad=10)
    ax.set_ylabel("Northing (km)", fontsize=10, color="#3C4743", labelpad=10)
    ax.tick_params(labelsize=8.5, colors="#58635F", length=3)
    for spine in ax.spines.values():
        spine.set_color("#AEB8B3")
        spine.set_linewidth(0.8)

    cax = fig.add_axes([0.89, 0.25, 0.025, 0.47])
    cbar = fig.colorbar(im, cax=cax, ticks=np.linspace(0, 1, 6))
    cbar.set_label("Fractional vegetation cover", fontsize=10, color="#26322E", labelpad=12)
    cbar.ax.tick_params(labelsize=8.5, colors="#58635F")
    cbar.outline.set_linewidth(0.6)
    cbar.outline.set_edgecolor("#8B9691")

    fig.text(0.08, 0.955, f"{region} wetland FVC", fontsize=25, fontweight="bold", color="#172824", ha="left")
    fig.text(0.08, 0.923, f"Continuous pixel values in {year}", fontsize=13, color="#4D5B56", ha="left")
    fig.text(
        0.08, 0.058,
        f"Display raster: {pixel_m:.0f} m source pixels  ·  Continuous FVC (0–1)  ·  No class thresholds",
        fontsize=9.2, color="#4D5B56", ha="left",
    )
    fig.text(
        0.08, 0.035,
        f"Valid pixels: {finite.size:,}  ·  Median: {np.median(finite):.3f}  ·  P10–P90: {np.percentile(finite, 10):.3f}–{np.percentile(finite, 90):.3f}  ·  Power stretch for display only",
        fontsize=8.7, color="#68746F", ha="left",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=260, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def render_triptych(inputs: list[Path], output_path: Path, year: int = 2020):
    """Render three same-year rasters with one continuous scale and display norm."""
    if len(inputs) != 3:
        raise ValueError("Triptych requires YRD, GBA, and BTH rasters in that order")
    loaded = [load_geotiff(path) for path in inputs]
    cmap = LinearSegmentedColormap.from_list("fvc_continuous", PALETTE, N=256)
    cmap.set_bad("#E8ECEB")
    norm = PowerNorm(gamma=0.62, vmin=0, vmax=1)

    width_ratios = [
        (extent[1] - extent[0]) / (extent[3] - extent[2])
        for _, extent, _ in loaded
    ]
    fig = plt.figure(figsize=(17, 7.2), facecolor="#F7F8F6")
    grid = fig.add_gridspec(
        1, 3, left=0.04, right=0.91, top=0.80, bottom=0.12,
        wspace=0.09, width_ratios=width_ratios,
    )
    axes = [fig.add_subplot(grid[0, index]) for index in range(3)]
    image = None
    for ax, key, (data, extent, pixel_m) in zip(axes, REGION_NAMES, loaded):
        ax.set_facecolor("#E8ECEB")
        image = ax.imshow(data, extent=extent, origin="upper", cmap=cmap, norm=norm, interpolation="nearest")
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(REGION_NAMES[key], loc="left", fontsize=14, fontweight="bold", color="#172824", pad=10)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color("#AEB8B3")
            spine.set_linewidth(0.7)

    cax = fig.add_axes([0.935, 0.23, 0.014, 0.42])
    cbar = fig.colorbar(image, cax=cax, ticks=np.linspace(0, 1, 6))
    cbar.set_label("Fractional vegetation cover", fontsize=10, color="#26322E", labelpad=11)
    cbar.ax.tick_params(labelsize=8, colors="#58635F")
    cbar.outline.set_linewidth(0.6)
    cbar.outline.set_edgecolor("#8B9691")

    fig.text(0.04, 0.94, "Wetland FVC across three urban regions", fontsize=25, fontweight="bold", color="#172824", ha="left")
    fig.text(0.04, 0.885, f"Continuous pixel values in {year}  ·  one shared 0–1 scale", fontsize=12.5, color="#4D5B56", ha="left")
    fig.text(
        0.04, 0.045,
        "All panels use the same source year, 120 m display resolution, continuous color scale, and power stretch. No FVC classes are imposed.",
        fontsize=8.8, color="#4D5B56", ha="left",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=260, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, nargs="?")
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--region", default="Yangtze River Delta")
    parser.add_argument("--year", type=int, default=2020)
    parser.add_argument("--triptych", nargs=3, type=Path, metavar=("YRD", "GBA", "BTH"))
    parser.add_argument("--triptych-output", type=Path)
    args = parser.parse_args()
    if args.triptych:
        if args.triptych_output is None:
            parser.error("--triptych-output is required with --triptych")
        render_triptych(args.triptych, args.triptych_output, args.year)
    else:
        if args.input is None or args.output is None:
            parser.error("input and output are required unless --triptych is used")
        render(args.input, args.output, args.region, args.year)


if __name__ == "__main__":
    main()
